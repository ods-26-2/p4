import time
import cv2
from src.capture import P4KernelVideoCapture
from src.undistort import RealtimeUndistorter
from src.metadata import MetadataFormatter

def main():
    capture = P4KernelVideoCapture(device="/dev/video0", width=1280, height=720, fps=30)
    undistorter = RealtimeUndistorter("config/camera_calibration.json")
    formatter = MetadataFormatter(camera_id="IMX519_RPi4_01", width=1280, height=720, fps=30)

    capture.start()
    print("=== Pipeline P4 Iniciado (Pressione 'Q' para encerrar) ===")

    try:
        while True:
            ret, frame, timestamp_ns, frame_id = capture.read()
            if not ret:
                time.sleep(0.005)
                continue

            # Desdistorção acelerada
            undistorted_frame = undistorter.process(frame)

            # Formatação do evento JSON de metadados
            event = formatter.build_event(
                frame_id=frame_id,
                timestamp_ns=timestamp_ns,
                is_undistorted=True
            )

            # Exibição de diagnóstico
            cv2.imshow("P4 Video Stream - Undistorted", undistorted_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        capture.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()