import os
import fcntl
import ctypes
import mmap


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


def ioctl(fd, request, argument):
    fcntl.ioctl(fd, request, argument)


fd = os.open(DEVICE, os.O_RDWR)

print("Câmera aberta:", DEVICE)


# ---------------------------------------------------------
# 1. Solicitar buffers ao driver
# ---------------------------------------------------------

req = V4L2RequestBuffers()

req.count = 4
req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
req.memory = V4L2_MEMORY_MMAP

ioctl(fd, VIDIOC_REQBUFS, req)

print("Buffers solicitados:", req.count)


# ---------------------------------------------------------
# 2. Consultar e mapear os buffers
# ---------------------------------------------------------

mapped_buffers = []

for index in range(req.count):

    buffer = V4L2Buffer()

    buffer.index = index
    buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
    buffer.memory = V4L2_MEMORY_MMAP

    ioctl(fd, VIDIOC_QUERYBUF, buffer)

    print(
        f"Buffer {index}: "
        f"length={buffer.length}, "
        f"offset={buffer.m}"
    )

    mapped = mmap.mmap(
        fd,
        buffer.length,
        mmap.MAP_SHARED,
        mmap.PROT_READ | mmap.PROT_WRITE,
        offset=buffer.m
    )

    mapped_buffers.append(mapped)


# ---------------------------------------------------------
# 3. Colocar todos os buffers na fila
# ---------------------------------------------------------

for index in range(req.count):

    buffer = V4L2Buffer()

    buffer.index = index
    buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
    buffer.memory = V4L2_MEMORY_MMAP

    ioctl(fd, VIDIOC_QBUF, buffer)


# ---------------------------------------------------------
# 4. Iniciar captura
# ---------------------------------------------------------

buffer_type = ctypes.c_int(V4L2_BUF_TYPE_VIDEO_CAPTURE)

ioctl(
    fd,
    VIDIOC_STREAMON,
    buffer_type
)

print()
print("Streaming iniciado.")
print()


try:

    for i in range(10):

        # Buffer que será preenchido pelo driver
        buffer = V4L2Buffer()

        buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        buffer.memory = V4L2_MEMORY_MMAP

        # Retira um frame da fila
        ioctl(
            fd,
            VIDIOC_DQBUF,
            buffer
        )

        timestamp_ns = (
            buffer.timestamp.tv_sec * 1_000_000_000
            + buffer.timestamp.tv_usec * 1_000
        )

        print(
            f"Frame {i}: "
            f"sequence={buffer.sequence} | "
            f"timestamp_ns={timestamp_ns} | "
            f"timestamp="
            f"{buffer.timestamp.tv_sec}."
            f"{buffer.timestamp.tv_usec:06d}"
        )

        # Devolve o buffer para o driver
        ioctl(
            fd,
            VIDIOC_QBUF,
            buffer
        )

finally:

    ioctl(
        fd,
        VIDIOC_STREAMOFF,
        buffer_type
    )

    for mapped in mapped_buffers:
        mapped.close()

    os.close(fd)

    print()
    print("Streaming encerrado.")