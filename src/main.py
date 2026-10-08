
import json

from src.gstreamer_capture import GStreamerCapture
from src.menu import escolher_camera, escolher_modo
from src.metadata import FrameMetadata
from src.video_recorder import VideoRecorder


def main():
    camera_id, config = escolher_camera()

    if config is None:
        return

    width, height, fps = escolher_modo(config["modes"])

    try:
        if config["backend"] == "gstreamer":
            camera = GStreamerCapture(
                device=config["device"],
                width=width,
                height=height,
                fps=fps
            )
        else:
            raise ValueError(
                f"Backend não implementado: {config['backend']}"
            )

    except (ValueError, RuntimeError) as erro:
        print(f"Erro ao iniciar a câmera: {erro}")
        return

    try:
        recorder = VideoRecorder(
            width=width,
            height=height,
            fps=fps
        )
    except RuntimeError as erro:
        camera.release()
        print(f"Erro ao iniciar a gravação: {erro}")
        return

    print("\nCaptura contínua iniciada.")
    print("Pressione Ctrl+C para encerrar.\n")

    try:
        while True:
            frame = camera.read()
            recorder.write(frame)

            metadata = FrameMetadata(
                camera_id=camera_id,
                width=frame.image.shape[1],
                height=frame.image.shape[0],
                fps=camera.fps,
                is_undistorted=False
            )

            payload = {
                "camera_id": metadata.camera_id,
                "frame_id": frame.frame_id,
                "timestamp_ns": frame.timestamp_ns,
                "resolution_width": metadata.width,
                "resolution_height": metadata.height,
                "fps": metadata.fps,
                "is_undistorted": metadata.is_undistorted,
                "shutter_speed_us": None,
                "gain_db": None
            }

            print(json.dumps(payload))

    except KeyboardInterrupt:
        print("\nCaptura interrompida pelo usuário.")

    finally:
        recorder.release()
        camera.release()
        print(f"Vídeo salvo em: {recorder.output_path}")
        print("Câmera liberada.")


if __name__ == "__main__":
    main()
