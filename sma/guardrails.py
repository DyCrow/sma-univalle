# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Guardrails: validación de esquema JSON, extracción robusta de JSON y verificación anti-alucinación de cifras."""
from __future__ import annotations

import json
import re

from .profiler import parse_number

# ------------------------------------------------------------------ JSON ---------------------------------------


def extract_json(text: str):
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    start = min([i for i in (t.find("{"), t.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("La respuesta no contiene JSON.")
    depth, in_str, esc = 0, False, False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
            if depth == 0:
                return json.loads(t[start:i + 1])
    raise ValueError("JSON incompleto o mal formado.")


def validate(spec, obj, path: str = "$") -> list[str]:
    """Valida obj contra spec. Devuelve lista de problemas (vacía = válido)."""
    errs: list[str] = []
    if isinstance(spec, str):
        nullable = spec.endswith("?")
        t = spec.rstrip("?")
        if obj is None:
            return [] if nullable or t == "any" else [f"{path}: se esperaba {t}, llegó null"]
        ok = {"str": isinstance(obj, str), "num": isinstance(obj, (int, float)) and not isinstance(obj, bool),
              "int": isinstance(obj, int) and not isinstance(obj, bool), "bool": isinstance(obj, bool), "any": True}[t]
        return [] if ok else [f"{path}: se esperaba {t}, llegó {type(obj).__name__}"]
    if isinstance(spec, list):
        if not isinstance(obj, list):
            return [f"{path}: se esperaba lista"]
        for i, it in enumerate(obj[:50]):
            errs += validate(spec[0], it, f"{path}[{i}]")
        return errs
    if isinstance(spec, dict):
        if not isinstance(obj, dict):
            return [f"{path}: se esperaba objeto"]
        for k, sub in spec.items():
            if k not in obj:
                errs.append(f"{path}.{k}: clave obligatoria ausente")
            else:
                errs += validate(sub, obj[k], f"{path}.{k}")
    return errs


# ------------------------------------------------------------------ cifras -------------------------------------
_NUM_TOKEN = re.compile(r"(?<![\w.])[-+]?\d[\d.,]*\d(?:\s?%)?|(?<![\w.])\d(?:\s?%)?")
_SCALE = re.compile(r"\s*(millones|millón|mil millones|miles|mil|M\b|k\b)", re.I)


def _candidates(tok: str, tail: str) -> tuple[set[float], float]:
    """Posibles valores numéricos de un token (ambigüedad miles/decimales) y su multiplicador de escala."""
    s = tok.replace("%", "").strip()
    vals = set()
    for dec in (".", ","):
        v = parse_number(s, dec)
        if v is not None:
            vals.add(v)
    mult = 1.0
    m = _SCALE.match(tail)
    if m:
        w = m.group(1).lower()
        mult = 1e9 if "mil millones" in w else 1e6 if w.startswith("mill") or w == "m" else 1e3
        vals = {v * mult for v in vals}
    return vals, mult


def unverified_numbers(text: str, whitelist: set[float], ignore_small_ints: bool = True) -> list[str]:
    """Devuelve los tokens numéricos del texto que NO aparecen (con tolerancia de redondeo) en la lista blanca."""
    bad = []
    wl = list(whitelist)
    for m in _NUM_TOKEN.finditer(text):
        tok = m.group(0)
        tail = text[m.end(): m.end() + 12]
        if m.start() > 0 and text[m.start() - 1] == "/":  # denominador de una escala (p. ej. 96/100)
            continue
        raw = tok.replace("%", "").strip()
        is_pct = "%" in tok
        if re.fullmatch(r"\d{4}", raw) and 1990 <= int(raw) <= 2100 and not is_pct:
            continue
        if ignore_small_ints and re.fullmatch(r"\d{1,2}", raw) and int(raw) <= 31 and not is_pct:
            continue
        cands, mult = _candidates(tok, tail)
        if not cands:
            continue
        ok = False
        for c in cands:
            decs = len(raw.split(",")[-1]) if "," in raw and not re.search(r",\d{3}$", raw) else len(raw.split(".")[-1]) if "." in raw and not re.search(r"\.\d{3}$", raw) else 0
            tol = max(0.5 * 10 ** (-decs) * mult + 0.0051, 0.002 * abs(c))  # redondeo de impresión + redondeo de los hechos (2 dec.)
            if any(abs(c - w) <= tol for w in wl):
                ok = True
                break
            if is_pct and any(abs(c - w * 100) <= tol for w in wl if abs(w) <= 1.5):
                ok = True
                break
        if not ok:
            bad.append(tok.strip())
    return bad
