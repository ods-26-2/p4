
import glob
import subprocess
from .camera_config import CAMERAS


def detectar_dispositivos_video():
    dispositivos = []

    for caminho in sorted(glob.glob("/dev/video*")):
        try:
            resultado = subprocess.run(
                [
                    "udevadm",
                    "info",
                    "--query=property",
                    f"--name={caminho}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            continue

        propriedades = {}

        for linha in resultado.stdout.splitlines():
            if "=" in linha:
                chave, valor = linha.split("=", 1)
                propriedades[chave] = valor

        capacidades = propriedades.get(
            "ID_V4L_CAPABILITIES", ""
        )

        if "capture" not in capacidades.split(":"):
            continue

        dispositivos.append({
            "device": caminho,
            "vendor_id": propriedades.get("ID_VENDOR_ID"),
            "model_id": propriedades.get("ID_MODEL_ID"),
            "serial": propriedades.get("ID_SERIAL_SHORT"),
            "name": propriedades.get("ID_V4L_PRODUCT"),
        })

    return dispositivos

def identificar_cameras(dispositivos):
    cameras_encontradas = []

    for dispositivo in dispositivos:
        for camera_id, config in CAMERAS.items():
            if (
                dispositivo["vendor_id"] == config.get("vendor_id")
                and dispositivo["model_id"] == config.get("product_id")
                and config.get("vendor_id") is not None
            ):
                cameras_encontradas.append({
                    "id": camera_id,
                    "name": config["name"],
                    "device": dispositivo["device"],
                    "validated": config["validated"],
                })

    return cameras_encontradas  


if __name__ == "__main__":
    dispositivos = detectar_dispositivos_video()
    cameras = identificar_cameras(dispositivos)

    for camera in cameras:
        print(camera)
