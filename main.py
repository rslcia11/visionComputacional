import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple
import cv2
import numpy as np
from tqdm import tqdm

from src.tracker import CameraTracker, TrackedPerson
from src.reid import AppearanceFeatureExtractor, CrossCameraMatcher
from src.visualizer import VideoVisualizer
from src.recorder import ResultsRecorder


def process_camera_stream(
    camera_id: str,
    video_path: str,
    output_video_path: str,
    tracker: CameraTracker,
    extractor: AppearanceFeatureExtractor,
    matcher: CrossCameraMatcher,
    recorder: ResultsRecorder,
    max_frames: int = 0,
    show: bool = False
) -> Tuple[int, int]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video source: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if max_frames > 0:
        total_frames = min(total_frames, max_frames)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    frame_idx = 0
    unique_local_ids: Set[int] = set()

    pbar = tqdm(total=total_frames, desc=f"Processing {camera_id.upper()}", unit="frame", ascii=True)

    while cap.isOpened() and (max_frames == 0 or frame_idx < max_frames):
        ret, frame = cap.read()
        if not ret:
            break

        timestamp_sec = frame_idx / fps

        # 1. Seguimiento intra-camara
        tracked_persons: List[TrackedPerson] = tracker.update(frame)
        active_local_ids = {p.track_id for p in tracked_persons}
        unique_local_ids.update(active_local_ids)

        # 2. Extraer recortes para detecciones validas
        crops = []
        valid_persons = []
        for person in tracked_persons:
            x1, y1, x2, y2 = person.bbox
            crop = frame[y1:y2, x1:x2]
            if crop.size > 0 and (y2 - y1) >= 12 and (x2 - x1) >= 12:
                crops.append(crop)
                valid_persons.append(person)

        # 3. Extraer embeddings de apariencia
        rendered_tracks = []
        if valid_persons:
            embeddings = extractor.extract(crops)

            for person, emb in zip(valid_persons, embeddings):
                # Asociar con el matcher inter-camara
                gid = matcher.associate_or_register(
                    camera_id=camera_id,
                    local_track_id=person.track_id,
                    feature_vector=emb,
                    currently_active_local_ids=active_local_ids
                )
                reid_sim = matcher.get_association_confidence(camera_id, person.track_id)

                rendered_tracks.append({
                    "bbox": person.bbox,
                    "local_id": person.track_id,
                    "global_id": gid,
                    "reid_sim": reid_sim
                })

                # 4. Registro en el CSV auditable
                recorder.record(
                    camera_id=camera_id,
                    frame_idx=frame_idx,
                    timestamp_sec=timestamp_sec,
                    local_id=person.track_id,
                    global_id=gid,
                    bbox=person.bbox,
                    confidence=person.confidence,
                    reid_similarity=reid_sim
                )

        # 5. Renderizado visual con etiquetas adaptativas
        annotated_frame = VideoVisualizer.draw_detections(
            frame=frame,
            camera_id=camera_id,
            frame_idx=frame_idx,
            timestamp_sec=timestamp_sec,
            tracks=rendered_tracks
        )

        out_writer.write(annotated_frame)

        if show:
            cv2.imshow(f"Stream: {camera_id.upper()}", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print(f"\n[!] Visualización interrumpida por usuario en frame {frame_idx}.")
                break

        frame_idx += 1
        pbar.update(1)

    pbar.close()
    cap.release()
    out_writer.release()
    if show:
        cv2.destroyAllWindows()

    return frame_idx, len(unique_local_ids)


def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Seguimiento y Reidentificacion de Personas Multi-Camara (MTMC Re-ID)"
    )
    parser.add_argument(
        "--cam_a",
        type=str,
        default="data/raw/cam_a.mp4",
        help="Ruta al video de la Camara A"
    )
    parser.add_argument(
        "--cam_b",
        type=str,
        default="data/raw/cam_b.mp4",
        help="Ruta al video de la Camara B"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="data/output",
        help="Directorio donde guardar videos procesados y CSV"
    )
    parser.add_argument(
        "--reid_threshold",
        type=float,
        default=0.70,
        help="Umbral de similitud coseno para asociacion entre camaras"
    )
    parser.add_argument(
        "--max_frames",
        type=int,
        default=0,
        help="Limite de fotogramas a procesar (0 = procesar todo el video)"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Mostrar ventana interactiva de OpenCV durante el procesamiento"
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = str(output_dir / "detections_and_associations.csv")
    out_cam_a = str(output_dir / "cam_a_annotated.mp4")
    out_cam_b = str(output_dir / "cam_b_annotated.mp4")

    print("\n" + "=" * 70)
    print("   SISTEMA DE SEGUIMIENTO Y REIDENTIFICACION MULTI-CAMARA (Re-ID)")
    print("=" * 70)
    print(f" Video Camara A      : {args.cam_a}")
    print(f" Video Camara B      : {args.cam_b}")
    print(f" Umbral Re-ID        : {args.reid_threshold}")
    print(f" Directorio Salida   : {args.output_dir}")
    print(f" Registro CSV        : {csv_path}")
    print(f" Visualizacion       : {'Activada' if args.show else 'Desactivada (Consola)'}")
    print("=" * 70 + "\n")

    # Inicializar componentes compartidos
    print("[1/4] Inicializando extractor de caracteristicas y matcher...")
    extractor = AppearanceFeatureExtractor(device="cpu")
    matcher = CrossCameraMatcher(similarity_threshold=args.reid_threshold)
    recorder = ResultsRecorder(output_path=csv_path)

    # Instancias de tracking independientes por camara
    tracker_a = CameraTracker(camera_id="cam_a")
    tracker_b = CameraTracker(camera_id="cam_b")

    start_time = time.time()

    # Paso 1: Procesar Camara A
    print("\n[2/4] Procesando flujo de Camara A...")
    frames_a, tracks_a = process_camera_stream(
        camera_id="cam_a",
        video_path=args.cam_a,
        output_video_path=out_cam_a,
        tracker=tracker_a,
        extractor=extractor,
        matcher=matcher,
        recorder=recorder,
        max_frames=args.max_frames,
        show=args.show
    )

    # Paso 2: Procesar Camara B
    print("\n[3/4] Procesando flujo de Camara B...")
    frames_b, tracks_b = process_camera_stream(
        camera_id="cam_b",
        video_path=args.cam_b,
        output_video_path=out_cam_b,
        tracker=tracker_b,
        extractor=extractor,
        matcher=matcher,
        recorder=recorder,
        max_frames=args.max_frames,
        show=args.show
    )

    recorder.close()
    elapsed_time = time.time() - start_time

    # Step 3: Compute summary statistics
    total_global_ids = len(matcher.gallery)
    reidentified_across_cameras = [
        gid for gid, ident in matcher.gallery.items()
        if len(ident.cameras_seen) > 1
    ]

    print("\n" + "=" * 70)
    print("                     EJECUCIÓN COMPLETADA CON ÉXITO")
    print("=" * 70)
    print(f" Tiempo total de procesamiento : {elapsed_time:.2f} s")
    print(f" Fotogramas procesados (Cam A) : {frames_a}")
    print(f" Fotogramas procesados (Cam B) : {frames_b}")
    print(f" Identidades locales en Cam A  : {tracks_a}")
    print(f" Identidades locales en Cam B  : {tracks_b}")
    print(f" Identidades Globales totales  : {total_global_ids}")
    print(f" Personas reidentificadas (A&B): {len(reidentified_across_cameras)} (IDs: {reidentified_across_cameras})")
    print("-" * 70)
    print(f" Video resultante Cam A        : {out_cam_a}")
    print(f" Video resultante Cam B        : {out_cam_b}")
    print(f" Registro CSV auditable        : {csv_path}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
