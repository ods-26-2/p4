import json

class MetadataFormatter:
    def __init__(self, camera_id="IMX519_RPi4_01", width=1280, height=720, fps=30):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps

    def build_event(self, frame_id: int, timestamp_ns: int, is_undistorted: bool, shutter_us=10000, gain_db=0.0) -> dict:
        return {
            "topic": "ods.sis2.p4_video_metadata",
            "camera_id": self.camera_id,
            "frame_id": frame_id,
            "timestamp_ns": timestamp_ns,
            "resolution": {
                "width": self.width,
                "height": self.height
            },
            "fps": self.fps,
            "is_undistorted": is_undistorted,
            "shutter_speed_us": shutter_us,
            "gain_db": gain_db
        }

    def to_json(self, event_dict: dict) -> str:
        return json.dumps(event_dict, indent=2)