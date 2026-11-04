
import unittest
from unittest.mock import patch

from src.v4l2_source import V4L2Source


class TestV4L2Source(unittest.TestCase):

    def test_configura_sensor_mode(self):
        with patch("src.v4l2_source.Device") as mock_device, \
             patch("src.v4l2_source.VideoCapture") as mock_capture:

            capture = mock_capture.return_value
            formato = capture.get_format.return_value

            formato.width = 1920
            formato.height = 1080
            formato.pixel_format.human_str.return_value = "RG10"

            def verificar_modo(*args):
                self.assertEqual(
                    mock_device.return_value.controls.sensor_mode.value,
                    2
                )

            capture.set_format.side_effect = verificar_modo

            fonte = V4L2Source(
                device="/dev/video1",
                width=1920,
                height=1080,
                pixel_format="RG10",
                sensor_mode=2
            )

            fonte.release()


if __name__ == "__main__":
    unittest.main()
