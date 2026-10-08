
CAMERAS = {
    "emeet": {
        "name": "EMEET SmartCam C60E 4K",
        "vendor_id": "328f",
        "product_id": "00f3",
        "validated": True,
        "backend": "gstreamer",
        "modes": {
            (3840, 2160): [30],
            (2560, 1440): [30],
            (1920, 1080): [30, 60],
            (1280, 960): [30],
            (1280, 720): [30, 60],
            (1024, 576): [30, 60],
            (960, 720): [30],
            (800, 600): [30],
            (640, 480): [30],
            (640, 360): [30, 60],
        },
    },
    "imx519": {
        "name": "IMX519",
        "validated": False,
        "backend": None,
        "modes": {},
    },
    "imx477": {
        "name": "IMX477",
        "validated": False,
        "backend": None,
        "modes": {},
    },
}
