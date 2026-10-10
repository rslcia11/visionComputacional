from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
from ultralytics import YOLO


@dataclass
class TrackedPerson:
    track_id: int
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float


class CameraTracker:
    def __init__(
        self,
        camera_id: str,
        model_weight: str = "yolov8n.pt",
        tracker_config: str = "bytetrack.yaml",
        conf_thresh: float = 0.35
    ):
        self.camera_id = camera_id
        self.conf_thresh = conf_thresh
        self.tracker_config = tracker_config
        self.model = YOLO(model_weight)

    def update(self, frame: np.ndarray) -> List[TrackedPerson]:
        results = self.model.track(
            source=frame,
            persist=True,
            tracker=self.tracker_config,
            classes=[0],  # Solo clase persona
            conf=self.conf_thresh,
            verbose=False,
            device="cpu"
        )

        tracked_people: List[TrackedPerson] = []
        if not results:
            return tracked_people

        first_res = results[0]
        boxes = first_res.boxes
        if boxes is None or len(boxes) == 0 or boxes.id is None:
            return tracked_people

        ids = boxes.id.cpu().numpy().astype(int)
        xyxys = boxes.xyxy.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy().astype(float)

        h, w = frame.shape[:2]
        for trk_id, xyxy, conf in zip(ids, xyxys, confs):
            x1, y1, x2, y2 = xyxy
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)

            if x2 > x1 and y2 > y1:
                tracked_people.append(TrackedPerson(
                    track_id=int(trk_id),
                    bbox=(x1, y1, x2, y2),
                    confidence=float(conf)
                ))

        return tracked_people
