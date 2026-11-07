# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Herramientas deterministas de percepción: inferencia de tipos, parseo robusto y calidad de datos.

Son las "herramientas" de los agentes (tool use). Los LLM razonan; la aritmética y el parseo exacto
los hace código verificable, para minimizar alucinaciones numéricas.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime

import numpy as np

from .text_utils import norm_key, snake, strip_accents

NULL_TOKENS = {
    "", "na", "n/a", "n.a.", "n.a", "nan", "null", "none", "nil", "-", "--", "---", "?", "??", "s/d", "sd", "s.d.",
    "sin dato", "sin datos", "sin informacion", "no aplica", "n.d.", "nd", "#n/a", "#value!", "#div/0!", "#ref!",
    "nulo", "missing", "vacio", "ninguno", "ninguna", "no disponible", "desconocido", "por definir", "xxx",
}


def is_null(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and np.isnan(v):
        return True
    return norm_key(str(v)) in NULL_TOKENS


# ------------------------------------------------------------------------------------------------
# NÚMEROS
# ------------------------------------------------------------------------------------------------
_CUR = re.compile(r"(cop|usd|eur|mxn|us\$|col\$|\$|€|£)", re.I)


def _clean_num_str(s: str) -> tuple[str, bool]:
    s = str(s).strip().replace(" ", " ")
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    s = _CUR.sub("", s).replace("%", "").replace(" ", "")
    return s, neg


def detect_decimal_convention(values: list[str]) -> str:
    """'.' o ',' según la evidencia de la columna completa (formatos mixtos incluidos)."""
    comma_dec = dot_dec = thou_dot = thou_com = 0
    for v in values[:3000]:
        s, _ = _clean_num_str(v)
        if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
            thou_dot += 1
        if re.fullmatch(r"-?\d{1,3}(,\d{3})+", s):
            thou_com += 1
        if re.search(r"\d,\d{1,2}$", s) and not re.search(r"\d,\d{3}$", s):
            comma_dec += 1
        if re.search(r"\d\.\d{1,2}$", s) and not re.search(r"\d\.\d{3}$", s):
            dot_dec += 1
        if re.search(r"\d\.\d{3},\d+$", s):
            comma_dec += 2
        if re.search(r"\d,\d{3}\.\d+$", s):
            dot_dec += 2
    if comma_dec > dot_dec:
        return ","
    if dot_dec == 0 and comma_dec == 0 and thou_dot > thou_com:
        return ","  # el punto actúa como separador de miles (convención colombiana)
    return "."


def parse_number(v, decimal: str = ".") -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return None if (isinstance(v, float) and np.isnan(v)) else float(v)
    s, neg = _clean_num_str(v)
    if not s or not re.search(r"\d", s) or re.search(r"[A-Za-z]", s) and not re.fullmatch(r"[-+]?\d+(\.\d+)?[eE][-+]?\d+", s):
        return None
    sign = -1.0 if neg else 1.0
    if s[0] in "+-":
        sign *= -1.0 if s[0] == "-" else 1.0
        s = s[1:]
    if not re.fullmatch(r"[\d.,]+|\d+(\.\d+)?[eE][-+]?\d+", s):
        return None
    if re.fullmatch(r"\d+(\.\d+)?[eE][-+]?\d+", s):
        return sign * float(s)
    has_dot, has_com = "." in s, "," in s
    try:
        if has_dot and has_com:
            dec = "." if s.rfind(".") > s.rfind(",") else ","
            thou = "," if dec == "." else "."
            return sign * float(s.replace(thou, "").replace(dec, "."))
        if has_com or has_dot:
            sep = "," if has_com else "."
            parts = s.split(sep)
            if len(parts) > 2:  # 1.234.567 -> miles
                return sign * float("".join(parts))
            if len(parts[1]) == 3 and decimal != sep and len(parts[0]) <= 3:  # 1.234 con '.' = miles; con ',' = miles
                return sign * float(parts[0] + parts[1])
            if len(parts[1]) == 3 and decimal != sep:
                return sign * float(parts[0] + parts[1])
            return sign * float(parts[0] + "." + parts[1])
        return sign * float(s)
    except ValueError:
        return None


# ------------------------------------------------------------------------------------------------
# FECHAS
# ------------------------------------------------------------------------------------------------
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "sept": 9, "oct": 10,
    "nov": 11, "dic": 12, "january": 1, "february": 2, "march": 3, "april": 4, "june": 6, "july": 7,
    "august": 8, "september": 9, "october": 10, "november": 11, "december": 12, "jan": 1, "apr": 4, "aug": 8, "dec": 12,
}
_FMT = [
    ("AAAA-MM-DD", re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T\s]\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$")),
    ("AAAA/MM/DD", re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$")),
    ("DD/MM/AAAA", re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s?[ap]\.?m\.?)?)?$", re.I)),
    ("DD-MM-AAAA", re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{2,4})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$")),
    ("DD.MM.AAAA", re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$")),
    ("D de mes de AAAA", re.compile(r"^(\d{1,2})\s+(?:de\s+)?([a-záéíóúñ]+)\.?,?\s+(?:de(?:l)?\s+)?(\d{4})$", re.I)),
    ("mes D, AAAA", re.compile(r"^([a-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})$", re.I)),
]


def _mk(y: int, m: int, d: int) -> date | None:
    if y < 100:
        y += 2000 if y < 70 else 1900
    try:
        return date(y, m, d)
    except ValueError:
        return None


def date_format_of(s: str) -> str | None:
    s = str(s).strip()
    for name, rx in _FMT:
        if rx.match(s):
            return name
    return None


def parse_date(v, dayfirst: bool = True) -> date | None:
    if isinstance(v, (datetime,)):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for name, rx in _FMT:
        m = rx.match(s)
        if not m:
            continue
        g = m.groups()
        if name in ("AAAA-MM-DD", "AAAA/MM/DD"):
            return _mk(int(g[0]), int(g[1]), int(g[2]))
        if name in ("DD/MM/AAAA", "DD-MM-AAAA", "DD.MM.AAAA"):
            a, b, y = int(g[0]), int(g[1]), int(g[2])
            if a > 12:
                return _mk(y, b, a)
            if b > 12:
                return _mk(y, a, b)
            return _mk(y, b, a) if dayfirst else _mk(y, a, b)
        if name == "D de mes de AAAA":
            mo = MESES.get(strip_accents(g[1]).lower())
            return _mk(int(g[2]), mo, int(g[0])) if mo else None
        if name == "mes D, AAAA":
            mo = MESES.get(strip_accents(g[0]).lower())
            return _mk(int(g[2]), mo, int(g[1])) if mo else None
    return None


def detect_dayfirst(values: list[str]) -> bool:
    d_first = m_first = 0
    for v in values[:3000]:
        m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.]\d{2,4}", str(v).strip())
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > 12:
                d_first += 1
            elif b > 12:
                m_first += 1
    return not (m_first > d_first)


# ------------------------------------------------------------------------------------------------
# INFERENCIA DE TIPO / ROL SEMÁNTICO
# ------------------------------------------------------------------------------------------------
BOOL_SETS = {"si", "no", "true", "false", "verdadero", "falso", "yes", "1", "0"}  # sin letras sueltas: 'N'/'S' pueden ser Norte/Sur
ID_HINTS = ("id", "codigo", "cod", "folio", "radicado", "referencia", "ref", "nro", "numero", "num", "documento",
            "cedula", "nit", "telefono", "celular", "sku", "guia", "ticket", "factura", "serial")
CODE_NUMERIC_HINTS = ("anio", "ano", "year", "mes", "month", "dia", "semana", "week", "estrato", "zip", "cp", "trimestre", "periodo")
TYPES = ["numerico", "fecha", "categorico", "texto_libre", "identificador", "booleano", "vacia"]
ROLES = ["medida", "dimension", "fecha", "identificador", "texto", "indicador", "descartable"]


def _name_has(name: str, hints, exact: bool = False) -> bool:
    toks = set(name.split("_"))
    if exact:
        return any(h in toks for h in hints)
    return any(h in toks or (len(h) > 3 and h in name) for h in hints)


def infer_column(raw_values: list[str], norm_name: str) -> dict:
    """Infiere tipo, formato y rol para una columna de texto crudo."""
    n_total = len(raw_values)
    vals = [str(v).strip() for v in raw_values if not is_null(v)]
    n = len(vals)
    info: dict = {"n_total": n_total, "n_no_nulos": n, "nulos": n_total - n, "pct_nulos": round(100 * (n_total - n) / n_total, 2) if n_total else 0.0}
    if n == 0:
        info.update(tipo="vacia", rol="descartable", detalle="Sin valores utilizables.")
        return info
    uniq = len(set(vals))
    ratio = uniq / n
    lowered = {norm_key(v) for v in vals}

    # booleano
    if len(lowered) <= 2 and lowered <= BOOL_SETS and not (lowered <= {"0", "1"} and False):
        info.update(tipo="booleano", rol="indicador", detalle="Dos estados.", n_unicos=uniq)
        return info

    # fecha
    fmts = Counter(date_format_of(v) for v in vals)
    fmts.pop(None, None)
    date_hits = sum(fmts.values())
    if date_hits / n >= 0.85:
        dayfirst = detect_dayfirst(vals)
        parsed = sum(1 for v in vals if parse_date(v, dayfirst))
        if parsed / n >= 0.85:
            info.update(tipo="fecha", rol="fecha", dayfirst=dayfirst, formatos=dict(fmts), n_formatos=len(fmts), tasa_parseo=round(parsed / n, 4),
                        detalle=f"{len(fmts)} formato(s) de fecha: {', '.join(fmts)}")
            return info

    # numérico
    codeish = bool(re.match(r"^0\d+$", vals[0])) and all(re.match(r"^\d+$", v) for v in vals[:50])
    decimal = detect_decimal_convention(vals)
    nums = [parse_number(v, decimal) for v in vals]
    ok = sum(x is not None for x in nums)
    if ok / n >= 0.9 and not codeish:
        arr = np.array([x for x in nums if x is not None])
        is_int = bool(np.all(np.mod(arr, 1) == 0))
        styles = set()
        for v in vals[:3000]:
            s = v.strip()
            style = ("moneda" if _CUR.search(s) else "") + ("%" if "%" in s else "") + ("coma_dec" if re.search(r"\d,\d{1,2}$", s) else "") + ("punto_dec" if re.search(r"\d\.\d{1,2}$", s) else "")
            styles.add(style or "plano")
        info.update(tipo="numerico", decimal=decimal, entero=is_int, tasa_parseo=round(ok / n, 4), n_estilos=len(styles), estilos=sorted(styles),
                    es_moneda=any("moneda" in s for s in styles), es_porcentaje=any("%" in s for s in styles), n_unicos=uniq)
        sorted_consecutive = is_int and ratio > 0.95 and arr.size > 5 and (np.ptp(arr) + 1) <= 1.05 * arr.size
        if (_name_has(norm_name, ID_HINTS) and is_int and ratio > 0.5) or sorted_consecutive or (ratio > 0.98 and is_int and arr.min() >= 1000 and _name_has(norm_name, ID_HINTS)):
            info.update(tipo="identificador", rol="identificador", detalle="Entero con unicidad casi total.")
        elif _name_has(norm_name, CODE_NUMERIC_HINTS, exact=True) and uniq <= 60:
            info.update(rol="dimension", detalle="Código numérico que actúa como categoría/periodo.")
        else:
            info.update(rol="medida", detalle="Variable cuantitativa continua/discreta.")
        return info

    # texto
    lens = np.array([len(v) for v in vals])
    words = np.array([len(v.split()) for v in vals])
    avg_len, avg_words = float(lens.mean()), float(words.mean())
    info.update(n_unicos=uniq, long_media=round(avg_len, 1), palabras_media=round(avg_words, 1))
    if (avg_words >= 4 and avg_len >= 25) or avg_len >= 60:
        info.update(tipo="texto_libre", rol="texto", detalle="Texto libre (promedio de palabras alto).")
        return info
    if ratio > 0.9 and (_name_has(norm_name, ID_HINTS) or avg_words < 2.5):
        info.update(tipo="identificador", rol="identificador", detalle="Cadena con unicidad casi total.")
        return info
    if uniq <= 60 or ratio <= 0.3:
        info.update(tipo="categorico", rol="dimension", detalle=f"{uniq} categorías.")
    else:
        info.update(tipo="categorico", rol="dimension", alta_cardinalidad=True, detalle=f"Categórica de alta cardinalidad ({uniq}).")
    return info


def normalize_headers(cols: list[str]) -> tuple[list[str], list[dict]]:
    """Normaliza encabezados a snake_case sin tildes; nombra columnas sin nombre; desambigua duplicados."""
    out, log, seen = [], [], Counter()
    for i, c in enumerate(cols):
        orig = str(c)
        base = snake(orig)
        reason = None
        if not base or re.fullmatch(r"unnamed_?\d*(_.*)?", base) or re.fullmatch(r"column[a_]?\d*", base) and False:
            base, reason = f"columna_sin_nombre_{i + 1}", "encabezado vacío o genérico"
        if base[0].isdigit():
            base = "c_" + base
        seen[base] += 1
        name = base if seen[base] == 1 else f"{base}_{seen[base]}"
        if seen[base] > 1:
            reason = "encabezado duplicado"
        out.append(name)
        log.append({"original": orig, "normalizado": name, "motivo": reason})
    return out, log


def canonical_categories(values: list[str]) -> tuple[dict, int]:
    """Agrupa variantes ('queja', 'QUEJA ', 'Quejá') bajo la forma más frecuente. Devuelve (mapa, n_variantes_unificadas)."""
    groups: dict[str, Counter] = {}
    for v in values:
        groups.setdefault(norm_key(v), Counter())[str(v).strip()] += 1
    mapping, merged = {}, 0
    for key, forms in groups.items():
        canon = forms.most_common(1)[0][0]
        if canon.islower() or canon.isupper():
            canon = canon.title() if len(forms) > 1 or canon.isupper() else canon
        for f in forms:
            mapping[f] = canon
        merged += len(forms) - 1
    return mapping, merged
