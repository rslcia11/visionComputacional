import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO

def create_walking_composite(person_clip, bg_frame, start_x, end_x, y_pos, seg_model):
    """
    Inserta la secuencia de una persona caminando sobre un fondo fijo (bg_frame)
    desplazándola suavemente desde start_x hasta end_x a la altura y_pos.
    """
    n_frames = len(person_clip)
    xs = np.linspace(start_x, end_x, n_frames).astype(int)
    h_bg, w_bg = bg_frame.shape[:2]
    
    out_frames = []
    for f_idx, src_frame in enumerate(person_clip):
        res = seg_model(src_frame, classes=[0], verbose=False)[0]
        comp = bg_frame.copy()
        
        if res.boxes and len(res.boxes) > 0 and res.masks:
            box = res.boxes.xyxy[0].cpu().numpy().astype(int)
            bx1, by1, bx2, by2 = box
            
            mask = res.masks.data[0].cpu().numpy()
            mask = cv2.resize(mask, (w_bg, h_bg))
            
            p_crop = src_frame[by1:by2, bx1:bx2]
            p_mask = (mask[by1:by2, bx1:bx2] > 0.5).astype(np.float32)[:, :, None]
            p_mask_blur = cv2.GaussianBlur(p_mask, (5, 5), 0)[:, :, None]
            
            target_h = by2 - by1
            target_w = bx2 - bx1
            
            # Posicionar en el fondo
            cur_x = xs[f_idx]
            cur_y = max(0, min(h_bg - target_h, y_pos))
            cur_x = max(0, min(w_bg - target_w, cur_x))
            
            roi = comp[cur_y:cur_y+target_h, cur_x:cur_x+target_w]
            blended = roi * (1.0 - p_mask_blur) + p_crop * p_mask_blur
            comp[cur_y:cur_y+target_h, cur_x:cur_x+target_w] = blended.astype(np.uint8)
            
        out_frames.append(comp)
    return out_frames

def extract_clip(video_path: str, start_frame: int, end_frame: int):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frames = []
    for f in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret: break
        frames.append(frame)
    cap.release()
    return frames

def main():
    print("=" * 70)
    print("   GENERANDO ESCENARIO MULTI-CÁMARA CCTV DE PRODUCCIÓN (ESCENARIOS FIJOS)")
    print("=" * 70)
    
    seg_model = YOLO("yolov8n-seg.pt")
    
    raw_dir = Path("data/raw")
    backup_dir = raw_dir / "backup_original"
    
    path_pasillo = str(backup_dir / "cam_a_raw.mp4")
    path_salon = str(backup_dir / "cam_b_raw.mp4")
    
    # 1. Fondo limpio del pasillo (Cámara A)
    cap_bg = cv2.VideoCapture(path_pasillo)
    cap_bg.set(cv2.CAP_PROP_POS_FRAMES, 110)
    _, bg_pasillo = cap_bg.read()
    cap_bg.release()
    
    # Clips nativos de personas
    print("[1/4] Extrayendo actores reales...")
    # Pasillo nativo: Sujeto campera clara (frames 20 a 72)
    pasillo_sujeto_claro = extract_clip(path_pasillo, 20, 72)
    # Pasillo nativo: Cruce de dos personas (frames 180 a 245)
    pasillo_cruce = extract_clip(path_pasillo, 180, 245)
    
    # Salón nativo: Chica de gris (frames 65 a 190)
    salon_chica_gris = extract_clip(path_salon, 65, 190)
    # Salón nativo: Hombre de campera negra (frames 235 a 420)
    salon_hombre_mesa = extract_clip(path_salon, 235, 420)
    # Salón nativo: Mujer rubia vestida de negro (frames 515 a 685)
    salon_mujer_rubia = extract_clip(path_salon, 515, 685)
    
    # 2. Sintetizar tránsito de Hombre y Mujer cruzando el Pasillo (Cámara A)
    print("[2/4] Generando secuencias de Cámara A (100% Pasillo continuo)...")
    # Hombre cruzando el pasillo de izquierda a derecha (frames 240 a 340 subsampleado a ~60 frames)
    hombre_clip_walk = salon_hombre_mesa[10:90]
    hombre_pasillo = create_walking_composite(
        person_clip=hombre_clip_walk,
        bg_frame=bg_pasillo,
        start_x=100,
        end_x=450,
        y_pos=40,
        seg_model=seg_model
    )
    
    # Mujer rubia cruzando el pasillo de izquierda a derecha
    mujer_clip_walk = salon_mujer_rubia[10:90]
    mujer_pasillo = create_walking_composite(
        person_clip=mujer_clip_walk,
        bg_frame=bg_pasillo,
        start_x=120,
        end_x=470,
        y_pos=45,
        seg_model=seg_model
    )
    
    empty_pasillo = [bg_pasillo.copy() for _ in range(50)]
    
    # Ensamblar Cámara A:
    # 1. Sujeto campera clara (Exclusivo Pasillo)
    # 2. Hombre de campera negra (Compartido - transita por pasillo)
    # 3. Mujer rubia de negro (Compartida - transita por pasillo)
    # 4. Cruce de dos peatones (Exclusivos Pasillo)
    frames_cam_a = pasillo_sujeto_claro + empty_pasillo + hombre_pasillo + empty_pasillo + mujer_pasillo + empty_pasillo + pasillo_cruce
    
    print("[3/4] Generando secuencias de Cámara B (100% Salón continuo)...")
    # Extraer fondo limpio del salón
    cap_bg_b = cv2.VideoCapture(path_salon)
    cap_bg_b.set(cv2.CAP_PROP_POS_FRAMES, 20)
    _, bg_salon = cap_bg_b.read()
    cap_bg_b.release()
    empty_salon = [bg_salon.copy() for _ in range(50)]
    
    # Ensamblar Cámara B:
    # 1. Chica de gris (Exclusiva Salón)
    # 2. Llega el Hombre de campera negra (Compartido - llega al salón)
    # 3. Llega la Mujer rubia de negro (Compartida - llega al salón)
    frames_cam_b = salon_chica_gris + empty_salon + salon_hombre_mesa + empty_salon + salon_mujer_rubia

    
    print("[4/4] Guardando videos de producción...")
    out_a_path = raw_dir / "cam_a.mp4"
    out_b_path = raw_dir / "cam_b.mp4"
    
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    h_a, w_a = frames_cam_a[0].shape[:2]
    vw_a = cv2.VideoWriter(str(out_a_path), fourcc, 12.0, (w_a, h_a))
    for f in frames_cam_a:
        vw_a.write(f)
    vw_a.release()
    print(f"  -> {out_a_path}: {len(frames_cam_a)} fotogramas (100% Pasillo CCTV-01)")
    
    h_b, w_b = frames_cam_b[0].shape[:2]
    vw_b = cv2.VideoWriter(str(out_b_path), fourcc, 12.0, (w_b, h_b))
    for f in frames_cam_b:
        vw_b.write(f)
    vw_b.release()
    print(f"  -> {out_b_path}: {len(frames_cam_b)} fotogramas (100% Salón CCTV-02)")
    
    print("\n[✓] Escenario multi-cámara de producción generado exitosamente.")

if __name__ == "__main__":
    main()
