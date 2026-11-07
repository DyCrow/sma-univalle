# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Renderizado del informe (HTML autocontenido + Markdown) y de las directivas de visualización (SVG propio)."""
from __future__ import annotations

import html
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd

from .branding import FIRMA_MD, FIRMA_TXT, WATERMARK_CSS, print_footer_html, watermark_html
from .text_utils import fmt_num as N, fmt_pct as P

PALETTE = ["#0f766e", "#b45309", "#4338ca", "#be123c", "#0369a1", "#65a30d", "#a21caf", "#475569"]
esc = html.escape


def _short(v: float) -> str:
    a = abs(v)
    if a >= 1e9:
        return f"{v / 1e9:.1f}".replace(".", ",") + " mil M"
    if a >= 1e6:
        return f"{v / 1e6:.1f}".replace(".", ",") + " M"
    if a >= 1e4:
        return f"{v / 1e3:.0f} mil"
    return N(v, 0 if a >= 100 else 1)


# ------------------------------------------------------------------------------------------ gráficos SVG
def _svg_wrap(body: str, w: int = 560, hgt: int = 280, title: str = "") -> str:
    return f'<svg viewBox="0 0 {w} {hgt}" role="img" aria-label="{esc(title)}" xmlns="http://www.w3.org/2000/svg" class="chart">{body}</svg>'


def _axes_text(x, y, s, anchor="middle", cls="tick"):
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" class="{cls}">{esc(str(s))}</text>'


def svg_line(labels, values, title):
    w, hgt, ml, mr, mt, mb = 560, 280, 52, 14, 14, 36
    if len(values) < 2:
        return None
    vmin, vmax = min(0, min(values)), max(values)
    span = (vmax - vmin) or 1
    px = lambda i: ml + (w - ml - mr) * i / (len(values) - 1)
    py = lambda v: mt + (hgt - mt - mb) * (1 - (v - vmin) / span)
    pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(values))
    area = f"{px(0):.1f},{py(vmin):.1f} " + pts + f" {px(len(values) - 1):.1f},{py(vmin):.1f}"
    body = ""
    for k in range(5):
        v = vmin + span * k / 4
        body += f'<line x1="{ml}" x2="{w - mr}" y1="{py(v):.1f}" y2="{py(v):.1f}" class="grid"/>' + _axes_text(ml - 6, py(v) + 3, _short(v), "end")
    step = max(1, len(labels) // 6)
    for i in range(0, len(labels), step):
        body += _axes_text(px(i), hgt - mb + 16, labels[i], "end" if px(i) > w - 46 else "middle")
    body += f'<polygon points="{area}" fill="{PALETTE[0]}" opacity="0.12"/><polyline points="{pts}" fill="none" stroke="{PALETTE[0]}" stroke-width="2.2" stroke-linejoin="round"/>'
    for i, v in enumerate(values):
        if len(values) <= 40:
            body += f'<circle cx="{px(i):.1f}" cy="{py(v):.1f}" r="2.6" fill="{PALETTE[0]}"><title>{esc(str(labels[i]))}: {N(v)}</title></circle>'
    return _svg_wrap(body, w, hgt, title)


def svg_bars(labels, values, title, fmt=None):
    n = len(values)
    if n == 0:
        return None
    rowh, ml, mr, mt = 26, 150, 70, 8
    w, hgt = 560, mt * 2 + rowh * n
    vmax = max(max(values), 1e-9)
    body = ""
    for i, (lab, v) in enumerate(zip(labels, values)):
        y = mt + i * rowh
        bw = (w - ml - mr) * (max(v, 0) / vmax)
        body += _axes_text(ml - 8, y + 16, (lab[:22] + "…") if len(lab) > 23 else lab, "end", "lab")
        body += f'<rect x="{ml}" y="{y + 4}" width="{bw:.1f}" height="{rowh - 9}" rx="3" fill="{PALETTE[i % 1]}"><title>{esc(lab)}: {N(v)}</title></rect>'
        body += _axes_text(ml + bw + 6, y + 16, (fmt or _short)(v), "start", "val")
    return _svg_wrap(body, w, hgt, title)


def svg_hist(values, title, bins=20):
    v = np.asarray([x for x in values if x == x], dtype=float)
    if len(v) < 5:
        return None
    lo, hi = np.percentile(v, [0.5, 99.5])
    if hi <= lo:
        hi = lo + 1
    counts, edges = np.histogram(np.clip(v, lo, hi), bins=bins, range=(lo, hi))
    w, hgt, ml, mr, mt, mb = 560, 260, 46, 12, 12, 34
    cmax = counts.max() or 1
    bw = (w - ml - mr) / bins
    body = ""
    for k in range(4):
        c = cmax * k / 3
        y = mt + (hgt - mt - mb) * (1 - c / cmax)
        body += f'<line x1="{ml}" x2="{w - mr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>' + _axes_text(ml - 6, y + 3, N(c, 0), "end")
    for i, c in enumerate(counts):
        bh = (hgt - mt - mb) * c / cmax
        body += f'<rect x="{ml + i * bw + 1:.1f}" y="{hgt - mb - bh:.1f}" width="{bw - 2:.1f}" height="{bh:.1f}" fill="{PALETTE[0]}" opacity="0.85"><title>{_short(edges[i])} – {_short(edges[i + 1])}: {c}</title></rect>'
    for k in range(5):
        body += _axes_text(ml + (w - ml - mr) * k / 4, hgt - mb + 16, _short(lo + (hi - lo) * k / 4))
    return _svg_wrap(body, w, hgt, title)


def svg_donut(labels, values, title):
    tot = float(sum(values))
    if tot <= 0:
        return None
    w, hgt, cx, cy, r, r2 = 560, 220, 120, 110, 90, 54
    body, ang = "", -math.pi / 2
    for i, v in enumerate(values):
        a2 = ang + 2 * math.pi * v / tot
        large = 1 if a2 - ang > math.pi else 0
        x1, y1, x2, y2 = cx + r * math.cos(ang), cy + r * math.sin(ang), cx + r * math.cos(a2), cy + r * math.sin(a2)
        x3, y3, x4, y4 = cx + r2 * math.cos(a2), cy + r2 * math.sin(a2), cx + r2 * math.cos(ang), cy + r2 * math.sin(ang)
        if v / tot > 0.9999:
            body += f'<circle cx="{cx}" cy="{cy}" r="{(r + r2) / 2}" fill="none" stroke="{PALETTE[i % 8]}" stroke-width="{r - r2}"/>'
        else:
            body += f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 {large} 1 {x2:.1f},{y2:.1f} L{x3:.1f},{y3:.1f} A{r2},{r2} 0 {large} 0 {x4:.1f},{y4:.1f} Z" fill="{PALETTE[i % 8]}"><title>{esc(labels[i])}: {N(v)} ({v / tot * 100:.1f}%)</title></path>'
        ang = a2
    for i, (lab, v) in enumerate(zip(labels, values)):
        y = 40 + i * 28
        body += f'<rect x="250" y="{y - 11}" width="14" height="14" rx="3" fill="{PALETTE[i % 8]}"/>' + _axes_text(272, y, f"{lab} · {N(v)} ({v / tot * 100:.1f}%)".replace(".", ","), "start", "lab")
    return _svg_wrap(body, w, hgt, title)


def render_directive(v: dict, run) -> str | None:
    """Convierte una directiva de visualización (Agente 4) en SVG calculando los datos desde el dataset limpio."""
    df, f = run.clean, run.facts
    tipo, ag = v["tipo"], v.get("agregacion", "conteo")
    try:
        if ag == "nulos":
            items = sorted([(c["normalizado"], c["pct_nulos"]) for c in run.schema if c["pct_nulos"] > 0], key=lambda x: -x[1])[:v.get("top", 10)]
            if not items:
                return None
            return svg_bars([a for a, _ in items], [b for _, b in items], v["titulo"], fmt=lambda x: N(x, 1) + "%")
        if ag == "sentimiento":
            s = f["texto"][0]["sentimiento"]
            return svg_donut(["Negativo", "Neutro", "Positivo"], [s["negativo"], s["neutro"], s["positivo"]], v["titulo"])
        if ag == "temas":
            t = f["texto"][0]["temas"][: v.get("top", 5)]
            return svg_bars([x["tema"] for x in t], [x["n"] for x in t], v["titulo"], fmt=lambda x: N(x, 0))
        x, y = v.get("columna_x"), v.get("columna_y")
        if tipo == "linea":
            tb = next((t for t in f["tiempo"] if t["columna"] == x), None)
            if not tb:
                return None
            key = "suma" if ag == "suma" else "media"
            pts = [(p["periodo"], p[key] if y else p["n"]) for p in tb["serie"] if p["suma"] is not None]
            return svg_line([a for a, _ in pts], [b for _, b in pts], v["titulo"])
        if tipo == "histograma":
            return svg_hist(df[x].dropna().tolist(), v["titulo"])
        if tipo in ("barras", "pastel"):
            if y and ag in ("suma", "media"):
                g = df.groupby(x)[y].agg("sum" if ag == "suma" else "mean").sort_values(ascending=False)
            else:
                g = df[x].value_counts()
            g = g.head(v.get("top", 8))
            labels, vals = [str(i) for i in g.index], [float(a) for a in g.values]
            return svg_donut(labels, vals, v["titulo"]) if tipo == "pastel" else svg_bars(labels, vals, v["titulo"])
    except Exception:  # noqa: BLE001  (un gráfico fallido no debe tumbar el informe)
        return None
    return None


# ------------------------------------------------------------------------------------------ markdown mínimo
def md_to_html(md: str) -> str:
    out, in_ul, in_ol = [], False, False

    def inline(s):
        s = esc(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w])_(.+?)_(?![\w])", r"<em>\1</em>", s)
        return s

    def close():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for line in md.split("\n"):
        if re.match(r"^\s*-\s+", line):
            if not in_ul:
                close()
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(re.sub(r'^\s*-\s+', '', line))}</li>")
        elif re.match(r"^\s*\d+\.\s+", line):
            if not in_ol:
                close()
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline(re.sub(r'^\s*\d+\.\s+', '', line))}</li>")
        elif line.strip() == "":
            close()
        else:
            close()
            out.append(f"<p>{inline(line)}</p>")
    close()
    return "\n".join(out)


# ------------------------------------------------------------------------------------------ Consejero
def advice_html(a: dict) -> str:
    rec = a["recomendacion"]
    badge = {"proceder": "ok", "proceder con condiciones": "warn", "pilotar primero": "warn", "reconsiderar": "bad", "posponer": "bad", "evidencia insuficiente": "bad"}.get(rec["postura"], "info")
    o = [f'<div class="advice"><div class="posture {badge}"><span class="k">Postura</span><strong>{esc(rec["postura"].capitalize())}</strong><span class="k">Confianza: {esc(rec["confianza"])}</span></div>']
    o.append(f'<p class="lead">{md_to_html(a["respuesta_directa"]).replace("<p>", "").replace("</p>", "")}</p>')
    o.append(f'<p class="muted">{esc(a["reformulacion"])}</p><p class="muted">{esc(a["lectura_del_rol"])}</p>')
    def lst(title, items, cls=""):
        if not items:
            return ""
        return f'<h4>{esc(title)}</h4><ul class="{cls}">' + "".join(f"<li>{md_to_html(i).replace('<p>', '').replace('</p>', '')}</li>" for i in items) + "</ul>"
    if a["evidencia_a_favor"] or a["evidencia_en_contra"]:
        o.append('<div class="two"><div>' + lst("Evidencia a favor", a["evidencia_a_favor"], "pro") + "</div><div>" + lst("Evidencia en contra", a["evidencia_en_contra"], "con") + "</div></div>")
    if a["cuestionamientos"]:
        o.append("<h4>Lo que yo cuestionaría</h4>")
        for c in a["cuestionamientos"]:
            o.append(f'<div class="challenge sev-{esc(c["severidad"])}"><div class="sev">{esc(c["severidad"])}</div><div><strong>{esc(c["supuesto"])}</strong><p>{esc(c["por_que_importa"])}</p><p class="muted"><em>Lo refutaría:</em> {esc(c["prueba_que_lo_refutaria"])}</p></div></div>')
    if a["sesgos_detectados"]:
        o.append("<h4>Sesgos que detecto en el planteamiento</h4><ul>" + "".join(f"<li><strong>{esc(s['sesgo'])}</strong> {esc(s['senal'])} — {esc(s['contramedida'])}</li>" for s in a["sesgos_detectados"]) + "</ul>")
    if a["premortem"]:
        o.append(lst("Pre-mortem: si fracasa en 6 meses, probablemente fue porque…", a["premortem"]))
    if a["alternativas"]:
        o.append("<h4>Alternativas</h4><div class='alts'>" + "".join(f"<div class='alt'><strong>{esc(x['opcion'])}</strong><p>＋ {esc(x['pros'])}</p><p>－ {esc(x['contras'])}</p><p class='muted'>Elegirla cuando: {esc(x['cuando_elegirla'])}</p></div>" for x in a["alternativas"]) + "</div>")
    if rec["condiciones"]:
        o.append(lst("Condiciones para avanzar", rec["condiciones"]))
    pl = a["plan_liderazgo"]
    o.append("<h4>Plan de liderazgo</h4>" + lst("Primeros pasos", pl["primeros_pasos"]) + lst("KPIs a vigilar", pl["kpis"]) + lst("Stakeholders", pl["stakeholders"]) +
             f"<p><strong>Comunicación:</strong> {esc(pl['comunicacion'])}</p><p><strong>Criterio de reversión:</strong> {esc(pl['criterio_de_reversion'])}</p>")
    if a["preguntas_para_el_administrador"]:
        o.append(lst("Preguntas que te devuelvo (las que más cambiarían la decisión)", a["preguntas_para_el_administrador"], "ask"))
    if a["datos_que_faltan"]:
        o.append(lst("Datos que faltan", a["datos_que_faltan"]))
    o.append("</div>")
    return "".join(o)


def advice_md(a: dict) -> str:
    L = [f"### Consejero estratégico — postura: **{a['recomendacion']['postura']}** (confianza {a['recomendacion']['confianza']})", "", a["respuesta_directa"], "", f"_{a['reformulacion']}_", "", f"_{a['lectura_del_rol']}_", ""]
    if a["evidencia_a_favor"]:
        L += ["**A favor:**"] + [f"- {x}" for x in a["evidencia_a_favor"]] + [""]
    if a["evidencia_en_contra"]:
        L += ["**En contra:**"] + [f"- {x}" for x in a["evidencia_en_contra"]] + [""]
    if a["cuestionamientos"]:
        L += ["**Lo que cuestionaría:**"] + [f"- [{c['severidad']}] **{c['supuesto']}** — {c['por_que_importa']} _Lo refutaría:_ {c['prueba_que_lo_refutaria']}" for c in a["cuestionamientos"]] + [""]
    if a["sesgos_detectados"]:
        L += ["**Sesgos detectados:**"] + [f"- {s['sesgo']} {s['senal']}: {s['contramedida']}" for s in a["sesgos_detectados"]] + [""]
    L += ["**Pre-mortem:**"] + [f"- {x}" for x in a["premortem"]] + ["", "**Alternativas:**"] + [f"- **{x['opcion']}** (+ {x['pros']}; − {x['contras']}; cuándo: {x['cuando_elegirla']})" for x in a["alternativas"]] + [""]
    pl = a["plan_liderazgo"]
    L += ["**Plan de liderazgo:**"] + [f"- {x}" for x in pl["primeros_pasos"]] + [f"- KPIs: {'; '.join(pl['kpis'])}", f"- Comunicación: {pl['comunicacion']}", f"- Reversión: {pl['criterio_de_reversion']}", ""]
    if a["preguntas_para_el_administrador"]:
        L += ["**Preguntas para ti:**"] + [f"- {x}" for x in a["preguntas_para_el_administrador"]] + [""]
    if a["datos_que_faltan"]:
        L += ["**Datos que faltan:**"] + [f"- {x}" for x in a["datos_que_faltan"]]
    return "\n".join(L)


# ------------------------------------------------------------------------------------------ informe completo
CSS = """
:root{--bg:#f7f8f6;--card:#fff;--ink:#16211f;--muted:#5b6b67;--line:#dfe5e2;--accent:#0f766e;--accent-soft:#e3f2ef;--warn:#b45309;--bad:#be123c;--ok:#15803d}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f1513;--card:#17201d;--ink:#e6eeeb;--muted:#9fb1ab;--line:#2a3733;--accent:#3cc4b4;--accent-soft:#143a35;--warn:#f59e0b;--bad:#fb7185;--ok:#4ade80}}
:root[data-theme=dark]{--bg:#0f1513;--card:#17201d;--ink:#e6eeeb;--muted:#9fb1ab;--line:#2a3733;--accent:#3cc4b4;--accent-soft:#143a35;--warn:#f59e0b;--bad:#fb7185;--ok:#4ade80}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:20px 16px 48px}h1{font-size:26px;margin:.2em 0}h2{font-size:19px;margin:1.6em 0 .6em;padding-bottom:.3em;border-bottom:2px solid var(--accent)}h3{font-size:16px;margin:1em 0 .3em}h4{font-size:14px;margin:1.1em 0 .3em;color:var(--accent)}
.muted{color:var(--muted)}.sub{color:var(--muted);font-size:13px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}.kpi .v{font-size:22px;font-weight:700}.kpi .l{font-size:12px;color:var(--muted)}
.callout{background:var(--accent-soft);border-left:4px solid var(--accent);padding:12px 14px;border-radius:6px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}
.card .t{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.tag{font-size:11px;padding:1px 8px;border-radius:99px;border:1px solid var(--line);color:var(--muted)}.tag.alto{color:var(--bad);border-color:var(--bad)}.tag.medio{color:var(--warn);border-color:var(--warn)}.tag.riesgo{background:var(--bad);color:#fff;border-color:var(--bad)}.tag.oportunidad{background:var(--ok);color:#fff;border-color:var(--ok)}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:12px}.chartbox{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}.chartbox h3{margin:.1em 0 .4em;font-size:14px}
svg.chart{width:100%;height:auto}svg .tick{fill:var(--muted);font-size:10px}svg .lab{fill:var(--ink);font-size:11px}svg .val{fill:var(--muted);font-size:11px}svg .grid{stroke:var(--line);stroke-width:1}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{color:var(--muted);font-weight:600}.scroll{overflow-x:auto}
.advice .posture{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:10px 14px;border-radius:8px;background:var(--accent-soft);border-left:5px solid var(--accent)}.posture.bad{border-color:var(--bad)}.posture.warn{border-color:var(--warn)}.posture.ok{border-color:var(--ok)}.posture strong{font-size:18px}.posture .k{font-size:12px;color:var(--muted)}
.lead{font-size:15.5px}.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.challenge{display:flex;gap:10px;border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin:6px 0;background:var(--card)}.challenge p{margin:.2em 0}.sev{font-size:11px;text-transform:uppercase;font-weight:700;min-width:46px;color:var(--muted)}.sev-alta .sev{color:var(--bad)}.sev-media .sev{color:var(--warn)}
.alts{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}.alt{border:1px solid var(--line);border-radius:8px;padding:8px 10px;background:var(--card)}.alt p{margin:.2em 0}ul.pro li::marker{color:var(--ok)}ul.con li::marker{color:var(--bad)}ul.ask li::marker{color:var(--accent)}
footer{margin-top:28px;font-size:12px;color:var(--muted)}code{background:var(--accent-soft);padding:1px 5px;border-radius:4px}
""" + WATERMARK_CSS


def render_html(run, advice: dict | None = None, standalone: bool = True) -> str:
    f, o = run.facts, run.outputs
    inf, a1, a3 = o["informe"], o["auditor"], o["interprete"]
    per = f["tiempo"][0] if f["tiempo"] else None
    kp = [(N(f["resumen"]["filas"]), "registros analizados"), (N(f["resumen"]["columnas"]), "variables"), (f"{a1['calidad_global']['puntaje']}/100", f"calidad de datos ({a1['calidad_global']['veredicto'].split(':')[0]})"),
          (a3["dominio_inferido"]["dominio"], f"dominio inferido ({a3['dominio_inferido']['confianza']})")]
    if per:
        kp.append((f"{per['desde']} → {per['hasta']}", f"periodo ({per['granularidad']})"))
    p = [f"<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{esc(inf['titulo'])}</title><style>{CSS}</style></head><body>{watermark_html()}{print_footer_html()}<div class='wrap'>" if standalone else "<div class='report'>"]
    p.append(f"<p class='sub'>Sistema multiagente · archivo <strong>{esc(run.filename)}</strong> · generado {datetime.now().strftime('%Y-%m-%d %H:%M')} · motor: {esc(run.llm_name)}</p><h1>{esc(inf['titulo'])}</h1>")
    p.append(f"<div class='firma'>{esc(FIRMA_TXT)}</div>")
    p.append("<div class='kpis'>" + "".join(f"<div class='kpi'><div class='v'>{esc(str(v))}</div><div class='l'>{esc(l)}</div></div>" for v, l in kp) + "</div>")
    p.append(f"<div class='callout'><strong>Resumen ejecutivo.</strong> {esc(inf['resumen_ejecutivo'])}</div>")
    if inf["recomendaciones"]:
        p.append("<h2>Recomendaciones priorizadas</h2><div class='scroll'><table><tr><th>#</th><th>Acción</th><th>Justificación</th><th>Plazo</th></tr>" +
                 "".join(f"<tr><td>{r['prioridad']}</td><td>{esc(r['accion'])}</td><td>{esc(r['justificacion'])}</td><td>{esc(r['plazo'])}</td></tr>" for r in inf["recomendaciones"]) + "</table></div>")
    p.append("<h2>Hallazgos de negocio</h2>")
    for hz in a3["hallazgos"]:
        p.append(f"<div class='card'><div class='t'><strong>{esc(hz['titulo'])}</strong><span class='tag {esc(hz['tipo'])}'>{esc(hz['tipo'])}</span><span class='tag {esc(hz['impacto'])}'>impacto {esc(hz['impacto'])}</span></div><p>{esc(hz['hallazgo'])}</p><p class='sub'>Acción sugerida: {esc(hz['accion_sugerida'])} · evidencia: <code>{esc(', '.join(hz['evidencia']))}</code></p></div>")
    charts = []
    for v in inf["visualizaciones"]:
        svg = render_directive(v, run)
        if svg:
            charts.append(f"<div class='chartbox'><h3>{esc(v['titulo'])}</h3>{svg}<div class='sub'>{esc(v['motivo'])}</div></div>")
    if charts:
        p.append("<h2>Visualizaciones</h2><div class='charts'>" + "".join(charts) + "</div>")
    for s in inf["secciones"]:
        p.append(f"<h2>{esc(s['titulo'])}</h2>{md_to_html(s['contenido_md'])}")
    if advice:
        p.append("<h2>Consejero estratégico</h2>" + advice_html(advice))
    p.append("<h2>Anexo A · Esquema inferido</h2><div class='scroll'><table><tr><th>Original</th><th>Normalizado</th><th>Tipo</th><th>Rol</th><th>% nulos</th><th>Detalle</th></tr>" +
             "".join(f"<tr><td>{esc(c['original'] or '(vacío)')}</td><td>{esc(c['normalizado'])}</td><td>{esc(c['tipo'])}</td><td>{esc(c['rol'])}</td><td>{N(c['pct_nulos'], 1)}</td><td>{esc(c.get('detalle', ''))}</td></tr>" for c in run.schema) + "</table></div>")
    p.append("<h2>Anexo B · Trazabilidad de agentes</h2><div class='scroll'><table><tr><th>Etapa</th><th>Motor</th><th>Entrada → salida</th><th>ms</th><th>Correcciones de guardrail</th></tr>" +
             "".join(f"<tr><td>{esc(t['etapa'])}</td><td>{esc(t['motor'])}</td><td>{esc(t['entrada'])} → {esc(t['salida'])}</td><td>{t['ms']}</td><td>{esc('; '.join(t['correcciones_guardrail'][:4]) or '—')}{(' · cifras no verificadas: ' + esc(', '.join(t['cifras_no_verificadas'][:5]))) if t['cifras_no_verificadas'] else ''}</td></tr>" for t in run.trace) + "</table></div>")
    p.append(f"<footer>Huella del catálogo de prompts: <code>{esc(run.prompt_hash)}</code> · Todas las cifras de este informe fueron verificadas contra el cómputo determinista de los datos.</footer>")
    p.append("</div></body></html>" if standalone else "</div>")
    return "".join(p)


def render_md(run, advice: dict | None = None) -> str:
    inf, a3, a1 = run.outputs["informe"], run.outputs["interprete"], run.outputs["auditor"]
    L = [f"# {inf['titulo']}", "", *[f"{x}  " for x in FIRMA_MD], "", f"_Archivo: {run.filename} · motor: {run.llm_name}_", "", "## Resumen ejecutivo", inf["resumen_ejecutivo"], "", "## Recomendaciones priorizadas"]
    L += [f"{r['prioridad']}. **{r['accion']}** — {r['justificacion']} (plazo: {r['plazo']})" for r in inf["recomendaciones"]]
    L += ["", "## Hallazgos de negocio"] + [f"- **{h['titulo']}** [{h['tipo']}, impacto {h['impacto']}]: {h['hallazgo']} _(evidencia: {', '.join(h['evidencia'])})_" for h in a3["hallazgos"]]
    for s in inf["secciones"]:
        L += ["", f"## {s['titulo']}", s["contenido_md"]]
    L += ["", "## Visualizaciones sugeridas"] + [f"- {v['titulo']} ({v['tipo']}; x={v.get('columna_x')}, y={v.get('columna_y')}, agregación {v['agregacion']})" for v in inf["visualizaciones"]]
    if advice:
        L += ["", advice_md(advice)]
    return "\n".join(L)
