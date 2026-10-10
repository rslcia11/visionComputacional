from pathlib import Path
import cv2
import pandas as pd

def extract_frame(video_path: str, frame_num: int, output_path: str):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(output_path, frame)
        print(f"Extracted frame {frame_num} from {video_path} -> {output_path}")
    else:
        print(f"Failed to extract frame {frame_num} from {video_path}")
    cap.release()

def main():
    out_dir = Path("data/output/evidence")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    artifact_dir = Path(r"C:\Users\Usuario\.gemini\antigravity-ide\brain\b0a7cb4c-4b66-461b-87a8-646d6d50966f\evidence")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    targets = [
        # (video, frame, filename, descripcion)
        ("data/output/cam_a_annotated.mp4", 25, "01_cam_a_actor1_gid1.jpg", "Cam A - Actor 1 (Global ID 1)"),
        ("data/output/cam_a_annotated.mp4", 120, "02_cam_a_actor2_rubia_gid2.jpg", "Cam A - Mujer Rubia (Global ID 2)"),
        ("data/output/cam_a_annotated.mp4", 305, "03_cam_a_actores3_4_cruce.jpg", "Cam A - Cruce de peatones (Global IDs 3 y 4)"),
        ("data/output/cam_b_annotated.mp4", 70, "04_cam_b_actor5_chica_gris_gid5.jpg", "Cam B - Chica saco gris (Global ID 5)"),
        ("data/output/cam_b_annotated.mp4", 185, "05_cam_b_actor1_reid_gid1.jpg", "Cam B - Actor 1 Reidentificado (Global ID 1)"),
        ("data/output/cam_b_annotated.mp4", 300, "06_cam_b_actor6_hombre_mesa_gid7.jpg", "Cam B - Hombre de espaldas (Global ID 7 independiente, CERO colisión)"),
        ("data/output/cam_b_annotated.mp4", 550, "07_cam_b_actor2_rubia_reid_gid2.jpg", "Cam B - Mujer Rubia Reidentificada (Global ID 2)"),
    ]

    for video, frame_num, fname, desc in targets:
        dst_local = str(out_dir / fname)
        dst_art = str(artifact_dir / fname)
        extract_frame(video, frame_num, dst_local)
        extract_frame(video, frame_num, dst_art)

if __name__ == "__main__":
    main()
