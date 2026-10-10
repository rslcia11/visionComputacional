import sys
from pathlib import Path
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.reid.extractor import AppearanceFeatureExtractor
from src.reid.matcher import CrossCameraMatcher


def test_feature_extractor_dimension_and_normalization():
    extractor = AppearanceFeatureExtractor(device="cpu")
    # Simular dos recortes de peatones
    dummy_crop_1 = np.random.randint(0, 255, (200, 100, 3), dtype=np.uint8)
    dummy_crop_2 = np.random.randint(0, 255, (180, 90, 3), dtype=np.uint8)

    features = extractor.extract([dummy_crop_1, dummy_crop_2])

    assert features.shape == (2, 512)
    # Norma de cada vector debe ser cercana a 1.0 (normalizado L2)
    norms = np.linalg.norm(features, axis=1)
    assert np.allclose(norms, [1.0, 1.0], atol=1e-3)


def test_cross_camera_matcher_associations_and_rejections():
    matcher = CrossCameraMatcher(similarity_threshold=0.70)

    # Embedding base para Persona A en Camara 1
    base_vec = np.random.randn(512).astype(np.float32)
    base_vec /= np.linalg.norm(base_vec)

    # 1. Registrar Persona A en Cam A
    gid_1 = matcher.associate_or_register("cam_a", local_track_id=101, feature_vector=base_vec)
    assert gid_1 == 1

    # 2. Embedding similar (Persona A en Cam B con >0.85 similitud)
    noise = np.random.randn(512).astype(np.float32)
    noise /= np.linalg.norm(noise)
    similar_vec = 0.9 * base_vec + 0.1 * noise
    similar_vec /= np.linalg.norm(similar_vec)

    gid_matched = matcher.associate_or_register("cam_b", local_track_id=201, feature_vector=similar_vec)
    # Debe asociarse al mismo ID global
    assert gid_matched == 1
    assert "cam_b" in matcher.gallery[1].cameras_seen

    # 3. Persona diferente en Cam B
    diff_vec = np.random.randn(512).astype(np.float32)
    diff_vec = diff_vec - np.dot(diff_vec, base_vec) * base_vec
    diff_vec /= np.linalg.norm(diff_vec)

    gid_different = matcher.associate_or_register("cam_b", local_track_id=202, feature_vector=diff_vec)
    # No debe forzar asociacion; debe crear un nuevo ID global
    assert gid_different == 2
    assert matcher.gallery[2].cameras_seen == {"cam_b"}


if __name__ == "__main__":
    test_feature_extractor_dimension_and_normalization()
    test_cross_camera_matcher_associations_and_rejections()
    print("Pruebas unitarias completadas con exito.")
