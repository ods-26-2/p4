import os
import fcntl
import ctypes
import mmap
import cv2
import numpy as np

from .frame import Frame


DEVICE = "/dev/video0"

VIDIOC_REQBUFS = 0xC0145608
VIDIOC_QUERYBUF = 0xC0585609
VIDIOC_QBUF = 0xC058560F
VIDIOC_DQBUF = 0xC0585611
VIDIOC_STREAMON = 0x40045612
VIDIOC_STREAMOFF = 0x40045613

V4L2_BUF_TYPE_VIDEO_CAPTURE = 1
V4L2_MEMORY_MMAP = 1


class Timeval(ctypes.Structure):
    _fields_ = [
        ("tv_sec", ctypes.c_long),
        ("tv_usec", ctypes.c_long),
    ]


class V4L2RequestBuffers(ctypes.Structure):
    _fields_ = [
        ("count", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("memory", ctypes.c_uint32),
        ("capabilities", ctypes.c_uint32),
        ("flags", ctypes.c_uint8),
        ("reserved", ctypes.c_uint8 * 3),
    ]


class V4L2Buffer(ctypes.Structure):
    _fields_ = [
        ("index", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("bytesused", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("field", ctypes.c_uint32),
        ("timestamp", Timeval),
        ("timecode", ctypes.c_uint8 * 16),
        ("sequence", ctypes.c_uint32),
        ("memory", ctypes.c_uint32),
        ("m", ctypes.c_uint64),
        ("length", ctypes.c_uint32),
        ("reserved2", ctypes.c_uint32),
        ("request_fd", ctypes.c_int32),
        ("reserved", ctypes.c_uint32),
    ]


class V4L2Capture:

    def __init__(self, device=DEVICE):

        self.device = device
        self.fd = os.open(device, os.O_RDWR)

        self.buffers = []

        self._request_buffers()
        self._map_buffers()
        self._queue_buffers()
        self._start_stream()

    def _ioctl(self, request, argument):
        fcntl.ioctl(self.fd, request, argument)

    def _request_buffers(self):

        request = V4L2RequestBuffers()

        request.count = 4
        request.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        request.memory = V4L2_MEMORY_MMAP

        self._ioctl(VIDIOC_REQBUFS, request)

        if request.count < 2:
            raise RuntimeError("V4L2 não forneceu buffers suficientes.")

    def _map_buffers(self):

        for index in range(4):

            buffer = V4L2Buffer()

            buffer.index = index
            buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
            buffer.memory = V4L2_MEMORY_MMAP

            self._ioctl(VIDIOC_QUERYBUF, buffer)

            mapped = mmap.mmap(
                self.fd,
                buffer.length,
                mmap.MAP_SHARED,
                mmap.PROT_READ | mmap.PROT_WRITE,
                offset=buffer.m
            )

            self.buffers.append(mapped)

    def _queue_buffers(self):

        for index in range(len(self.buffers)):

            buffer = V4L2Buffer()

            buffer.index = index
            buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
            buffer.memory = V4L2_MEMORY_MMAP

            self._ioctl(VIDIOC_QBUF, buffer)

    def _start_stream(self):

        buffer_type = ctypes.c_int(V4L2_BUF_TYPE_VIDEO_CAPTURE)

        self._ioctl(
            VIDIOC_STREAMON,
            buffer_type
        )

    def read(self):

        buffer = V4L2Buffer()

        buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        buffer.memory = V4L2_MEMORY_MMAP

        self._ioctl(
            VIDIOC_DQBUF,
            buffer
        )

        try:

            data = self.buffers[buffer.index][:buffer.bytesused]

            encoded_image = cv2.imdecode(
                np.frombuffer(
                    data,
                    dtype=np.uint8
                ),
                cv2.IMREAD_COLOR
            )

            if encoded_image is None:
                raise RuntimeError("Não foi possível decodificar o frame.")

            timestamp_ns = (
                buffer.timestamp.tv_sec * 1_000_000_000
                + buffer.timestamp.tv_usec * 1_000
            )

            return Frame(
                image=encoded_image,
                timestamp_ns=timestamp_ns,
                frame_id=buffer.sequence
            )

        finally:

            self._ioctl(
                VIDIOC_QBUF,
                buffer
            )

    def release(self):

        buffer_type = ctypes.c_int(V4L2_BUF_TYPE_VIDEO_CAPTURE)

        self._ioctl(
            VIDIOC_STREAMOFF,
            buffer_type
        )

        for buffer in self.buffers:
            buffer.close()

        os.close(self.fd)