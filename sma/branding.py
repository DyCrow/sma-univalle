# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Marca de autoría y propiedad intelectual: constantes y fragmentos CSS/HTML compartidos.

Se define en un único lugar para que la interfaz web, el informe HTML/Markdown, el expediente técnico y la
impresión a PDF muestren exactamente la misma firma.
"""
from __future__ import annotations

AUTORES = "ANDRES SANCHEZ Y SAMUEL MORA"
UNIVERSIDAD = "Universidad del Valle"
ASIGNATURA = "Proyecto Integrador Multidisciplinar"
PROYECTO = "PROYECTO INTEGRADOR - UNIVALLE"

LEYENDA_MARCA = f"{PROYECTO} | AUTORES: {AUTORES}"
LEYENDA_PIE = f"DOCUMENTO CONFIDENCIAL - PROYECTO INTEGRADOR UNIVALLE - {AUTORES}"
FIRMA_TXT = f"Desarrollado por: {AUTORES} — {UNIVERSIDAD} · Asignatura: {ASIGNATURA}"
FIRMA_MD = [f"**Desarrollado por:** {AUTORES} — {UNIVERSIDAD}", f"**Asignatura:** {ASIGNATURA}"]

# --- CSS: overlay flotante semitransparente (-30°), sin bloquear clics, + pie de página al imprimir ------------
WATERMARK_CSS = """
.wm{position:fixed;inset:0;overflow:hidden;pointer-events:none;z-index:2147483000;user-select:none;-webkit-user-select:none}
.wm-in{position:absolute;inset:-60%;display:flex;flex-wrap:wrap;align-content:center;justify-content:center;gap:120px 70px;transform:rotate(-30deg);opacity:.09;color:#6b7280}
.wm-in span{font:700 17px/1 system-ui,Segoe UI,Roboto,sans-serif;letter-spacing:.06em;white-space:nowrap}
@media (prefers-color-scheme:dark){.wm-in{color:#cbd5e1;opacity:.08}}
.print-footer{display:none}
.firma{font-size:12.5px;color:var(--muted);border-left:3px solid var(--accent);padding:2px 10px;margin:6px 0 10px}
@page{margin:14mm 12mm 20mm}
@media print{
 .print-footer{display:block;position:fixed;left:0;right:0;bottom:0;text-align:center;font:600 10px/1.3 system-ui,Segoe UI,Roboto,sans-serif;letter-spacing:.04em;color:#222;background:#fff;border-top:1px solid #888;padding:4px 8px;z-index:2147483001}
 body{padding-bottom:26px;background:#fff!important;color:#000!important}
 .wm-in{opacity:.07;color:#555}
 header.top,.drop,.chips,.tabs,.btn,#status{display:none!important}
 .pane:not(.on){display:none!important}
 .card,.kpi,.chartbox,.challenge,.alt,tr{break-inside:avoid;page-break-inside:avoid}
}
"""


def watermark_html() -> str:
    """Overlay con la leyenda repetida; pointer-events:none (definido en CSS) para no obstaculizar clics."""
    spans = "".join(f"<span>{LEYENDA_MARCA}</span>" for _ in range(90))
    return f'<div class="wm" aria-hidden="true"><div class="wm-in">{spans}</div></div>'


def print_footer_html() -> str:
    return f'<div class="print-footer">{LEYENDA_PIE}</div>'
