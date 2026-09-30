import time
import gi
import numpy as np

gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GstApp

class P4KernelVideoCapture:
    def __init__(self, device="/dev/video0", width=1280, height=720, fps=30):
        Gst.init(None)
        
        pipeline_str = (
            f"v4l2src device={device} ! "
            f"video/x-raw, width={width}, height={height}, framerate={fps}/1 ! "
            f"videoconvert ! video/x-raw, format=BGR ! "
            f"appsink name=sink emit-signals=true max-buffers=1 drop=true sync=false"
        )
        
        self.pipeline = Gst.parse_launch(pipeline_str)
        self.appsink = self.pipeline.get_by_name("sink")
        
        self.latest_frame = None
        self.latest_timestamp_ns = 0
        self.frame_id = 0
        
        self.appsink.connect("new-sample", self._on_new_sample)

    def _on_new_sample(self, sink):
        sample = sink.emit("pull-sample")
        if not sample:
            return Gst.FlowReturn.ERROR

        buffer = sample.get_buffer()
        
        # Extração do timestamp monotônico no nível do kernel Linux
        if buffer.pts != Gst.CLOCK_TIME_NONE:
            self.latest_timestamp_ns = buffer.pts
        else:
            self.latest_timestamp_ns = time.clock_gettime_ns(time.CLOCK_MONOTONIC)

        caps = sample.get_caps()
        height = caps.get_structure(0).get_value("height")
        width = caps.get_structure(0).get_value("width")
        
        success, map_info = buffer.map(Gst.MapFlags.READ)
        if success:
            frame_array = np.ndarray(
                shape=(height, width, 3),
                dtype=np.uint8,
                buffer=map_info.data
            )
            self.latest_frame = frame_array.copy()
            buffer.unmap(map_info)
            self.frame_id += 1

        return Gst.FlowReturn.OK

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)

    def read(self):
        if self.latest_frame is None:
            return False, None, 0, 0
        return True, self.latest_frame, self.latest_timestamp_ns, self.frame_id

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)