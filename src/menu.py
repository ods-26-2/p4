
from .camera_config import CAMERAS
from .camera_detector import detectar_dispositivos_video, identificar_cameras



def escolher_camera():
    dispositivos = detectar_dispositivos_video()
    cameras_detectadas = identificar_cameras(dispositivos)

    print("\n=== P4 - FONTE DE VÍDEO ===")

    if not cameras_detectadas:
        print("\nNenhuma câmera compatível foi detectada.")
        return None, None

    print("\nEscolha a câmera:\n")

    for indice, camera in enumerate(cameras_detectadas, start=1):
        print(f"{indice}. {camera['name']} ({camera['device']})")

    while True:
        try:
            escolha = int(input("\nNúmero da opção: "))

            if 1 <= escolha <= len(cameras_detectadas):
                break

            print("Opção fora da lista. Tente novamente.")

        except ValueError:
            print("Digite um número válido.")

    camera = cameras_detectadas[escolha - 1]
    camera_id = camera["id"]

    config = CAMERAS[camera_id].copy()
    config["device"] = camera["device"]

    return camera_id, config



def escolher_modo(modos_suportados):
    modos = sorted(
        modos_suportados.items(),
        key=lambda item: item[0][0] * item[0][1],
        reverse=True
    )

    print("\nEscolha a resolução:\n")

    for indice, (resolucao, fps_disponiveis) in enumerate(
        modos, start=1
    ):
        largura, altura = resolucao
        print(
            f"{indice}. {largura}x{altura} "
            f"(FPS disponíveis: {fps_disponiveis})"
        )

    while True:
        try:
            escolha = int(input("\nNúmero da opção: "))

            if 1 <= escolha <= len(modos):
                break

            print("Opção fora da lista. Tente novamente.")

        except ValueError:
            print("Digite um número válido.")

    (largura, altura), fps_disponiveis = modos[escolha - 1]

    while True:
        try:
            fps = int(input(f"Escolha o FPS {fps_disponiveis}: "))

            if fps in fps_disponiveis:
                break

            print("Esse FPS não está disponível para a resolução.")

        except ValueError:
            print("Digite um número válido.")

    return largura, altura, fps
