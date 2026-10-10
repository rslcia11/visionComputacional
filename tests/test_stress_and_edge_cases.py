import sys
from pathlib import Path
import cv2
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.detector import PersonDetector
from src.tracker import CameraTracker
from src.reid.extractor import AppearanceFeatureExtractor
from src.reid.matcher import CrossCameraMatcher, GlobalIdentity


def generate_synthetic_person_image(shirt_color: tuple, pants_color: tuple, noise_level: float = 0.0) -> np.ndarray:
    """Genera una imagen sintetica estandarizada de 256x128 con regiones de torso y piernas."""
    img = np.ones((256, 128, 3), dtype=np.uint8) * 180  # Fondo claro

    # Cabeza: 15% superior
    cv2.circle(img, (64, 25), 18, (190, 160, 140), -1)

    # Torso: 40% de altura
    cv2.rectangle(img, (28, 45), (100, 145), shirt_color, -1)

    # Piernas: 45% de altura
    cv2.rectangle(img, (32, 145), (60, 240), pants_color, -1)
    cv2.rectangle(img, (68, 145), (96, 240), pants_color, -1)

    if noise_level > 0.0:
        noise = np.random.normal(0, noise_level * 255, img.shape).astype(np.int16)
        noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        return noisy

    return img


def test_case_1_scale_and_illumination_invariance():
    """
    TEST 1: Invarianza ante variaciones severas de iluminación y escala.
    La misma persona (camisa roja, pantalón azul) observada con:
    a) Iluminación normal
    b) 40% menos de brillo (penumbra)
    c) Escala reducida a la mitad (lejos de la cámara)
    d) Ruido gaussiano de compresión
    """
    print("\n--- [TEST 1] Invarianza de Re-ID ante Escala, Iluminación y Ruido ---")
    extractor = AppearanceFeatureExtractor(device="cpu")

    person_base = generate_synthetic_person_image(shirt_color=(40, 40, 210), pants_color=(180, 50, 40))

    # 1. Variación de iluminación (40% más oscura)
    person_dark = (person_base.astype(np.float32) * 0.6).astype(np.uint8)

    # 2. Variación de escala (resize a 50% y luego escalado para simular persona lejana)
    h, w = person_base.shape[:2]
    small = cv2.resize(person_base, (w // 2, h // 2))
    person_scaled = cv2.resize(small, (w, h))

    # 3. Ruido de sensor y compresión de video (5% de desviación estándar)
    person_noisy = generate_synthetic_person_image(shirt_color=(40, 40, 210), pants_color=(180, 50, 40), noise_level=0.05)

    # 4. Persona totalmente diferente (camisa verde, pantalón negro)
    person_different = generate_synthetic_person_image(shirt_color=(30, 190, 40), pants_color=(20, 20, 20))

    features = extractor.extract([person_base, person_dark, person_scaled, person_noisy, person_different])
    assert features.shape == (5, 512), "Dimensión incorrecta de embeddings"

    emb_base = features[0]
    emb_dark = features[1]
    emb_scaled = features[2]
    emb_noisy = features[3]
    emb_diff = features[4]

    sim_dark = float(np.dot(emb_base, emb_dark))
    sim_scaled = float(np.dot(emb_base, emb_scaled))
    sim_noisy = float(np.dot(emb_base, emb_noisy))
    sim_diff = float(np.dot(emb_base, emb_diff))

    print(f"  Similitud con versión oscura (-40% luz)   : {sim_dark:.4f}")
    print(f"  Similitud con versión lejana (baja escala): {sim_scaled:.4f}")
    print(f"  Similitud con versión ruidosa (+ruido)    : {sim_noisy:.4f}")
    print(f"  Similitud con OTRA persona (verde/negro)  : {sim_diff:.4f}")

    assert sim_dark > 0.70, "Fallo: El modelo no toleró la penumbra"
    assert sim_scaled > 0.70, "Fallo: El modelo no toleró la reducción de escala"
    assert sim_noisy > 0.70, "Fallo: El modelo no toleró el ruido"
    assert sim_diff < 0.70, f"Fallo: El modelo no discriminó a la persona diferente bajo el umbral de 0.70 (sim={sim_diff:.4f})"
    assert (sim_dark - sim_diff) > 0.20, "Margen de separación insuficiente entre misma persona y diferente"
    print("  => PASÓ: Invarianza robusta y margen de discriminación confirmado.")



def test_case_2_strict_rejection_policy_no_forced_matching():
    print("\n--- [TEST 2] Política de Rechazo Estricta (Zero Forced Matches) ---")
    matcher = CrossCameraMatcher(similarity_threshold=0.62)

    # Población Cámara A: 3 personas
    cam_a_people = [
        np.array([1.0, 0.0, 0.0] + [0.0]*509, dtype=np.float32),
        np.array([0.0, 1.0, 0.0] + [0.0]*509, dtype=np.float32),
        np.array([0.0, 0.0, 1.0] + [0.0]*509, dtype=np.float32),
    ]
    for i, emb in enumerate(cam_a_people, start=1):
        gid = matcher.associate_or_register("cam_a", local_track_id=i, feature_vector=emb)
        assert gid == i, f"Error al registrar persona {i} en Cam A"

    print("  Registradas 3 personas en Cámara A -> Global IDs asignados: 1, 2, 3")

    # Población Cámara B: 3 personas completamente distintas (vectores ortogonales)
    cam_b_new_people = [
        np.array([0.0, 0.0, 0.0, 1.0] + [0.0]*508, dtype=np.float32),
        np.array([0.0, 0.0, 0.0, 0.0, 1.0] + [0.0]*507, dtype=np.float32),
        np.array([0.0, 0.0, 0.0, 0.0, 0.0, 1.0] + [0.0]*506, dtype=np.float32),
    ]

    for j, emb in enumerate(cam_b_new_people, start=10):
        gid = matcher.associate_or_register("cam_b", local_track_id=j, feature_vector=emb)
        assert gid not in [1, 2, 3], f"ERROR CRÍTICO: Asociación forzada de persona {j} a ID {gid}"

    assert len(matcher.gallery) == 6, f"Esperadas 6 identidades globales, encontradas {len(matcher.gallery)}"
    print("  => PASÓ: Cero asociaciones forzadas. Todas las personas nuevas recibieron IDs únicos.")


def test_case_3_bipartite_matching_with_cross_overlapping():
    print("\n--- [TEST 3] Asignación Bipartita y Desambiguación Inter-Cámara ---")
    matcher = CrossCameraMatcher(similarity_threshold=0.62)

    vec_p1 = np.random.randn(512).astype(np.float32)
    vec_p1 /= np.linalg.norm(vec_p1)

    vec_p2 = np.random.randn(512).astype(np.float32)
    vec_p2 = vec_p2 - np.dot(vec_p2, vec_p1) * vec_p1
    vec_p2 /= np.linalg.norm(vec_p2)

    vec_p3 = np.random.randn(512).astype(np.float32)
    vec_p3 = vec_p3 - np.dot(vec_p3, vec_p1) * vec_p1 - np.dot(vec_p3, vec_p2) * vec_p2
    vec_p3 /= np.linalg.norm(vec_p3)

    # Registro en Cámara A
    gid_p1_a = matcher.associate_or_register("cam_a", local_track_id=1, feature_vector=vec_p1)
    gid_p2_a = matcher.associate_or_register("cam_a", local_track_id=2, feature_vector=vec_p2)

    # En Cámara B aparecen con leve ruido de observación (ruido unitario escalado al 8%)
    noise_2 = np.random.randn(512).astype(np.float32)
    noise_2 /= np.linalg.norm(noise_2)
    noisy_p2 = 0.92 * vec_p2 + 0.08 * noise_2
    noisy_p2 /= np.linalg.norm(noisy_p2)

    noise_1 = np.random.randn(512).astype(np.float32)
    noise_1 /= np.linalg.norm(noise_1)
    noisy_p1 = 0.92 * vec_p1 + 0.08 * noise_1
    noisy_p1 /= np.linalg.norm(noisy_p1)

    # Entran en orden invertido en Cam B: P2, luego P3 (nueva), luego P1
    gid_p2_b = matcher.associate_or_register("cam_b", local_track_id=50, feature_vector=noisy_p2)
    gid_p3_b = matcher.associate_or_register("cam_b", local_track_id=51, feature_vector=vec_p3)
    gid_p1_b = matcher.associate_or_register("cam_b", local_track_id=52, feature_vector=noisy_p1)

    print(f"  P1: Cam A id=1 -> GID={gid_p1_a} | Cam B id=52 -> GID={gid_p1_b}")
    print(f"  P2: Cam A id=2 -> GID={gid_p2_a} | Cam B id=50 -> GID={gid_p2_b}")
    print(f"  P3 (Nueva): Cam B id=51 -> GID={gid_p3_b}")

    assert gid_p1_b == gid_p1_a, "Fallo: P1 no fue reidentificada correctamente en Cam B"
    assert gid_p2_b == gid_p2_a, "Fallo: P2 no fue reidentificada correctamente en Cam B"
    assert gid_p3_b not in [gid_p1_a, gid_p2_a], "Fallo: Persona nueva P3 fue asociada incorrectamente a P1 o P2"
    print("  => PASÓ: Mapeo inter-cámara biunívoco exacto.")


def test_case_4_ema_temporal_drift_stability():
    print("\n--- [TEST 4] Estabilidad Temporal de la Memoria Visual (Filtro EMA) ---")
    matcher = CrossCameraMatcher(similarity_threshold=0.62, ema_alpha=0.20)

    base_vector = np.random.randn(512).astype(np.float32)
    base_vector /= np.linalg.norm(base_vector)

    gid = matcher.associate_or_register("cam_a", local_track_id=1, feature_vector=base_vector)

    for frame in range(150):
        # En video real, cada fotograma es una observación ruidosa de la apariencia verdadera
        noise_t = np.random.randn(512).astype(np.float32)
        noise_t /= np.linalg.norm(noise_t)
        frame_obs = 0.94 * base_vector + 0.06 * noise_t
        frame_obs /= np.linalg.norm(frame_obs)
        matcher.associate_or_register("cam_a", local_track_id=1, feature_vector=frame_obs)

    final_gallery_emb = matcher.gallery[gid].embedding
    cos_sim_initial_vs_final = float(np.dot(base_vector, final_gallery_emb))

    print(f"  Similitud entre embedding inicial y tras 150 frames de caminata: {cos_sim_initial_vs_final:.4f}")
    assert cos_sim_initial_vs_final > 0.85, "Fallo: El filtro EMA sufrió deriva temporal excesiva (drift)"
    print("  => PASÓ: Memoria visual ultra-estable sin degradación.")


def test_case_5_zero_detection_and_empty_scenes():
    print("\n--- [TEST 5] Manejo Robusto de Escenas Vacías y Degradadas ---")
    extractor = AppearanceFeatureExtractor(device="cpu")
    matcher = CrossCameraMatcher(similarity_threshold=0.62)

    empty_feat = extractor.extract([])
    assert empty_feat.shape == (0, 512), "Fallo: No manejó lista vacía"

    tiny_crops = [np.zeros((4, 4, 3), dtype=np.uint8), np.ones((2, 2, 3), dtype=np.uint8)]
    res = extractor.extract(tiny_crops)
    assert res.shape == (0, 512), "Fallo: No filtró recortes no válidos"


    print("  => PASÓ: Resiliencia comprobada ante entradas vacías o corruptas.")


if __name__ == "__main__":
    print("=" * 75)
    print("  SUITE DE PRUEBAS DE ESTRÉS Y CASOS LÍMITE (HARD EDGE CASES)")
    print("=" * 75)
    test_case_1_scale_and_illumination_invariance()
    test_case_2_strict_rejection_policy_no_forced_matching()
    test_case_3_bipartite_matching_with_cross_overlapping()
    test_case_4_ema_temporal_drift_stability()
    test_case_5_zero_detection_and_empty_scenes()
    print("\n" + "=" * 75)
    print("  TODAS LAS PRUEBAS DE ESTRÉS Y CASOS LÍMITE PASARON AL 100%")
    print("=" * 75)
