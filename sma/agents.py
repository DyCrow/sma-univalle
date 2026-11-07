# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Clase Agent: ejecuta un prompt estructurado sobre un payload, valida, reintenta, aplica guardrails y cae a respaldo."""
from __future__ import annotations

import json
import re
import time
from typing import Callable

from .guardrails import _NUM_TOKEN, _candidates, extract_json, unverified_numbers, validate
from .llm import LLM
from .prompts import SCHEMAS, render_system_prompt

MAX_PAYLOAD_CHARS = 100_000
NV = "[cifra no verificada]"


def build_whitelist(*objs) -> set[float]:
    """Lista blanca de cifras: números de los objetos + números presentes en sus textos."""
    from .analytics import collect_numbers

    wl: set[float] = set()
    for o in objs:
        collect_numbers(o, wl)
        _numbers_from_strings(o, wl)
    wl |= {abs(x) for x in list(wl)}  # el sentido (subió/cayó) lo da el verbo; se verifica la magnitud
    return wl


def _numbers_from_strings(o, wl: set):
    if isinstance(o, str):
        for m in _NUM_TOKEN.finditer(o):
            c, _ = _candidates(m.group(0), o[m.end(): m.end() + 12])
            wl |= c
    elif isinstance(o, dict):
        for v in o.values():
            _numbers_from_strings(v, wl)
    elif isinstance(o, (list, tuple)):
        for v in o:
            _numbers_from_strings(v, wl)


def scrub_numbers(obj, wl: set[float], found: list[str]):
    """Recorre el JSON de salida y sustituye cifras no respaldadas por una marca explícita."""
    if isinstance(obj, str):
        bad = unverified_numbers(obj, wl)
        for b in dict.fromkeys(bad):
            found.append(b)
            obj = re.sub(r"(?<![\w.,])" + re.escape(b) + r"(?![\w])", NV, obj, count=0)
        return obj
    if isinstance(obj, dict):
        return {k: scrub_numbers(v, wl, found) if k not in ("ref", "id", "evidencia", "original", "normalizado", "columna", "a", "b", "medida", "dimension", "variable", "valor", "plazo") else v for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub_numbers(v, wl, found) for v in obj]
    return obj


class Agent:
    def __init__(self, key: str, offline_fn: Callable[[dict], dict], post_fn: Callable[[dict, dict, dict], dict] | None = None):
        self.key, self.offline_fn, self.post_fn = key, offline_fn, post_fn
        self.schema = SCHEMAS[key]

    def run(self, llm: LLM, payload: dict) -> tuple[dict, dict]:
        t0 = time.time()
        meta = {"agente": self.key, "motor": "determinista", "intentos": 0, "problemas_validacion": [], "correcciones_guardrail": [], "cifras_no_verificadas": []}
        out = None
        if llm.available:
            system = render_system_prompt(self.key)
            user = "PAYLOAD (JSON):\n" + json.dumps(payload, ensure_ascii=False, default=str)[:MAX_PAYLOAD_CHARS]
            base_user = user
            for attempt in range(2):
                meta["intentos"] += 1
                try:
                    txt = llm.complete(system, user)
                    obj = extract_json(txt)
                    errs = validate(self.schema, obj)
                    if errs:
                        meta["problemas_validacion"] += errs[:6]
                        user = base_user + "\n\nTU RESPUESTA ANTERIOR NO CUMPLIÓ EL ESQUEMA:\n- " + "\n- ".join(errs[:8]) + "\nCorrige y devuelve SOLO el JSON válido."
                        continue
                    out, meta["motor"] = obj, "llm"
                    break
                except Exception as e:  # noqa: BLE001
                    meta["problemas_validacion"].append(f"{type(e).__name__}: {str(e)[:160]}")
            if out is None:
                meta["motor"] = "llm→respaldo determinista"
        if out is None:
            out = self.offline_fn(payload)
        if self.post_fn:
            out = self.post_fn(out, payload, meta)
        meta["ms"] = int((time.time() - t0) * 1000)
        return out, meta


# ============================================================ post-procesadores (guardrails específicos) =============
def post_auditor(out: dict, payload: dict, meta: dict) -> dict:
    sch = {c["original"]: c for c in payload["esquema_preliminar"]}
    fixed = []
    seen = set()
    for m in out.get("mapeo_columnas", []):
        base = sch.get(m.get("original"))
        if not base:
            meta["correcciones_guardrail"].append(f"Columna inexistente descartada: {m.get('original')}")
            continue
        seen.add(m["original"])
        if abs(float(m.get("pct_nulos", 0)) - base["pct_nulos"]) > 0.01:
            meta["correcciones_guardrail"].append(f"pct_nulos de {base['normalizado']} corregido a valor medido ({base['pct_nulos']}).")
        m["pct_nulos"] = base["pct_nulos"]
        fixed.append(m)
    for o, base in sch.items():
        if o not in seen:
            meta["correcciones_guardrail"].append(f"Columna omitida por el agente, restituida: {base['normalizado']}.")
            fixed.append({"original": o, "normalizado": base["normalizado"], "tipo": base["tipo"], "rol": base["rol"], "pct_nulos": base["pct_nulos"]})
    out["mapeo_columnas"] = fixed
    return out


def post_analista(out: dict, payload: dict, meta: dict) -> dict:
    f = payload["hechos"]
    nums = {n["columna"]: n for n in f["numericas"]}
    refs = set(f["refs"])
    res = []
    for r in out.get("resumen_cuantitativo", []):
        t = nums.get(r.get("columna"))
        if not t:
            meta["correcciones_guardrail"].append(f"Variable inexistente en resumen_cuantitativo: {r.get('columna')} (descartada).")
            continue
        for k in ("n", "media", "mediana", "min", "max", "suma", "desv"):
            if r.get(k) is not None and t.get(k) is not None and abs(float(r[k]) - float(t[k])) > max(0.01, 0.002 * abs(float(t[k]))):
                meta["correcciones_guardrail"].append(f"{t['columna']}.{k}: {r[k]} → {t[k]} (valor medido).")
        res.append({k: t[k] for k in ("n", "media", "mediana", "min", "max", "suma", "desv")} | {"columna": t["columna"]})
    out["resumen_cuantitativo"] = res
    for sec in ("interacciones", "tendencias", "correlaciones", "anomalias"):
        keep = []
        for it in out.get(sec, []):
            if it.get("ref") in refs:
                keep.append(it)
            else:
                meta["correcciones_guardrail"].append(f"{sec}: ref inexistente '{it.get('ref')}' descartada.")
        out[sec] = keep
    cat = out.get("analisis_cualitativo", {})
    if len(cat.get("top_categorias", [])) > 5:
        meta["correcciones_guardrail"].append("top_categorias recortado a 5 (restricción AJ-03).")
        cat["top_categorias"] = cat["top_categorias"][:5]
    out["analisis_cualitativo"] = cat
    wl = build_whitelist(f)
    found: list[str] = []
    out = scrub_numbers(out, wl, found)
    meta["cifras_no_verificadas"] += found
    return out


def post_interprete(out: dict, payload: dict, meta: dict) -> dict:
    f = payload["hechos"]
    refs = set(f["refs"])
    keep = []
    for h in out.get("hallazgos", []):
        ev = [r for r in h.get("evidencia", []) if r in refs]
        if not ev:
            meta["correcciones_guardrail"].append(f"Hallazgo '{h.get('titulo')}' descartado: sin evidencia verificable.")
            continue
        h["evidencia"] = ev
        keep.append(h)
    out["hallazgos"] = keep
    have = {a["columna"] for a in out.get("alertas_datos_faltantes", [])}
    for c in payload["esquema"]:
        if c.get("pct_nulos", 0) >= 5 and c["normalizado"] not in have:
            out.setdefault("alertas_datos_faltantes", []).append({"columna": c["normalizado"], "pct_nulos": "N/A" if c["tipo"] == "vacia" else c["pct_nulos"], "impacto": "No se imputaron valores."})
            meta["correcciones_guardrail"].append(f"Alerta de nulos añadida para {c['normalizado']} ({c['pct_nulos']}%).")
    # nulos reales: sobreescribir con el valor medido
    nulos = {c["normalizado"]: c for c in payload["esquema"]}
    for a in out.get("alertas_datos_faltantes", []):
        c = nulos.get(a["columna"])
        if c and a["pct_nulos"] != "N/A" and abs(float(a["pct_nulos"]) - c["pct_nulos"]) > 0.01:
            meta["correcciones_guardrail"].append(f"pct_nulos de {a['columna']} corregido ({a['pct_nulos']} → {c['pct_nulos']}).")
            a["pct_nulos"] = c["pct_nulos"]
    wl = build_whitelist(f, payload["esquema"], payload.get("problemas", []))
    found: list[str] = []
    out = scrub_numbers(out, wl, found)
    meta["cifras_no_verificadas"] += found
    return out


def post_informe(out: dict, payload: dict, meta: dict) -> dict:
    cols = set(payload["columnas_validas"]) | {"__nulos__"}
    ok = []
    for v in out.get("visualizaciones", []):
        if v["tipo"] not in ("linea", "barras", "histograma", "pastel"):
            meta["correcciones_guardrail"].append(f"Visualización {v['id']} descartada: tipo '{v['tipo']}' no permitido.")
            continue
        if (v.get("columna_x") and v["columna_x"] not in cols) or (v.get("columna_y") and v["columna_y"] not in cols):
            meta["correcciones_guardrail"].append(f"Visualización {v['id']} descartada: columna inexistente.")
            continue
        ok.append(v)
    out["visualizaciones"] = ok
    words = out["resumen_ejecutivo"].split()
    if len(words) > 120:
        meta["correcciones_guardrail"].append(f"Resumen ejecutivo recortado de {len(words)} a 120 palabras.")
        out["resumen_ejecutivo"] = " ".join(words[:120])
    names = {"Calidad de datos y limitaciones"}
    if not any(s["titulo"] in names for s in out["secciones"]):
        meta["correcciones_guardrail"].append("Sección obligatoria de calidad añadida.")
        out["secciones"].append(payload["seccion_calidad"])
    wl = build_whitelist(payload["hechos"], payload["auditoria"], payload["analisis"], payload["interpretacion"])
    found: list[str] = []
    out = scrub_numbers(out, wl, found)
    meta["cifras_no_verificadas"] += found
    return out


def post_estratega(out: dict, payload: dict, meta: dict) -> dict:
    wl = build_whitelist(payload["hechos"], payload.get("contexto_usuario", {}), payload.get("senales", {}), payload.get("calidad", {}))
    found: list[str] = []
    out = scrub_numbers(out, wl, found)
    meta["cifras_no_verificadas"] += found
    if not out.get("cuestionamientos") and out.get("modo") in ("decision", "decisión"):
        meta["correcciones_guardrail"].append("El agente no cuestionó una decisión: se activó el cuestionamiento de respaldo.")
    return out
