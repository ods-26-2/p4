import os
import cv2

CHECKERBOARD = (8, 6)
OUTPUT_DIR = "./data/dataset_inv1"
os.makedirs(OUTPUT_DIR, exist_ok=True)

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

saved_count = 0
print("=== Coletor de Calibração P4 -> INV-1 ===")
print("ESPAÇO: Salva frame | Q: Sair")

while True:
    ret, frame = cap.read()
    if not ret:
        continue
        
    display_frame = frame.copy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    found, corners = cv2.findChessboardCorners(
        gray, CHECKERBOARD, 
        flags=cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK + cv2.CALIB_CB_NORMALIZE_IMAGE
    )
    
    if found:
        criteria = (cv2.TERMCRITERIA_EPS + cv2.TERMCRITERIA_MAX_ITER, 30, 0.001)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        cv2.drawChessboardCorners(display_frame, CHECKERBOARD, corners2, found)
        cv2.putText(display_frame, f"PADRAO OK | Salvos: {saved_count}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    else:
        cv2.putText(display_frame, f"Buscando Padrao... | Salvos: {saved_count}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
    cv2.imshow("Calibração INV-1", display_frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord(' ') and found:
        filename = os.path.join(OUTPUT_DIR, f"imx519_calib_{saved_count:03d}.png")
        cv2.imwrite(filename, frame)
        print(f"[OK] Imagem salva: {filename}")
        saved_count += 1
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()