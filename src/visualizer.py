from typing import Dict, List, Tuple
import cv2
import numpy as np


class VideoVisualizer:
    # Paleta de 16 colores distintivos para identidades globales
    COLOR_PALETTE = [
        (46, 204, 113),   # Verde
        (52, 152, 219),   # Azul
        (155, 89, 182),   # Purpura
        (241, 196, 15),   # Amarillo
        (230, 126, 34),   # Naranja
        (231, 76, 60),    # Rojo
        (26, 188, 156),   # Turquesa
        (243, 156, 18),   # Ambar
        (52, 73, 94),     # Azul oscuro
        (255, 107, 129),  # Rosa
        (112, 161, 255),  # Celeste
        (123, 237, 159),  # Verde claro
        (255, 165, 2),    # Coral
        (255, 71, 87),    # Carmesi
        (30, 144, 255),   # Azul dodger
        (255, 218, 121),  # Crema
    ]

    @classmethod
    def get_color_for_global_id(cls, global_id: int) -> Tuple[int, int, int]:
        color = cls.COLOR_PALETTE[(global_id - 1) % len(cls.COLOR_PALETTE)]
        # Formato BGR para OpenCV
        return (color[2], color[1], color[0])

    @classmethod
    def draw_detections(
        cls,
        frame: np.ndarray,
        camera_id: str,
        frame_idx: int,
        timestamp_sec: float,
        tracks: List[Dict]  # Lista de dicts con bbox, local_id, global_id, reid_sim
    ) -> np.ndarray:
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # 1. Dibujar primero el banner de metadatos superior para que nunca tape los badges
        banner_h = 32
        cv2.rectangle(annotated, (0, 0), (w, banner_h), (15, 15, 15), -1)
        banner_text = f"CAM: {camera_id.upper()} | Frame: {frame_idx:04d} | Time: {timestamp_sec:.1f}s | Active Tracks: {len(tracks)}"
        cv2.putText(
            annotated,
            banner_text,
            (12, 21),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            lineType=cv2.LINE_AA
        )

        # 2. Dibujar detecciones y badges
        for item in tracks:
            x1, y1, x2, y2 = item["bbox"]
            local_id = item["local_id"]
            global_id = item["global_id"]
            reid_sim = item.get("reid_sim", 1.0)

            color = cls.get_color_for_global_id(global_id)

            # Caja delimitadora
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2, lineType=cv2.LINE_AA)

            # Textos de etiquetas
            label_global = f"GLOBAL ID: #{global_id}"
            label_local = f"Local ID: {local_id}"

            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.45
            thickness = 1

            (w_g, h_g), _ = cv2.getTextSize(label_global, font, font_scale, thickness)
            (w_l, h_l), _ = cv2.getTextSize(label_local, font, font_scale, thickness)

            badge_w = max(w_g, w_l) + 14
            badge_h = h_g + h_l + 14

            # Posicionamiento inteligente del badge:
            # Si el sujeto está muy cerca del borde superior (o del banner), dibujamos el badge ADENTRO de la caja
            if (y1 - badge_h) < (banner_h + 4):
                badge_y1 = y1 + 4
                badge_y2 = min(h - 2, badge_y1 + badge_h)
            else:
                badge_y1 = y1 - badge_h
                badge_y2 = y1

            badge_x1 = max(0, min(x1, w - badge_w - 4))
            badge_x2 = min(w - 2, badge_x1 + badge_w)

            # Fondo del badge con borde
            cv2.rectangle(annotated, (badge_x1, badge_y1), (badge_x2, badge_y2), (20, 20, 20), -1)
            cv2.rectangle(annotated, (badge_x1, badge_y1), (badge_x2, badge_y2), color, 1, lineType=cv2.LINE_AA)

            # Texto del Global ID y Local ID
            cv2.putText(
                annotated,
                label_global,
                (badge_x1 + 6, badge_y1 + h_g + 4),
                font,
                font_scale,
                color,
                thickness,
                lineType=cv2.LINE_AA
            )
            cv2.putText(
                annotated,
                label_local,
                (badge_x1 + 6, badge_y1 + h_g + h_l + 8),
                font,
                font_scale - 0.05,
                (220, 220, 220),
                thickness,
                lineType=cv2.LINE_AA
            )

        return annotated
