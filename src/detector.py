from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from ultralytics import YOLO


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    class_id: int


class PersonDetector:
    def __init__(self, model_weight: str = "yolov8n.pt", conf_thresh: float = 0.40):
        self.conf_thresh = conf_thresh
        self.model = YOLO(model_weight)
        # Clase 0 en dataset COCO corresponde a persona
        self.target_class_id = 0

    def detect(self, frame: np.ndarray) -> List[Detection]:
        results = self.model.predict(
            source=frame,
            conf=self.conf_thresh,
            classes=[self.target_class_id],
            verbose=False,
            device="cpu"
        )

        detections: List[Detection] = []
        if not results:
            return detections

        first_res = results[0]
        boxes = first_res.boxes
        if boxes is None or len(boxes) == 0:
            return detections

        for box in boxes:
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())

            x1, y1, x2, y2 = xyxy
            # Asegurar coordenadas dentro de los limites del frame
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)

            if x2 > x1 and y2 > y1:
                detections.append(Detection(
                    bbox=(x1, y1, x2, y2),
                    confidence=conf,
                    class_id=cls_id
                ))

        return detections
