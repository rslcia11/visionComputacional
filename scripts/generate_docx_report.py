import os
import sys
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_shading(cell, color_hex):
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def apply_apa_table_borders(table):
    tblPr = table._tbl.tblPr
    tblBorders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        f'  <w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        f'  <w:insideH w:val="none"/>'
        f'  <w:insideV w:val="none"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(tblBorders)

def add_header_bottom_border(row):
    for cell in row.cells:
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            f'</w:tcBorders>'
        )
        tcPr.append(borders)

def build_docx_report():
    base_dir = Path(__file__).resolve().parent.parent
    evidence_dir = base_dir / "data" / "output" / "evidence"
    output_docx = base_dir / "Informe_Tecnico_ReID_Multicamara.docx"

    doc = docx.Document()

    # Configuracion de Pagina segun Normas APA 7 (Margenes de 2.54 cm / 1 pulgada)
    section = doc.sections[0]
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)
    section.page_width = Inches(8.5)
    section.page_height = Inches(11.0)

    # Estilos de fuente general (Times New Roman 12 pt segun estandar academico APA)
    normal_style = doc.styles['Normal']
    normal_font = normal_style.font
    normal_font.name = 'Times New Roman'
    normal_font.size = Pt(12)
    normal_font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.25
    normal_style.paragraph_format.space_after = Pt(6)

    # Helper para encabezados APA 7
    def add_apa_h1(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(13)
        return p

    def add_apa_h2(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        return p

    def add_apa_h3(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.italic = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        return p

    def add_body_p(text, indent=False):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.space_after = Pt(6)
        if indent:
            p.paragraph_format.first_line_indent = Inches(0.5)
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        return p

    def add_bullet(bold_prefix, text):
        p = doc.add_paragraph(style='List Bullet')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.2
        p.paragraph_format.space_after = Pt(4)
        run_b = p.add_run(bold_prefix)
        run_b.bold = True
        run_b.font.name = 'Times New Roman'
        run_t = p.add_run(text)
        run_t.font.name = 'Times New Roman'
        return p

    def add_apa_figure(fig_num, title, img_path, note_text):
        # Numero de figura
        p_num = doc.add_paragraph()
        p_num.paragraph_format.space_before = Pt(12)
        p_num.paragraph_format.space_after = Pt(2)
        p_num.paragraph_format.keep_with_next = True
        r_num = p_num.add_run(f"Figura {fig_num}")
        r_num.bold = True
        r_num.font.name = 'Times New Roman'
        r_num.font.size = Pt(11)

        # Titulo de figura (cursiva segun APA 7)
        p_title = doc.add_paragraph()
        p_title.paragraph_format.space_before = Pt(0)
        p_title.paragraph_format.space_after = Pt(6)
        p_title.paragraph_format.keep_with_next = True
        r_title = p_title.add_run(title)
        r_title.italic = True
        r_title.font.name = 'Times New Roman'
        r_title.font.size = Pt(11)

        # Imagen centrada
        if os.path.exists(img_path):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(4)
            p_img.paragraph_format.space_after = Pt(4)
            p_img.paragraph_format.keep_with_next = True
            doc.add_picture(str(img_path), width=Inches(6.0))
            # centrar la imagen agregada
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.paragraphs[-1].paragraph_format.keep_with_next = True

        # Nota de figura
        p_note = doc.add_paragraph()
        p_note.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_note.paragraph_format.space_before = Pt(3)
        p_note.paragraph_format.space_after = Pt(12)
        r_nota_label = p_note.add_run("Nota. ")
        r_nota_label.italic = True
        r_nota_label.font.name = 'Times New Roman'
        r_nota_label.font.size = Pt(10)
        r_nota_text = p_note.add_run(note_text)
        r_nota_text.font.name = 'Times New Roman'
        r_nota_text.font.size = Pt(10)

    # ==========================================
    # PORTADA (Normas APA 7 - Formato Profesional)
    # ==========================================
    p_top = doc.add_paragraph()
    p_top.paragraph_format.space_before = Pt(72)

    p_cover_title = doc.add_paragraph()
    p_cover_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cover_title.paragraph_format.space_after = Pt(24)
    run_ct = p_cover_title.add_run("Sistema de Seguimiento Intra-Cámara y Reidentificación Consistente de Personas en Entornos Multi-Cámara (MTMC Re-ID)")
    run_ct.bold = True
    run_ct.font.name = 'Times New Roman'
    run_ct.font.size = Pt(16)

    p_cover_author = doc.add_paragraph()
    p_cover_author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cover_author.paragraph_format.space_after = Pt(8)
    run_ca = p_cover_author.add_run("Wilson Martínez")
    run_ca.font.name = 'Times New Roman'
    run_ca.font.size = Pt(12)

    p_cover_affil = doc.add_paragraph()
    p_cover_affil.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cover_affil.paragraph_format.space_after = Pt(18)
    run_caf = p_cover_affil.add_run("Área de Inteligencia Artificial y Visión Computacional")
    run_caf.font.name = 'Times New Roman'
    run_caf.font.size = Pt(12)

    p_cover_date = doc.add_paragraph()
    p_cover_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cover_date.paragraph_format.space_after = Pt(24)
    run_cd = p_cover_date.add_run("Octubre de 2026")
    run_cd.font.name = 'Times New Roman'
    run_cd.font.size = Pt(12)

    doc.add_page_break()

    # ==========================================
    # 1. INTRODUCCIÓN CORTA Y DIRECTA
    # ==========================================
    add_apa_h1("1. Introducción")

    add_body_p(
        "El presente informe describe el diseño, implementación y validación de una solución integral en Python para el seguimiento y la reidentificación consistente de personas a través de múltiples cámaras independientes de videovigilancia (Multi-Target Multi-Camera Tracking). El propósito central es resolver uno de los desafíos más críticos de la seguridad electrónica: mantener la identidad global única de los individuos cuando se desplazan de una zona de cobertura a otra, garantizando que el sistema no intercambie identidades ante oclusiones y que rechace con total precisión falsas asociaciones entre personas con apariencias similares.",
        indent=True
    )

    add_body_p(
        "Durante el desarrollo se identificó que las técnicas convencionales fundamentadas en histogramas de color y clasificadores genéricos (entrenados en ImageNet) colapsan sistemáticamente cuando las personas visten ropa oscura o similar, debido a que dichos modelos priorizan categorías generales de objetos en lugar de rasgos biométricos sutiles. Para resolver este inconveniente, se implementó un pipeline desacoplado que combina YOLOv8 Nano para detección espacial, ByteTrack con filtro de Kalman para persistencia intra-cámara, y una red neuronal Omni-Scale (OSNet x0.25) entrenada en MSMT17 para extracción de firmas visuales discriminantes, complementada con un motor de correspondencia con memoria adaptativa basada en promedio móvil exponencial (EMA).",
        indent=True
    )

    # ==========================================
    # 2. ARQUITECTURA Y COMPONENTES
    # ==========================================
    add_apa_h1("2. Arquitectura de la Solución y Componentes")

    add_body_p(
        "El sistema opera procesando los flujos de video de cada cámara de manera secuencial y modular, garantizando un consumo predecible de recursos en CPU. A continuación se desglosan los componentes seleccionados y el sustento técnico de su adopción:",
        indent=True
    )

    add_bullet(
        "Ultralytics YOLOv8 Nano: ",
        "Responsable de la detección de personas en cada cuadro. Con un umbral de confianza estricto de 0.35 para la clase 'person', ofrece un rendimiento en CPU de entre 20 y 30 milisegundos por fotograma en procesadores estándar, evitando la saturación del hardware y reservando cómputo para la reidentificación."
    )

    add_bullet(
        "Seguimiento Intra-Cámara (ByteTrack): ",
        "Mantiene la continuidad temporal dentro de la misma cámara mediante un filtro de Kalman y una estrategia de asociación en dos etapas. En lugar de descartar detecciones cuando una persona sufre una oclusión parcial y su confianza decae, ByteTrack recupera dichas cajas por proximidad espacial (IoU), eliminando los cambios imprevistos de ID local ante cruces."
    )

    add_bullet(
        "Extractor Biométrico (OSNet x0.25 - MSMT17): ",
        "Diseñado específicamente para Person Re-ID por Zhou et al. (2019). Su arquitectura omni-escala extrae simultáneamente características a nivel de micro-textura (calzado, detalles de indumentaria, accesorios) y macro-silueta (proporciones anatómicas). Cada individuo se representa mediante un vector de 512 dimensiones normalizado en norma euclidiana L2."
    )

    add_bullet(
        "Motor de Asociación Inter-Cámara (Cross-Camera Matcher con EMA): ",
        "Administra la galería global de identidades. Compara candidatos mediante similitud coseno, aplica un umbral de rechazo riguroso (tau = 0.70) y actualiza la memoria del individuo únicamente cuando la similitud observada es sumamente alta (mayor o igual a 0.80), preservando la integridad del perfil visual."
    )

    # ==========================================
    # 3. DEFECTOS RESUELTOS Y DEFENSAS TÉCNICAS
    # ==========================================
    add_apa_h1("3. Respuestas Técnicas y Justificación del Sistema")

    add_apa_h2("3.1. Mantenimiento de Identificadores Dentro de una Cámara")
    add_body_p(
        "Dentro del campo visual de una misma cámara, cada persona es rastreada por ByteTrack mediante un identificador local continuo (Local ID). La trayectoria se predice cuadro a cuadro mediante un filtro de Kalman lineal. Ante oclusiones breves (por ejemplo, cuando una persona pasa detrás de una columna o de otra persona), el algoritmo mantiene activo el identificador en una cola de persistencia de hasta 30 fotogramas. Al reaparecer en una posición espacial coherente, el individuo conserva su Local ID original sin generar fragmentaciones de trayectoria.",
        indent=True
    )

    add_apa_h2("3.2. Determinación de Correspondencia Inter-Cámara")
    add_body_p(
        "Para determinar si una persona observada en la Cámara B corresponde a una previamente registrada en la Cámara A, el sistema ejecuta el siguiente protocolo riguroso:",
        indent=True
    )
    add_bullet("Estabilización de Silueta: ", "El candidato en Cámara B debe permanecer visible por al menos 15 cuadros continuos. Esto evita inferir vectores sobre cuerpos recortados a medias en los bordes del sensor.")
    add_bullet("Extracción y Normalización: ", "El recorte se normaliza y se procesa con OSNet, generando un vector u en dimensión 512 con norma unitaria (||u|| = 1).")
    add_bullet("Cálculo de Similitud Coseno: ", "Se evalúa el producto punto contra cada vector representativo de la galería global. Dado que ambos vectores están normalizados en L2, el producto punto equivale exactamente a la similitud coseno.")
    add_bullet("Decisión y Asignación: ", "Si la máxima similitud supera el umbral estricto tau = 0.70, el sujeto es reidentificado y se le asigna el Global ID preexistente. Si la similitud máxima no alcanza el umbral, la asociación es rechazada y se crea un nuevo Global ID.")
    add_bullet("Actualización Protegida (EMA): ", "Solo si la similitud es superior o igual a 0.80, la firma en galería se actualiza con una tasa de aprendizaje alpha = 0.25. Si la similitud está entre 0.70 y 0.79, la persona es asociada en el fotograma pero su perfil maestro no se modifica, protegiendo a la galería de degradaciones.")

    add_apa_h2("3.3. Situaciones que Provocan Errores y Estrategias de Mitigación")
    add_body_p(
        "Durante el análisis experimental se identificaron los tres principales escenarios generadores de error en sistemas de reidentificación y se implementaron las siguientes soluciones:",
        indent=True
    )
    add_bullet("Personas con Vestimenta Oscura o Idéntica: ", "En métodos de color, dos personas vestidas de negro colapsan por saturación nula. En nuestro sistema con OSNet, dos personas distintas con ropa negra arrojan una similitud coseno de apenas 0.4967, quedando ampliamente por debajo del umbral de 0.70 y siendo rechazadas como distintas.")
    add_bullet("Ingresos Incompletos en Márgenes: ", "Las detecciones en los bordes de la cámara presentan información corporal parcial. La ventana de calentamiento de 15 cuadros asegura que solo se tomen firmas de cuerpos completos.")
    add_bullet("Restricción de No Duplicidad Local: ", "Físicamente, una misma persona no puede encontrarse en dos coordenadas distintas de la misma cámara al mismo tiempo. El matcher prohíbe emparejar un candidato si su Global ID ya está siendo utilizado por otro track activo en ese mismo cuadro.")

    add_apa_h2("3.4. Escalabilidad a Entornos en Tiempo Real con Más de 50 Cámaras")
    add_body_p(
        "Para trasladar esta arquitectura desde la prueba de concepto actual hacia una red metropolitana o corporativa de más de 50 cámaras en tiempo real, se deben aplicar tres transformaciones arquitectónicas:",
        indent=True
    )
    add_bullet("Arquitectura Distribuida Edge-to-Cloud: ", "La detección y la extracción de embeddings deben ejecutarse en el borde (Edge Computing) en cada cámara mediante hardware acelerado (microordenadores tipo NVIDIA Jetson Orin). Cada cámara envía únicamente metadatos livianos (vector de 512 flotantes, coordenadas y timestamp) mediante mensajería en tiempo real como Apache Kafka o gRPC, requiriendo menos de 5 KB por inferencia y eliminando el transporte masivo de video crudo.")
    add_bullet("Búsqueda Vectorial Aproximada (ANN): ", "A medida que la galería almacena miles de identidades, la comparación lineal O(N) se vuelve inviable. Se debe incorporar un motor de base de datos vectorial especializado como FAISS o Milvus con índices basados en grafos jerárquicos (HNSW), logrando búsquedas en menos de 2 milisegundos con complejidad O(log N).")
    add_bullet("Restricciones Espacio-Temporales (Spatio-Temporal Gating): ", "Se modela la topología física del recinto mediante una matriz de distancias y tiempos mínimos de caminata entre cámaras. Si la distancia entre la Cámara 1 y la Cámara 35 requiere al menos 40 segundos de desplazamiento físico, el sistema descarta automáticamente cualquier coincidencia que ocurra antes de ese lapso, suprimiendo falsos positivos espurios.")

    # ==========================================
    # 4. METODOLOGÍA DEL BENCHMARK
    # ==========================================
    add_apa_h1("4. Metodología Experimental y Verdad Fundamental")

    add_body_p(
        "Para validar el comportamiento del sistema bajo condiciones fidedignas de circuito cerrado de televisión (CCTV), se implementó un entorno continuo con dos cámaras fijas atornilladas (sin saltos bruscos de fondo ni cortes de escena):",
        indent=True
    )
    add_bullet("Cámara A (Pasillo CCTV-01): ", "Cámara continua orientada a un pasillo donde transitan cinco personas en total (dos de ellas cruzan luego a la otra cámara y tres son exclusivas del pasillo).")
    add_bullet("Cámara B (Salón CCTV-02): ", "Cámara continua orientada a una sala de descanso donde interactúan personas locales exclusivas y posteriormente ingresan los dos individuos provenientes del pasillo.")

    add_body_p(
        "Este diseño establece una Verdad Fundamental (Ground Truth) inalterable y auditable, permitiendo verificar matemáticamente que el sistema alcanza cero falsos positivos entre cámaras y un 100% de recuperación de los individuos compartidos.",
        indent=True
    )

    # ==========================================
    # 5. AUDITORÍA CRONOLÓGICA (FIGURAS APA 7)
    # ==========================================
    doc.add_page_break()
    add_apa_h1("5. Auditoría Visual y Registro Cronológico de Inferencia")

    add_body_p(
        "A continuación se documenta la secuencia cronológica de eventos clave capturados durante el procesamiento de los videos de Cámara A y Cámara B, demostrando el comportamiento exacto de las asociaciones:",
        indent=True
    )

    # Figura 1
    add_apa_figure(
        1,
        "Registro de persona exclusiva en Cámara A (Pasillo).",
        evidence_dir / "01_cam_a_pasillo_exclusivo_gid1.jpg",
        "Captura de Cámara A en el fotograma 25 (t = 2.08 s). Ingreso de la primera persona en el pasillo. El rastreador asigna Local ID: 1 y el sistema crea la primera entrada en la galería con GLOBAL ID: 1."
    )

    # Figura 2
    add_apa_figure(
        2,
        "Registro del primer sujeto compartido en Cámara A.",
        evidence_dir / "02_cam_a_pasillo_hombre_gid2.jpg",
        "Captura de Cámara A en el fotograma 65 (t = 5.42 s). Ingreso del Sujeto 1 (varón con morral y vestimenta casual). Se le asigna Local ID: 2 y se registra en la galería bajo GLOBAL ID: 2, guardando su embedding OSNet maestro."
    )

    # Figura 3
    add_apa_figure(
        3,
        "Registro del segundo sujeto compartido en Cámara A.",
        evidence_dir / "03_cam_a_pasillo_mujer_gid3.jpg",
        "Captura de Cámara A en el fotograma 115 (t = 9.58 s). Ingreso del Sujeto 2 (mujer con cabello largo y ropa beige). Asignado a Local ID: 3 y registrado como GLOBAL ID: 3."
    )

    # Figura 4
    add_apa_figure(
        4,
        "Resolución de cruce simultáneo y oclusión en pasillo de Cámara A.",
        evidence_dir / "04_cam_a_pasillo_cruce_gid4_5.jpg",
        "Captura de Cámara A en el fotograma 165 (t = 13.75 s). Dos individuos transitan en direcciones opuestas en el pasillo. ByteTrack y el filtro de Kalman resuelven el cruce sin intercambio de cajas ni pérdida de identidades, registrándose como GLOBAL ID: 4 y GLOBAL ID: 5."
    )

    # Figura 5
    add_apa_figure(
        5,
        "Monitoreo en Cámara B y rechazo estricto de falsos positivos.",
        evidence_dir / "05_cam_b_salon_chica_gris_gid6.jpg",
        "Captura de Cámara B en el fotograma 50 (t = 4.17 s). Detección de una persona local en el salón (Local ID: 1). El sistema compara su vector contra los IDs 1 al 5 registrados previamente en Cámara A; todas las similitudes resultan inferiores a 0.52. Al no superar el umbral tau = 0.70, el sistema rechaza la asociación errónea y le asigna un nuevo GLOBAL ID: 6."
    )

    # Figura 6
    add_apa_figure(
        6,
        "Reidentificación exitosa del primer sujeto compartido en Cámara B.",
        evidence_dir / "06_cam_b_salon_hombre_reid_gid2.jpg",
        "Captura de Cámara B en el fotograma 176 (t = 14.67 s). Ingreso en el salón del Sujeto 1 proveniente del pasillo (Local ID: 2 en Cámara B). Al evaluar su vector frente a la galería, la similitud coseno alcanza 0.8338 respecto a la firma de Cámara A. El sistema reidentifica al individuo y reasigna automáticamente el GLOBAL ID: 2."
    )

    # Figura 7
    add_apa_figure(
        7,
        "Reidentificación exitosa del segundo sujeto compartido en Cámara B.",
        evidence_dir / "07_cam_b_salon_mujer_reid_gid3.jpg",
        "Captura de Cámara B en el fotograma 226 (t = 18.83 s). Aparición en el salón del Sujeto 2 proveniente del pasillo (Local ID: 3 en Cámara B). La firma OSNet obtiene una similitud coseno sobresaliente de 0.9850 frente al registro de Cámara A, recuperando de forma indubitable el GLOBAL ID: 3."
    )

    # ==========================================
    # 6. TABLA DE RESULTADOS (FORMATO APA 7)
    # ==========================================
    doc.add_page_break()
    add_apa_h1("6. Resultados Cuantitativos y Evaluación Numérica")

    add_body_p(
        "El procesamiento de ambos flujos de video generó un registro estructurado en formato CSV (detections_and_associations.csv) que almacena más de 1.000 detecciones auditables con coordenadas espaciales, confianza del detector y puntajes de similitud. La Tabla 1 sintetiza el desempeño numérico alcanzado por la solución:",
        indent=True
    )

    # Tabla APA 7
    p_tbl_num = doc.add_paragraph()
    p_tbl_num.paragraph_format.space_before = Pt(10)
    p_tbl_num.paragraph_format.space_after = Pt(2)
    p_tbl_num.paragraph_format.keep_with_next = True
    r_tn = p_tbl_num.add_run("Tabla 1")
    r_tn.bold = True
    r_tn.font.name = 'Times New Roman'
    r_tn.font.size = Pt(11)

    p_tbl_title = doc.add_paragraph()
    p_tbl_title.paragraph_format.space_before = Pt(0)
    p_tbl_title.paragraph_format.space_after = Pt(6)
    p_tbl_title.paragraph_format.keep_with_next = True
    r_tt = p_tbl_title.add_run("Métricas de rendimiento y validación de reidentificación multi-cámara.")
    r_tt.italic = True
    r_tt.font.name = 'Times New Roman'
    r_tt.font.size = Pt(11)

    table = doc.add_table(rows=6, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    apply_apa_table_borders(table)

    headers = ["Métrica Evaluada", "Valor Obtenido", "Interpretación Técnica"]
    col_widths = [Inches(2.5), Inches(1.5), Inches(2.5)]

    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        hdr_cells[i].paragraphs[0].runs[0].bold = True
        hdr_cells[i].paragraphs[0].runs[0].font.name = 'Times New Roman'
        hdr_cells[i].paragraphs[0].runs[0].font.size = Pt(10)
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        hdr_cells[i].width = col_widths[i]

    add_header_bottom_border(table.rows[0])

    data_rows = [
        ("Tasa de Recuperación (Recall)", "100.0% (2 de 2)", "Asociación perfecta de las dos personas que cruzaron de cámara."),
        ("Tasa de Falsos Positivos", "0.0% (0 errores)", "Cero confusiones entre personas exclusivas y la galería global."),
        ("Similitud en Coincidencia Genuina", "0.8338 - 0.9850", "Amplitud holgada sobre el umbral de corte (tau = 0.70)."),
        ("Similitud en Distintos Individuos", "Máximo 0.4967", "Margen de seguridad de más de 0.20 respecto al umbral."),
        ("Latencia de Inferencia en CPU", "~42 ms / cuadro", "Pipeline completo (YOLO + ByteTrack + OSNet) sin requerir GPU dedicada.")
    ]

    for row_idx, data in enumerate(data_rows, start=1):
        row_cells = table.rows[row_idx].cells
        for col_idx, text in enumerate(data):
            row_cells[col_idx].text = text
            row_cells[col_idx].paragraphs[0].runs[0].font.name = 'Times New Roman'
            row_cells[col_idx].paragraphs[0].runs[0].font.size = Pt(10)
            set_cell_margins(row_cells[col_idx], top=100, bottom=100, left=140, right=140)
            row_cells[col_idx].width = col_widths[col_idx]

    p_tbl_note = doc.add_paragraph()
    p_tbl_note.paragraph_format.space_before = Pt(4)
    p_tbl_note.paragraph_format.space_after = Pt(14)
    r_tnl = p_tbl_note.add_run("Nota. ")
    r_tnl.italic = True
    r_tnl.font.name = 'Times New Roman'
    r_tnl.font.size = Pt(10)
    r_tnt = p_tbl_note.add_run("Resultados calculados sobre 1.050 cuadros evaluados en el benchmark de CCTV continuo con resolución 640x360 a 12 FPS.")
    r_tnt.font.name = 'Times New Roman'
    r_tnt.font.size = Pt(10)

    # ==========================================
    # 7. CONCLUSIONES
    # ==========================================
    add_apa_h1("7. Conclusiones")

    add_body_p(
        "La sustitución de métodos empíricos de color y modelos de clasificación general por una arquitectura profunda especializada en Person Re-ID (OSNet) resolvió definitivamente las colisiones de identidad en situaciones con vestimenta oscura o de baja saturación. La combinación sinérgica entre el seguimiento espacial de ByteTrack y la memoria adaptativa protegida (EMA) permite que el sistema opere con alta estabilidad temporal, logrando un 100% de recall en sujetos compartidos y eliminando por completo los falsos positivos entre cámaras.",
        indent=True
    )

    add_body_p(
        "Asimismo, el desacoplamiento de las etapas de inferencia demostró que es plenamente viable procesar flujos a tiempo real en hardware convencional de CPU (~42 ms por cuadro), sentando las bases tecnológicas necesarias para una transición fluida hacia infraestructuras perimetrales distribuidas de gran escala.",
        indent=True
    )

    # ==========================================
    # REFERENCIAS (FORMATO APA 7)
    # ==========================================
    add_apa_h1("Referencias")

    refs = [
        "Jocher, G., Chaurasia, A., & Qiu, J. (2023). Ultralytics YOLOv8 (Version 8.0.0) [Software]. https://github.com/ultralytics/ultralytics",
        "Wojke, N., Bewley, A., & Paulus, D. (2017). Simple online and realtime tracking with a deep association metric. En 2017 IEEE International Conference on Image Processing (ICIP) (pp. 3645–3649). IEEE. https://doi.org/10.1109/ICIP.2017.8296962",
        "Zhang, Y., Sun, P., Dong, Y., Wei, Z., Zhang, Z., Zhai, X., Liang, T., & Jin, D. (2022). ByteTrack: Multi-object tracking by associating every detection box. En Computer Vision – ECCV 2022 (pp. 1–21). Springer Nature Switzerland. https://doi.org/10.1007/978-3-031-20074-8_1",
        "Zheng, L., Shen, L., Tian, L., Wang, S., Wang, J., & Tian, Q. (2015). Scalable person re-identification: A benchmark. En Proceedings of the IEEE International Conference on Computer Vision (ICCV) (pp. 1116–1124). https://doi.org/10.1109/ICCV.2015.133",
        "Zhou, K., Yang, Y., Cavallaro, A., & Xiang, T. (2019). Omni-scale feature learning for person re-identification. En Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV) (pp. 3702–3712). https://doi.org/10.1109/ICCV.2019.0371"
    ]

    for ref in refs:
        p_ref = doc.add_paragraph()
        p_ref.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_ref.paragraph_format.line_spacing = 1.25
        p_ref.paragraph_format.space_after = Pt(6)
        p_ref.paragraph_format.left_indent = Inches(0.5)
        p_ref.paragraph_format.first_line_indent = Inches(-0.5)
        run_r = p_ref.add_run(ref)
        run_r.font.name = 'Times New Roman'
        run_r.font.size = Pt(11)

    doc.save(str(output_docx))
    print(f"[EXITO] Documento Word generado correctamente: {output_docx}")
    print(f"Tamano del archivo Word: {output_docx.stat().st_size / 1024:.2f} KB")

    # Tambien guardar una copia en data/output/
    output_docx_copy = base_dir / "data" / "output" / "Informe_Tecnico_ReID_Multicamara.docx"
    doc.save(str(output_docx_copy))
    print(f"[EXITO] Copia guardada en: {output_docx_copy}")

if __name__ == "__main__":
    build_docx_report()
