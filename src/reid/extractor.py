from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np
import torch
from torchvision import transforms
from huggingface_hub import hf_hub_download

from src.reid.osnet_model import osnet_x0_25


class AppearanceFeatureExtractor:
    """
    Extractor de caracteristicas de apariencia para reidentificacion de personas (Person Re-ID).
    Utiliza el estado del arte (SOTA): Omni-Scale Network (OSNet x0.25)
    preentrenado en MSMT17 (Multi-Scene Multi-Time Person Re-ID).

    Produce embeddings de 512 dimensiones normalizados en norma L2.
    """
    def __init__(self, device: str = "cpu", weights_path: Optional[str] = None):
        self.device = torch.device(device)

        # 1. Cargar pesos oficiales de OSNet x0.25 entrenados en MSMT17
        if weights_path is None:
            weights_path = hf_hub_download(
                repo_id="kaiyangzhou/osnet",
                filename="osnet_x0_25_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth"
            )

        checkpoint = torch.load(weights_path, map_location=self.device)
        num_classes = checkpoint.get("classifier.weight", torch.zeros(4101, 512)).shape[0]

        self.model = osnet_x0_25(num_classes=num_classes, pretrained=False)
        self.model.load_state_dict(checkpoint)
        self.model.eval()
        self.model.to(self.device)

        # Preprocesamiento estandar SOTA para Re-ID (256x128)
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((256, 128)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    @torch.no_grad()
    def extract(self, crops: List[np.ndarray]) -> np.ndarray:
        if not crops:
            return np.empty((0, 512), dtype=np.float32)

        tensors = []
        for crop in crops:
            h, w = crop.shape[:2]
            if h < 8 or w < 8:
                continue

            rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            tensors.append(self.transform(rgb_crop))

        if not tensors:
            return np.empty((0, 512), dtype=np.float32)

        batch_tensor = torch.stack(tensors).to(self.device)
        embeddings = self.model(batch_tensor).cpu().numpy()

        # Normalizacion L2 estricta de 512 dimensiones
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms < 1e-6] = 1.0
        embeddings = embeddings / norms

        return embeddings.astype(np.float32)
