# Sistema de Detección, Seguimiento y Reidentificación Multi-Cámara (MTMC Re-ID)

Solución de visión computacional en Python para seguimiento intra-cámara (*Single-Camera Tracking*) y reidentificación consistente de personas entre múltiples cámaras independientes (*Cross-Camera Person Re-ID*).

El sistema está diseñado para operar con flujos de video independientes, resolviendo oclusiones locales, garantizando identidades globales únicas y aplicando políticas estrictas de rechazo para evitar falsas asociaciones.

---

## 1. Arquitectura del Sistema y Componentes

El pipeline procesa cada flujo de video desacoplando la detección espacial, la persistencia temporal local y el mapeo biométrico global:

```
[ Video Stream (Cámara A / B) ]
              │
              ▼
  1. Detección de Personas (YOLOv8 Nano)
     - Filtro estricto clase 'person' (conf >= 0.35)
     - Supresión de falsos positivos
              │
              ▼
  2. Seguimiento Intra-Cámara (ByteTrack)
     - Asociación en dos etapas (detecciones altas y bajas)
     - Preservación de trayectoria ante cruces y oclusiones breves
     - Asignación de Local Track ID
              │
              ▼
  3. Extracción de Firmas Visuales (OSNet x0.25 en MSMT17)
     - Red Omni-Scale específica de Person Re-ID
     - Generación de vector d=512 normalizado en norma L2
              │
              ▼
  4. Motor de Asociación y Memoria (Cross-Camera Matcher)
     - Similitud Coseno con matriz de asignación global
     - Umbral de rechazo estricto (tau >= 0.70)
     - Ventana de confirmación y estabilización de silueta
     - Actualización exponencial protegida (EMA alpha=0.25 para sim >= 0.80)
              │
     ┌────────┴────────┐
     ▼                 ▼
[ Video Anotado ]  [ Registro CSV Auditable ]
(Local vs Global)   (Timestamp, BBox, Conf, Score)
```

### ¿Por qué estos componentes?
* **Ultralytics YOLOv8n (`src/detector.py`):** Ofrece un balance óptimo de velocidad y precisión en CPU (20-30 ms por fotograma en AMD Ryzen / Intel i5/i7). No requiere GPU dedicada para procesar flujos a ~15-20 FPS.
* **ByteTrack (`src/tracker.py`):** A diferencia de SORT básico (que descarta detecciones cuando la confianza cae por oclusión parcial), ByteTrack recupera cajas de baja confianza mediante similitud espacial (IoU), eliminando cambios innecesarios de ID (*ID switches*) cuando dos personas se cruzan.
* **OSNet x0.25 (`src/reid/extractor.py`):** Los modelos entrenados en ImageNet (como ResNet o MobileNet) clasifican categorías generales, por lo que dos personas vestidas de oscuro presentan correlaciones artificialmente altas (>0.85). **OSNet (Omni-Scale Network)** fue entrenado específicamente con *Triplet Loss* en **MSMT17** para separar individuos mediante micro-texturas (calzado, peinado, ropa) y macro-siluetas. Es ultra ligero (~2.2M parámetros, ~8.8 MB).
* **Cross-Camera Matcher con EMA (`src/reid/matcher.py`):** Gestiona la galería global. Compara candidatos mediante producto interno normalizado y protege la memoria: solo actualiza la firma de una persona si la asociación tiene alta confianza ($\ge 0.80$).

---

## 2. Requisitos e Instalación

### Requisitos del Sistema
* Python 3.10 o 3.11
* Entorno virtual (`venv` o `conda`)
* CPU multi-núcleo recomendada (funciona tanto en CPU como en GPU CUDA)

### Instalación Paso a Paso

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/rslcia11/visionComputacional.git
   cd visionComputacional
   ```

2. **Crear y activar un entorno virtual:**
   ```bash
   # Con venv:
   python -m venv venv
   # En Windows:
   .\venv\Scripts\activate
   # En Linux / macOS:
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Las dependencias principales son `torch`, `torchvision`, `ultralytics`, `opencv-python`, `scipy`, `pandas`, `tqdm` y `huggingface-hub`). Los pesos de YOLO y OSNet se descargan automáticamente en la primera ejecución.*

---

## 3. Guía de Ejecución

### Ejecución Rápida con los Videos de Prueba
Procesa los streams de Cámara A y Cámara B generando los videos anotados y el archivo CSV:
```bash
python main.py
```

### Visualización en Ventana Interactiva
Para observar las detecciones y las etiquetas de ID en tiempo real con OpenCV:
```bash
python main.py --show
```
*(Presionar la tecla `q` en la ventana para detener la visualización).*

### ¿Cómo probar con tus propios videos?
Puedes pasar cualquier par de videos usando los argumentos `--cam_a` y `--cam_b`:
```bash
python main.py --cam_a ruta/a/tu_video_camara_1.mp4 --cam_b ruta/a/tu_video_camara_2.mp4 --output_dir resultados
```

### Opciones y Parámetros Configurables
| Parámetro | Tipo | Por Defecto | Descripción |
| :--- | :---: | :---: | :--- |
| `--cam_a` | `str` | `data/raw/cam_a.mp4` | Ruta al video de la primera cámara |
| `--cam_b` | `str` | `data/raw/cam_b.mp4` | Ruta al video de la segunda cámara |
| `--output_dir` | `str` | `data/output` | Carpeta de salida para videos y CSV |
| `--reid_threshold` | `float` | `0.70` | Umbral de similitud para asociar personas entre cámaras |
| `--max_frames` | `int` | `0` | Límite de cuadros a procesar (`0` = procesar todo el video) |
| `--show` | `flag` | `False` | Abre ventana interactiva OpenCV durante el procesamiento |

---

## 4. Estructura de Entregables Generados

Tras la ejecución, la carpeta `data/output/` contiene:
1. **`cam_a_annotated.mp4`:** Video procesado de Cámara A (Pasillo CCTV-01) con bounding boxes, `Local ID` y `GLOBAL ID`.
2. **`cam_b_annotated.mp4`:** Video procesado de Cámara B (Salón CCTV-02) con el seguimiento y las reidentificaciones correspondientes.
3. **`detections_and_associations.csv`:** Registro estructurado auditable de cada inferencia:
   ```csv
   camera_id,frame_idx,timestamp_sec,local_id,global_id,bbox_x1,bbox_y1,bbox_x2,bbox_y2,detector_confidence,reid_similarity_score
   cam_a,25,2.083,1,1,389,83,494,282,0.8852,1.0
   cam_b,176,14.667,2,2,305,42,540,420,0.9140,0.7058
   ```
4. **`evidence/`:** Capturas de fotogramas clave certificando las asociaciones y la ausencia de colisiones.

---

## 5. Pruebas Automatizadas

El proyecto incluye suites de pruebas unitarias y de estrés para validar el pipeline numérico:

```bash
# 1. Pruebas de integración y dimensiones de embeddings
python tests/test_pipeline.py

# 2. Pruebas de estrés (invarianza lumínica, tolerancia a ruido y rechazo estricto)
python tests/test_stress_and_edge_cases.py
```

Ambas pruebas certifican:
* Invarianza de embeddings ante penumbra (-40% iluminación) y transformaciones afines.
* Rechazo estricto de falsos positivos en personas no coincidentes (similitud $< 0.50$).
* Estabilidad temporal de la galería bajo actualización adaptativa EMA.

---

## 6. Estructura del Repositorio

```text
├── src/
│   ├── detector.py          # Inferencia y filtrado YOLOv8 Nano
│   ├── tracker.py           # Tracker intra-cámara ByteTrack
│   ├── recorder.py          # Registro CSV estructurado
│   ├── visualizer.py        # Anotador de video con paleta cromática de IDs
│   └── reid/
│       ├── extractor.py     # Extractor de embeddings OSNet x0.25 (MSMT17)
│       ├── matcher.py       # Motor de asociación inter-cámara y galería EMA
│       └── osnet_model.py   # Arquitectura Omni-Scale Network en PyTorch
├── scripts/
│   ├── create_fixed_cctv_scenario.py # Generador del benchmark continuo
│   └── extract_evidence_frames.py    # Extracción de fotogramas de auditoría
├── tests/
│   ├── test_pipeline.py              # Pruebas unitarias de flujo
│   └── test_stress_and_edge_cases.py # Pruebas de estrés y casos límite
├── data/
│   ├── raw/                 # Videos de entrada (cam_a.mp4 y cam_b.mp4)
│   └── output/              # Videos renderizados y CSV auditable
├── requirements.txt         # Dependencias de Python
└── main.py                  # CLI y orquestador principal
```

---

## 7. Referencias

* **OSNet:** Zhou et al., *"Omni-Scale Feature Learning for Person Re-Identification"*, ICCV 2019.
* **ByteTrack:** Zhang et al., *"ByteTrack: Multi-Object Tracking by Associating Every Detection Box"*, ECCV 2022.
* **YOLOv8:** Ultralytics, *"Real-Time Flying Object and Person Detection"*, 2023.

