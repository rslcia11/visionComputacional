from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment


@dataclass
class GlobalIdentity:
    global_id: int
    embedding: np.ndarray  # Vector normalizado en norma L2
    cameras_seen: Set[str] = field(default_factory=set)
    local_ids_mapped: Dict[str, Set[int]] = field(default_factory=dict)
    sample_count: int = 1


class CrossCameraMatcher:
    def __init__(
        self,
        similarity_threshold: float = 0.70,
        same_camera_threshold: float = 0.82,
        ema_alpha: float = 0.25
    ):
        self.similarity_threshold = similarity_threshold
        self.same_camera_threshold = same_camera_threshold
        self.ema_alpha = ema_alpha
        self.next_global_id = 1
        self.gallery: Dict[int, GlobalIdentity] = {}
        # Mapeo: (camera_id, local_track_id) -> (global_id, score_similitud)
        self.local_to_global: Dict[Tuple[str, int], Tuple[int, float]] = {}

    def get_global_id(self, camera_id: str, local_track_id: int) -> Optional[int]:
        key = (camera_id, local_track_id)
        if key in self.local_to_global:
            return self.local_to_global[key][0]
        return None

    def get_association_confidence(self, camera_id: str, local_track_id: int) -> float:
        key = (camera_id, local_track_id)
        if key in self.local_to_global:
            return self.local_to_global[key][1]
        return 1.0

    def associate_or_register(
        self,
        camera_id: str,
        local_track_id: int,
        feature_vector: np.ndarray,
        currently_active_local_ids: Optional[Set[int]] = None
    ) -> int:
        key = (camera_id, local_track_id)

        # Normalizar vector entrante
        norm = np.linalg.norm(feature_vector)
        if norm > 1e-6:
            feature_vector = feature_vector / norm

        # 1. Si ya está mapeado este track local, actualizar embedding con EMA
        if key in self.local_to_global:
            assigned_gid, initial_score = self.local_to_global[key]
            identity = self.gallery[assigned_gid]

            updated = (1.0 - self.ema_alpha) * identity.embedding + self.ema_alpha * feature_vector
            updated_norm = np.linalg.norm(updated)
            if updated_norm > 1e-6:
                identity.embedding = updated / updated_norm
            identity.sample_count += 1

            # Si el track nació como ID nuevo (initial_score == 1.0) y aún está en ventana de calentamiento (<= 15 frames),
            # reevaluar si ahora con la silueta completa supera el umbral inter-cámara con otra identidad
            if initial_score == 1.0 and identity.sample_count <= 15:
                best_match_gid = None
                best_match_sim = -1.0
                for gid, other_identity in self.gallery.items():
                    if gid == assigned_gid:
                        continue
                    # Solo considerar identidades que provengan de otra cámara
                    if any(c != camera_id for c in other_identity.cameras_seen):
                        sim = float(np.dot(other_identity.embedding, feature_vector))
                        if sim >= self.similarity_threshold and sim > best_match_sim:
                            best_match_sim = sim
                            best_match_gid = gid

                if best_match_gid is not None:
                    # Promover y unificar con la identidad global existente
                    del self.gallery[assigned_gid]
                    self.local_to_global[key] = (best_match_gid, best_match_sim)
                    target_identity = self.gallery[best_match_gid]
                    target_identity.cameras_seen.add(camera_id)
                    if camera_id not in target_identity.local_ids_mapped:
                        target_identity.local_ids_mapped[camera_id] = set()
                    target_identity.local_ids_mapped[camera_id].add(local_track_id)
                    merged = (1.0 - self.ema_alpha) * target_identity.embedding + self.ema_alpha * identity.embedding
                    target_identity.embedding = merged / np.linalg.norm(merged)
                    return best_match_gid

            return assigned_gid

        # 2. Búsqueda de coincidencias candidatas
        best_gid: Optional[int] = None
        best_sim = -1.0

        for gid, identity in self.gallery.items():
            # Si el Global ID ya está activo simultáneamente en esta cámara, descartar
            # (una persona no puede estar en dos lugares a la vez en la misma cámara)
            if currently_active_local_ids and camera_id in identity.local_ids_mapped:
                if identity.local_ids_mapped[camera_id].intersection(currently_active_local_ids):
                    continue

            sim = float(np.dot(identity.embedding, feature_vector))

            # ¿Es una identidad de OTRA cámara o de la MISMA cámara?
            is_from_other_camera = any(c != camera_id for c in identity.cameras_seen)
            required_threshold = (
                self.similarity_threshold if is_from_other_camera else self.same_camera_threshold
            )

            if sim >= required_threshold and sim > best_sim:
                best_sim = sim
                best_gid = gid

        # 3. Si hay coincidencia que supera el umbral riguroso, asociar
        if best_gid is not None:
            self.local_to_global[key] = (best_gid, best_sim)
            identity = self.gallery[best_gid]
            identity.cameras_seen.add(camera_id)
            if camera_id not in identity.local_ids_mapped:
                identity.local_ids_mapped[camera_id] = set()
            identity.local_ids_mapped[camera_id].add(local_track_id)

            # EMA update con la nueva observacion (solo si confianza es solida)
            if best_sim >= 0.80:
                updated = (1.0 - self.ema_alpha) * identity.embedding + self.ema_alpha * feature_vector
                identity.embedding = updated / np.linalg.norm(updated)
            identity.sample_count += 1
            return best_gid


        # 4. Si no supera el umbral, registrar nueva identidad global
        new_gid = self.next_global_id
        self.next_global_id += 1

        new_identity = GlobalIdentity(
            global_id=new_gid,
            embedding=feature_vector.copy(),
            cameras_seen={camera_id},
            local_ids_mapped={camera_id: {local_track_id}},
            sample_count=1
        )
        self.gallery[new_gid] = new_identity
        self.local_to_global[key] = (new_gid, 1.0)  # Nueva identidad, score 1.0
        return new_gid
