
CAMERAS = {
    "emeet": {
        "source_id": "emeet",
        "device": "/dev/video0",
        "width": 640,
        "height": 480,
        "fps": None,
        "pixel_format": "MJPG",
        "raw": False,
        "socket_path": "/tmp/p4_video_shm",
        "enabled": True
    },

    "imx519": {
        "source_id": "imx519",
        "device": "/dev/video0",
        "width": 1920,
        "height": 1080,
        "fps": None,
        "pixel_format": "RG10",
        "raw": True,
        "socket_path": "/tmp/p4_imx519_shm",
        "enabled": True
    },  

    "imx477": {
        "source_id": "imx477",
        "device": None,
        "width": None,
        "height": None,
        "fps": None,
        "pixel_format": None,
        "raw": None,
        "socket_path": "/tmp/p4_imx477_shm",
        "enabled": False
    }
}
