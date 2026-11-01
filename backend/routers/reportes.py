"""
backend/routers/reportes.py
----------------------------
Router FastAPI para exportación institucional de reportes (HU-12).
Permite descargar en formatos XLSX y PDF datos de:
- KPIs y perspectivas del Cuadro de Mando Integral (CMI).
- Feed de Alertas Tempranas Institucionales.
- Cierre de Gestión y Rendimiento.

Aplica segregación estricta de alcance por rol (RBAC / PoLP) y registra
cada exportación en la bitácora de auditoría log_pipeline_ingesta (etapa='EXPORT').
"""

import io
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.log_pipeline import LogPipelineIngesta
from services.kpi_service import KPIService
from services.alert_engine import AlertEngine

router = APIRouter(prefix="/api/v1/reportes", tags=["Reportes y Exportación Institucional"])

ROLES_PERMITIDOS = [
    "ADMIN",
    "DIRECTOR_ACADEMICO",
    "ANALISTA_FINANCIERO",
    "AUDITOR_CALIDAD",
    "ANALISTA_MARKETING",
]


def _crear_excel_en_memoria(
    tipo: str,
    titulo: str,
    metadatos: Dict[str, Any],
    cabeceras: List[str],
    filas: List[List[Any]]
) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = tipo[:30].upper()

    # Estilos institucionales
    header_font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0C1E33", end_color="0C1E33", fill_type="solid")
    
    col_hdr_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    col_hdr_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")

    meta_font_bold = Font(name="Calibri", size=10, bold=True, color="374151")
    meta_font_val = Font(name="Calibri", size=10, color="1F2937")

    border_thin = Border(
        left=Side(style='thin', color='E5E7EB'),
        right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),
        bottom=Side(style='thin', color='E5E7EB')
    )

    # Fila 1: Título institucional
    ws.merge_cells("A1:G1")
    cell_title = ws["A1"]
    cell_title.value = f"GIRAGROUP BI SYSTEM — {titulo.upper()}"
    cell_title.font = header_font
    cell_title.fill = header_fill
    cell_title.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # Fila 2 a 4: Metadatos de auditoría y parámetros
    ws["A2"] = "Generado por:"
    ws["A2"].font = meta_font_bold
    ws["B2"] = f"{metadatos.get('usuario')} ({metadatos.get('rol')})"
    ws["B2"].font = meta_font_val

    ws["D2"] = "Fecha de Emisión:"
    ws["D2"].font = meta_font_bold
    ws["E2"] = metadatos.get("fecha")
    ws["E2"].font = meta_font_val

    ws["A3"] = "Gestión / Período:"
    ws["A3"].font = meta_font_bold
    ws["B3"] = metadatos.get("gestion") or "Todas las Gestiones"
    ws["B3"].font = meta_font_val

    ws["D3"] = "Filtro Programa:"
    ws["D3"].font = meta_font_bold
    ws["E3"] = metadatos.get("programa") or "Todos los Programas"
    ws["E3"].font = meta_font_val

    # Fila 5: Cabeceras de la tabla
    row_idx = 5
    for col_idx, cabecera in enumerate(cabeceras, start=1):
        c = ws.cell(row=row_idx, column=col_idx, value=cabecera)
        c.font = col_hdr_font
        c.fill = col_hdr_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[row_idx].height = 24

    # Filas de datos
    for fila in filas:
        row_idx += 1
        for col_idx, valor in enumerate(fila, start=1):
            c = ws.cell(row=row_idx, column=col_idx, value=valor)
            c.border = border_thin
            if isinstance(valor, (int, float)):
                c.alignment = Alignment(horizontal="right", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")

    # Auto-ajuste de anchos de columna
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len and cell.row > 1:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _crear_pdf_en_memoria(
    tipo: str,
    titulo: str,
    metadatos: Dict[str, Any],
    cabeceras: List[str],
    filas: List[List[Any]]
) -> bytes:
    buf = io.BytesIO()
    # Si hay muchas columnas usar landscape
    pagesize = landscape(letter) if len(cabeceras) > 5 else letter
    doc = SimpleDocTemplate(
        buf,
        pagesize=pagesize,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0C1E33')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#4B5563')
    )
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#1E293B')
    )
    meta_val_style = ParagraphStyle(
        'DocMetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#334155')
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10
    )
    header_cell_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    elements = []

    # Título institucional
    elements.append(Paragraph(f"GIRAGROUP BI SYSTEM — {titulo.upper()}", title_style))
    elements.append(Paragraph("Reporte Institucional Oficial de Inteligencia de Negocios y Analítica", subtitle_style))
    elements.append(Spacer(1, 10))

    # Tabla de Metadatos
    meta_data = [
        [
            Paragraph("Usuario:", meta_style), Paragraph(f"{metadatos.get('usuario')} ({metadatos.get('rol')})", meta_val_style),
            Paragraph("Fecha:", meta_style), Paragraph(metadatos.get("fecha", ""), meta_val_style)
        ],
        [
            Paragraph("Gestión:", meta_style), Paragraph(metadatos.get("gestion") or "Todas", meta_val_style),
            Paragraph("Programa:", meta_style), Paragraph(metadatos.get("programa") or "Todos", meta_val_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[60, 200, 60, 200])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 14))

    # Preparar tabla de datos
    table_content = []
    # Fila de cabeceras
    table_content.append([Paragraph(h, header_cell_style) for h in cabeceras])

    # Filas de contenido (limitar a 200 en PDF si es muy extenso para evitar desbordes)
    for fila in filas[:250]:
        fila_parrafos = []
        for val in fila:
            texto = str(val if val is not None else "")
            fila_parrafos.append(Paragraph(texto, cell_style))
        table_content.append(fila_parrafos)

    data_table = Table(table_content, repeatRows=1)
    data_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0C1E33')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))
    elements.append(data_table)

    doc.build(elements)
    return buf.getvalue()


@router.get(
    "/export",
    summary="Exportar reportes de KPIs, Alertas y Cierre en formato XLSX o PDF con RBAC y Auditoría"
)
def exportar_reporte(
    tipo: str = Query(..., description="Tipo de reporte: kpis, alertas, cierre"),
    formato: str = Query("xlsx", description="Formato de salida: xlsx o pdf"),
    gestion: Optional[str] = Query(None, description="Filtro opcional de gestión"),
    programa: Optional[str] = Query(None, description="Filtro opcional de programa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tiempo_inicio = time.time()
    tipo_clean = (tipo or "").strip().lower()
    formato_clean = (formato or "").strip().lower()
    # Gestión numérica para filtrar el DW (mismo criterio que KPIService: solo dígitos)
    gestion_int = int(gestion.strip()) if gestion and gestion.strip().isdigit() else None

    if tipo_clean not in ("kpis", "alertas", "cierre"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de reporte inválido. Opciones válidas: 'kpis', 'alertas', 'cierre'."
        )

    if formato_clean not in ("xlsx", "pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de exportación no soportado. Opciones válidas: 'xlsx', 'pdf'."
        )

    if current_user.role not in ROLES_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos suficientes para exportar reportes institucionales."
        )

    cabeceras: List[str] = []
    filas: List[List[Any]] = []
    titulo_reporte = ""

    # ── 1. EXPORTACIÓN DE ALERTAS TEMPRANAS ────────────────────────────────────
    if tipo_clean == "alertas":
        titulo_reporte = "Feed Institucional de Alertas Tempranas"
        engine = AlertEngine(db)
        todas = engine.evaluar_todas(persistir_notificaciones=False)

        # Segregación RBAC estricta (PoLP)
        if current_user.role == "DIRECTOR_ACADEMICO":
            alertas_filtradas = [a for a in todas if a.get("tipo") in ("ACADEMICO", "DESERCION")]
        elif current_user.role == "ANALISTA_FINANCIERO":
            alertas_filtradas = [a for a in todas if a.get("tipo") == "FINANCIERO"]
        elif current_user.role == "ANALISTA_MARKETING":
            alertas_filtradas = [a for a in todas if a.get("tipo") in ("MARKETING", "DEMANDA", "CONVERSION")]
        else:
            # ADMIN y AUDITOR_CALIDAD ven todas las alertas
            alertas_filtradas = todas

        # Filtro opcional por programa
        if programa and programa.strip().upper() not in ("", "TODOS", "ALL"):
            prog_low = programa.strip().lower()
            alertas_filtradas = [
                a for a in alertas_filtradas
                if prog_low in str(a.get("modulo", "")).lower()
                or prog_low in str(a.get("mensaje", "")).lower()
            ]

        cabeceras = [
            "Regla",
            "Tipo",
            "Severidad",
            "Estudiante",
            "Código",
            "Módulo / Contexto",
            "Métrica Valor",
            "Umbral Disparador",
            "Mensaje Institucional"
        ]
        for a in alertas_filtradas:
            metrica_val = str(a.get("metrica_valor", ""))
            umbral_val = str(a.get("umbral_disparador", ""))
            mensaje_val = str(a.get("mensaje", ""))

            # Segregación estricta de montos financieros por rol (# PoLP):
            # Solo ADMIN y ANALISTA_FINANCIERO ven montos financieros.
            if current_user.role not in ("ADMIN", "ANALISTA_FINANCIERO"):
                if a.get("tipo") in ("FINANCIERO", "RIESGO_CRUZADO") or "Bs" in metrica_val or "Bs" in mensaje_val or "Bs" in umbral_val:
                    if a.get("tipo") in ("FINANCIERO", "RIESGO_CRUZADO") or "Bs" in metrica_val:
                        metrica_val = "[RESTRINGIDO PoLP]"
                    if "Bs" in umbral_val or a.get("tipo") == "FINANCIERO":
                        umbral_val = "[RESTRINGIDO PoLP]"
                    mensaje_val = re.sub(r'Bs\.?\s*[\d,]+(\.\d+)?', '[RESTRINGIDO PoLP]', mensaje_val)
                    mensaje_val = re.sub(r'deuda de\s+[\d,]+(\.\d+)?', 'deuda de [RESTRINGIDO PoLP]', mensaje_val)

            filas.append([
                a.get("regla", ""),
                a.get("tipo", ""),
                a.get("severidad", ""),
                a.get("estudiante", ""),
                a.get("codigo_estudiante", "") or "S/C",
                a.get("modulo", "") or "N/D",
                metrica_val,
                umbral_val,
                mensaje_val
            ])

    # ── 2. EXPORTACIÓN DE KPIS Y CMI ──────────────────────────────────────────
    elif tipo_clean == "kpis":
        titulo_reporte = "Cuadro de Mando Integral y KPIs Consolidados"
        kpi_srv = KPIService(db)
        cmi_data = kpi_srv.obtener_perspectivas_cmi_completo(gestion=gestion, programa=programa).get("perspectivas", {})
        ticket_programas = kpi_srv.calcular_ticket_promedio_por_programa(programa_filtro=programa, gestion_filtro=gestion_int)

        # Construir tabla según rol
        cabeceras = ["Perspectiva CMI", "Indicador Clave (KPI)", "Valor Calculado", "Meta / Referencia", "Estado"]

        # Perspectiva Financiera: solo ADMIN y ANALISTA_FINANCIERO ven montos reales.
        # Todo otro rol ve [RESTRINGIDO PoLP] (# PoLP).
        fin = cmi_data.get("financiera", {})
        if current_user.role in ("ADMIN", "ANALISTA_FINANCIERO"):
            rec_pct_val = fin.get('recaudacion_vs_meta_pct')
            rec_bs_val = fin.get('monto_total_recaudado_bs')
            meta_bs_val = fin.get('monto_meta_gestion_bs')
            mora_pct_val = fin.get('mora_total_pct')
            tk_bs_val = fin.get('ticket_promedio_bs')

            rec_pct_str = f"{rec_pct_val}%" if rec_pct_val is not None else "N/D"
            rec_bs_str = f"Bs. {rec_bs_val:,.2f}" if rec_bs_val is not None else "Bs. 0.00"
            meta_bs_str = f"Bs. {meta_bs_val:,.2f}" if meta_bs_val is not None else "Bs. 0.00"
            mora_pct_str = f"{mora_pct_val}%" if mora_pct_val is not None else "0.0%"
            tk_bs_str = f"Bs. {tk_bs_val:,.2f}" if tk_bs_val is not None else "Bs. 0.00"

            filas.append(["Financiera", "Cumplimiento Recaudación vs Meta", rec_pct_str, "100.0%", "Óptimo" if (rec_pct_val or 0) >= 90 else "En Riesgo"])
            filas.append(["Financiera", "Monto Total Recaudado (Bs)", rec_bs_str, meta_bs_str, "Ejecutado"])
            filas.append(["Financiera", "Mora Total de Cartera (%)", mora_pct_str, "< 15.0%", "Controlado" if (mora_pct_val or 0) < 15 else "Alerta"])
            filas.append(["Financiera", "KPI Ticket Promedio Global (Bs)", tk_bs_str, "Bs. 850.00", "Rentable"])

            # Desglose Ticket Promedio por programa
            for prog in ticket_programas:
                filas.append([
                    "Financiera (Ticket Prog.)",
                    f"Ticket Promedio: {prog['programa']}",
                    f"Bs. {prog['ticket_promedio_bs']:,.2f}" if prog.get('ticket_promedio_bs') is not None else "Bs. 0.00",
                    f"Rec: Bs. {prog['recaudacion_bs']:,.2f} | Mat: {prog['matricula']}" if prog.get('recaudacion_bs') is not None else "N/D",
                    "Normal" if prog.get('matricula', 0) > 0 else "Sin Matrícula"
                ])
        else:
            filas.append(["Financiera", "Cumplimiento Recaudación vs Meta", "[RESTRINGIDO PoLP]", "100.0%", "[RESTRINGIDO PoLP]"])
            filas.append(["Financiera", "Monto Total Recaudado (Bs)", "[RESTRINGIDO PoLP]", "[RESTRINGIDO PoLP]", "[RESTRINGIDO PoLP]"])
            filas.append(["Financiera", "Mora Total de Cartera (%)", "[RESTRINGIDO PoLP]", "< 15.0%", "[RESTRINGIDO PoLP]"])
            filas.append(["Financiera", "KPI Ticket Promedio Global (Bs)", "[RESTRINGIDO PoLP]", "[RESTRINGIDO PoLP]", "[RESTRINGIDO PoLP]"])

            for prog in ticket_programas:
                filas.append([
                    "Financiera (Ticket Prog.)",
                    f"Ticket Promedio: {prog['programa']}",
                    "[RESTRINGIDO PoLP]",
                    f"Rec: [RESTRINGIDO PoLP] | Mat: {prog['matricula']}",
                    "[RESTRINGIDO PoLP]"
                ])

        # Perspectiva Aprendizaje / Académica (Solo ADMIN y DIRECTOR_ACADEMICO)
        if current_user.role in ("ADMIN", "DIRECTOR_ACADEMICO"):
            apr = cmi_data.get("aprendizaje_crecimiento", {})
            prom_n = apr.get('promedio_general_notas')
            t_apr = apr.get('tasa_aprobacion_pct')
            filas.append(["Aprendizaje y Crecimiento", "Promedio General de Notas", f"{prom_n} pts" if prom_n is not None else "N/D", ">= 75.0 pts", "Satisfactorio"])
            filas.append(["Aprendizaje y Crecimiento", "Tasa de Aprobación Global", f"{t_apr}%" if t_apr is not None else "N/D", ">= 90.0%", "Óptimo"])
            filas.append(["Aprendizaje y Crecimiento", "Estudiantes en Riesgo Académico", str(apr.get("estudiantes_en_riesgo") or 0), "0", "En Seguimiento"])

        # Perspectiva Procesos Internos / Calidad (Solo ADMIN y AUDITOR_CALIDAD)
        if current_user.role in ("ADMIN", "AUDITOR_CALIDAD"):
            proc = cmi_data.get("procesos_internos", {})
            c_med = proc.get('confianza_media_beto_pct')
            t_aut = proc.get('tasa_automatizacion_pct')
            filas.append(["Procesos Internos (DataOps)", "Confianza Media Modelo BETO NER", f"{c_med}%" if c_med is not None else "N/D", ">= 95.0%", "Operativo"])
            filas.append(["Procesos Internos (DataOps)", "Tasa Automatización Limpieza", f"{t_aut}%" if t_aut is not None else "N/D", ">= 90.0%", "Óptimo"])
            filas.append(["Procesos Internos (DataOps)", "Documentos Procesados DW", str(proc.get("documentos_procesados") or 0), "N/A", "Registrado"])
            filas.append(["Procesos Internos (DataOps)", "Registros Derivados a HITL", str(proc.get("registros_derivados_hitl") or 0), "< 15", "Controlado"])

        # Perspectiva Cliente / Mercado (Solo ADMIN y ANALISTA_MARKETING)
        if current_user.role in ("ADMIN", "ANALISTA_MARKETING"):
            cli = cmi_data.get("cliente_mercado", {})
            t_adm = cli.get('tasa_conversion_admisiones_pct')
            filas.append(["Cliente y Mercado", "Tasa Conversión Admisiones", f"{t_adm}%" if t_adm is not None else "N/D", ">= 30.0%", "Cumplido"])
            filas.append(["Cliente y Mercado", "Total Matrícula Acumulada", str(cli.get("total_matricula_acumulada") or 0), "N/A", "Activa"])

    # ── 3. EXPORTACIÓN DE CIERRE DE GESTIÓN ────────────────────────────────────
    elif tipo_clean == "cierre":
        titulo_reporte = "Cierre Institucional de Gestión y Rendimiento"
        kpi_srv = KPIService(db)
        ticket_programas = kpi_srv.calcular_ticket_promedio_por_programa(programa_filtro=programa, gestion_filtro=gestion_int)

        cabeceras = ["Programa Académico", "Gestión", "Matrícula Registrada", "Recaudación Total (Bs)", "Ticket Promedio (Bs)", "Estado de Cierre"]
        gestion_label = gestion or "2026-I"

        if not ticket_programas:
            rec_str = "[RESTRINGIDO PoLP]" if current_user.role not in ("ADMIN", "ANALISTA_FINANCIERO") else "Bs. 0.00"
            ticket_str = "[RESTRINGIDO PoLP]" if current_user.role not in ("ADMIN", "ANALISTA_FINANCIERO") else "Bs. 0.00"
            filas.append([
                "Consolidado General",
                gestion_label,
                0,
                rec_str,
                ticket_str,
                "Sin Movimientos"
            ])
        else:
            for prog in ticket_programas:
                # Solo ADMIN y ANALISTA_FINANCIERO ven montos financieros. Todo otro rol ve [RESTRINGIDO PoLP] (# PoLP).
                if current_user.role not in ("ADMIN", "ANALISTA_FINANCIERO"):
                    rec_str = "[RESTRINGIDO PoLP]"
                    ticket_str = "[RESTRINGIDO PoLP]"
                else:
                    rec_str = f"Bs. {prog['recaudacion_bs']:,.2f}" if prog.get('recaudacion_bs') is not None else "Bs. 0.00"
                    ticket_str = f"Bs. {prog['ticket_promedio_bs']:,.2f}" if prog.get('ticket_promedio_bs') is not None else "Bs. 0.00"

                filas.append([
                    prog["programa"],
                    gestion_label,
                    prog["matricula"],
                    rec_str,
                    ticket_str,
                    "Cerrado Satisfactorio" if prog["matricula"] > 0 else "Sin Matrícula"
                ])

    # ── METADATOS COMUNES DE AUDITORÍA ────────────────────────────────────────
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadatos = {
        "usuario": current_user.username,
        "rol": current_user.role,
        "fecha": now_str,
        "gestion": gestion,
        "programa": programa,
    }

    # ── GENERACIÓN DEL ARCHIVO ────────────────────────────────────────────────
    if formato_clean == "xlsx":
        file_bytes = _crear_excel_en_memoria(tipo_clean, titulo_reporte, metadatos, cabeceras, filas)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"reporte_{tipo_clean}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    else:
        file_bytes = _crear_pdf_en_memoria(tipo_clean, titulo_reporte, metadatos, cabeceras, filas)
        media_type = "application/pdf"
        filename = f"reporte_{tipo_clean}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    # ── REGISTRO DE AUDITORÍA EN log_pipeline_ingesta (etapa='EXPORT') ─────────
    tiempo_total_ms = int((time.time() - tiempo_inicio) * 1000)
    try:
        log_entry = LogPipelineIngesta(
            etapa="EXPORT",
            nivel="SUCCESS",
            modulo="REPORTES_EXPORT",
            mensaje=(
                f"Exportación de reporte tipo='{tipo_clean}' en formato '{formato_clean}' "
                f"realizada exitosamente por '{current_user.username}' (rol='{current_user.role}'). "
                f"Filas exportadas: {len(filas)}."
            ),
            tiempo_ms=tiempo_total_ms,
            metadata_json={
                "tipo": tipo_clean,
                "formato": formato_clean,
                "gestion": gestion,
                "programa": programa,
                "usuario_id": current_user.id,
                "username": current_user.username,
                "rol": current_user.role,
                "total_filas_exportadas": len(filas)
            }
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        # No bloquear la descarga en caso de fallo de log
        try:
            db.rollback()
        except Exception:
            pass

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@router.get("/historial", summary="Consultar historial de auditoría de reportes exportados")
def get_historial_exportaciones(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna el historial de exportaciones registradas en log_pipeline_ingesta (etapa='EXPORT').
    Aplica RBAC: ADMIN ve todas las exportaciones; otros roles ven solo sus propias exportaciones.
    """
    if current_user.role not in ROLES_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"El rol '{current_user.role}' no tiene autorización para consultar reportes."
        )

    query = db.query(LogPipelineIngesta).filter(LogPipelineIngesta.etapa == "EXPORT")

    if current_user.role != "ADMIN":
        logs = query.order_by(LogPipelineIngesta.id.desc()).limit(limit * 3).all()
        logs_filtrados = [
            lg for lg in logs
            if isinstance(lg.metadata_json, dict) and lg.metadata_json.get("username") == current_user.username
        ][:limit]
    else:
        logs_filtrados = query.order_by(LogPipelineIngesta.id.desc()).limit(limit).all()

    resultados = []
    for lg in logs_filtrados:
        meta = lg.metadata_json if isinstance(lg.metadata_json, dict) else {}
        fecha_str = lg.created_at.isoformat() if getattr(lg, "created_at", None) else datetime.now().isoformat()
        resultados.append({
            "id": lg.id,
            "fecha": fecha_str,
            "usuario": meta.get("username", "desconocido"),
            "rol": meta.get("rol", "N/A"),
            "tipo": meta.get("tipo", "N/A"),
            "formato": meta.get("formato", "N/A"),
            "gestion": meta.get("gestion") or "Todas",
            "programa": meta.get("programa") or "Todos",
            "filas": meta.get("total_filas_exportadas", 0),
            "tiempo_ms": lg.tiempo_ms or 0,
            "nivel": lg.nivel or "SUCCESS",
            "mensaje": lg.mensaje
        })

    return {"total": len(resultados), "historial": resultados}

