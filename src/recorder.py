import csv
from pathlib import Path
from typing import Optional, Tuple


class ResultsRecorder:
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.fieldnames = [
            "camera_id",
            "frame_idx",
            "timestamp_sec",
            "local_id",
            "global_id",
            "bbox_x1",
            "bbox_y1",
            "bbox_x2",
            "bbox_y2",
            "detector_confidence",
            "reid_similarity_score"
        ]
        self._file = open(self.output_path, mode="w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self._file, fieldnames=self.fieldnames)
        self.writer.writeheader()
        self._file.flush()

    def record(
        self,
        camera_id: str,
        frame_idx: int,
        timestamp_sec: float,
        local_id: int,
        global_id: int,
        bbox: Tuple[int, int, int, int],
        confidence: float,
        reid_similarity: float
    ):
        x1, y1, x2, y2 = bbox
        self.writer.writerow({
            "camera_id": camera_id,
            "frame_idx": frame_idx,
            "timestamp_sec": round(timestamp_sec, 3),
            "local_id": local_id,
            "global_id": global_id,
            "bbox_x1": x1,
            "bbox_y1": y1,
            "bbox_x2": x2,
            "bbox_y2": y2,
            "detector_confidence": round(confidence, 4),
            "reid_similarity_score": round(reid_similarity, 4)
        })

    def close(self):
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()
