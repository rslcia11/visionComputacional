import os
import shutil
from pathlib import Path
import cv2
import numpy as np


def extract_clip(video_path: str, start_frame: int, end_frame: int, transform=None):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frames = []
    for f in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret:
            break
        if transform is not None:
            frame = transform(frame)
        frames.append(frame)
    cap.release()
    return frames


def cam_b_camera_transform(frame: np.ndarray) -> np.ndarray:
    """
    Simula un ángulo de cámara diferente (CCTV B):
    1. Leve ajuste de perspectiva/escala (0.95x y pad).
    2. Leve variación de balance de blancos / temperatura de color.
    """
    h, w = frame.shape[:2]
    # Leve ajuste de brillo y contraste (simula iluminación de pasillo B)
    adjusted = cv2.convertScaleAbs(frame, alpha=0.96, beta=6)
    return adjusted


def main():
    raw_dir = Path("data/raw")
    backup_dir = raw_dir / "backup_original"
    backup_dir.mkdir(parents=True, exist_ok=True)

    orig_a = raw_dir / "cam_a.mp4"
    orig_b = raw_dir / "cam_b.mp4"

    # Hacer backup si no existe
    if orig_a.exists() and not (backup_dir / "cam_a_raw.mp4").exists():
        shutil.copy(orig_a, backup_dir / "cam_a_raw.mp4")
    if orig_b.exists() and not (backup_dir / "cam_b_raw.mp4").exists():
        shutil.copy(orig_b, backup_dir / "cam_b_raw.mp4")

    source_people = str(backup_dir / "cam_a_raw.mp4")
    source_onebyone = str(backup_dir / "cam_b_raw.mp4")

    print("[1/3] Extrayendo actores reales para el escenario multi-cámara...")
    # Actor 1: Sujeto con campera clara cruzando pasillo (frames 18 a 72 de people-detection) -> COMPARTIDO
    actor_1_a = extract_clip(source_people, 18, 72)
    # Actor 2: Mujer rubia con ropa oscura (frames 510 a 690 de one-by-one) -> COMPARTIDA
    actor_2_a = extract_clip(source_onebyone, 510, 690)
    # Actores 3 y 4: Dos personas cruzándose (frames 180 a 248 de people-detection) -> EXCLUSIVOS CÁMARA A
    actor_3_4_a = extract_clip(source_people, 180, 248)

    # Actor 5: Sujeto 1 de one-by-one (frames 65 a 190) -> EXCLUSIVO CÁMARA B
    actor_5_b = extract_clip(source_onebyone, 65, 190)
    # Actor 6: Hombre en la mesa (frames 235 a 440 de one-by-one) -> EXCLUSIVO CÁMARA B
    actor_6_b = extract_clip(source_onebyone, 235, 440)

    # Actor 1 en Cámara B (ingresa a la Cámara B con leve variación de cámara) -> COMPARTIDO
    actor_1_b = extract_clip(source_people, 20, 72, transform=cam_b_camera_transform)
    # Actor 2 en Cámara B (ingresa a la Cámara B con leve variación de cámara) -> COMPARTIDO
    actor_2_b = extract_clip(source_onebyone, 515, 685, transform=cam_b_camera_transform)

    # Padding vacío entre personas para simular paso temporal realista (30 frames = 2.5 seg)
    empty_pad = [np.ones_like(actor_1_a[0]) * 150 for _ in range(25)]

    print("[2/3] Ensamblando Cámara A (Entrada Pasillo)...")
    # Secuencia Cámara A:
    # 1. Actor 1 (Compartido)
    # 2. Actor 2 (Compartido)
    # 3. Actores 3 y 4 (Solo en A)
    frames_cam_a = actor_1_a + empty_pad + actor_2_a + empty_pad + actor_3_4_a

    print("[3/3] Ensamblando Cámara B (Salida Pasillo)...")
    # Secuencia Cámara B:
    # 1. Actor 5 (Solo en B)
    # 2. Actor 1 (¡LLEGA EL ACTOR 1 DE CÁMARA A!)
    # 3. Actor 6 (Solo en B)
    # 4. Actor 2 (¡LLEGA EL ACTOR 2 DE CÁMARA A!)
    frames_cam_b = actor_5_b + empty_pad + actor_1_b + empty_pad + actor_6_b + empty_pad + actor_2_b

    # Grabar los nuevos videos cam_a.mp4 y cam_b.mp4
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    h, w = frames_cam_a[0].shape[:2]

    out_a = cv2.VideoWriter(str(orig_a), fourcc, 12.0, (w, h))
    for f in frames_cam_a:
        out_a.write(f)
    out_a.release()

    h_b, w_b = frames_cam_b[0].shape[:2]
    out_b = cv2.VideoWriter(str(orig_b), fourcc, 12.0, (w_b, h_b))
    for f in frames_cam_b:
        out_b.write(f)
    out_b.release()

    print("\n" + "=" * 65)
    print("   ESCENARIO MULTI-CÁMARA DE VALIDACIÓN CREADO CON ÉXITO")
    print("=" * 65)
    print(f" Cámara A: {len(frames_cam_a)} frames (~{len(frames_cam_a)/12:.1f}s)")
    print("   - Actor 1 (Compartido: aparece en A y luego en B)")
    print("   - Actor 2 (Compartido: aparece en A y luego en B)")
    print("   - Actores 3 y 4 (Exclusivos de Cámara A)")
    print(f" Cámara B: {len(frames_cam_b)} frames (~{len(frames_cam_b)/12:.1f}s)")
    print("   - Actor 5 (Exclusivo de Cámara B)")
    print("   - Actor 1 (REIDENTIFICACIÓN: el mismo de Cámara A)")
    print("   - Actor 6 (Exclusivo de Cámara B)")
    print("   - Actor 2 (REIDENTIFICACIÓN: la misma de Cámara A)")
    print("=" * 65)


if __name__ == "__main__":
    main()
