# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Construcción de esquema (mapeo dinámico de variables) y ejecución del plan de limpieza.

El Agente 1 PROPONE el esquema (tipos/roles); este módulo lo VALIDA contra la evidencia y lo EJECUTA.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from .profiler import (ID_HINTS, ROLES, TYPES, _name_has, canonical_categories, infer_column, is_null, normalize_headers,
                       parse_date, parse_number)
from .text_utils import norm_key

MEASURE_NONNEG_HINTS = ("cantidad", "unidades", "precio", "valor", "total", "monto", "importe", "edad", "dias", "costo", "ingreso", "venta", "peso", "stock")


def build_schema(raw: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Esquema determinista inicial (percepción). Devuelve (schema, log_encabezados)."""
    names, hlog = normalize_headers(list(raw.columns))
    schema = []
    for orig, name in zip(raw.columns, names):
        info = infer_column(raw[orig].tolist(), name)
        info.update(original=str(orig), normalizado=name)
        tokens_ocultos = sum(1 for v in raw[orig] if str(v).strip() != "" and is_null(v))
        info["tokens_nulo_ocultos"] = tokens_ocultos
        schema.append(info)
    return schema, hlog


def validate_schema_override(proposed: dict, base: dict) -> tuple[dict, list[str]]:
    """Acepta ajustes del LLM solo si son coherentes con la evidencia. Devuelve (entrada_final, notas)."""
    notes = []
    out = dict(base)
    t, r = proposed.get("tipo"), proposed.get("rol")
    if t in TYPES and t != base["tipo"]:
        ok = True
        if t == "numerico" and base["tipo"] != "numerico":
            ok = base.get("tasa_parseo", 0) >= 0.9
        if t == "fecha" and base["tipo"] != "fecha":
            ok = False
        if t == "vacia":
            ok = base["n_no_nulos"] == 0
        if ok:
            out["tipo"] = t
            notes.append(f"{base['normalizado']}: tipo {base['tipo']}→{t} (propuesta del agente aceptada).")
        else:
            notes.append(f"{base['normalizado']}: propuesta de tipo '{t}' rechazada por evidencia insuficiente (se conserva '{base['tipo']}').")
    if r in ROLES and r != base["rol"]:
        compat = {"medida": {"numerico"}, "fecha": {"fecha"}, "texto": {"texto_libre", "categorico"}, "indicador": {"booleano", "categorico"},
                  "dimension": {"categorico", "numerico", "booleano", "fecha"}, "identificador": set(TYPES), "descartable": set(TYPES)}
        if out["tipo"] in compat[r]:
            out["rol"] = r
            notes.append(f"{base['normalizado']}: rol {base['rol']}→{r}.")
        else:
            notes.append(f"{base['normalizado']}: propuesta de rol '{r}' rechazada: incompatible con el tipo '{out['tipo']}' (se conserva '{base['rol']}').")
    return out, notes


def apply_cleaning(raw: pd.DataFrame, schema: list[dict]) -> tuple[pd.DataFrame, dict]:
    """Ejecuta el plan de limpieza. Devuelve (DataFrame tipado, reporte de acciones/calidad)."""
    log: dict = {"acciones": [], "valores_no_parseables": {}, "variantes_unificadas": {}, "duplicados_eliminados": 0}
    data = {}
    today = date.today()
    for col in schema:
        s = raw[col["original"]]
        name, tipo = col["normalizado"], col["tipo"]
        vals = [None if is_null(v) else str(v).strip() for v in s]
        if tipo == "numerico":
            dec = col.get("decimal", ".")
            parsed = [parse_number(v, dec) if v is not None else None for v in vals]
            bad = sum(1 for v, p in zip(vals, parsed) if v is not None and p is None)
            if bad:
                log["valores_no_parseables"][name] = bad
            data[name] = pd.array([np.nan if p is None else p for p in parsed], dtype="float64")
            if col.get("n_estilos", 1) > 1 or col.get("es_moneda"):
                log["acciones"].append(f"{name}: numérico normalizado (símbolos de moneda/%, separadores de miles y decimales unificados).")
        elif tipo == "fecha":
            df_first = col.get("dayfirst", True)
            parsed = [parse_date(v, df_first) if v is not None else None for v in vals]
            bad = sum(1 for v, p in zip(vals, parsed) if v is not None and p is None)
            if bad:
                log["valores_no_parseables"][name] = bad
            data[name] = pd.to_datetime(pd.Series([pd.Timestamp(p) if p else pd.NaT for p in parsed]))
            if col.get("n_formatos", 1) > 1:
                log["acciones"].append(f"{name}: {col['n_formatos']} formatos de fecha heterogéneos estandarizados a AAAA-MM-DD.")
            else:
                log["acciones"].append(f"{name}: fechas convertidas a AAAA-MM-DD.")
        elif tipo == "booleano":
            truthy = {"si", "true", "verdadero", "yes", "s", "y", "1", "x"}
            data[name] = pd.Series([None if v is None else norm_key(v) in truthy for v in vals], dtype="object")
        elif tipo == "categorico":
            present = [v for v in vals if v is not None]
            mapping, merged = canonical_categories(present)
            if merged:
                log["variantes_unificadas"][name] = merged
                log["acciones"].append(f"{name}: {merged} variante(s) ortográficas/de mayúsculas unificadas.")
            data[name] = pd.Series([mapping.get(v, v) if v is not None else None for v in vals], dtype="object")
        else:  # texto_libre, identificador, vacia
            data[name] = pd.Series(vals, dtype="object")
    clean = pd.DataFrame(data)
    # duplicados exactos: solo se eliminan si hay evidencia de que una repetición NO puede ser legítima
    # (hay identificador, o ≥5 columnas con una fecha); sin eso, filas idénticas pueden ser casos reales distintos
    before = len(clean)
    dups = int(clean.duplicated().sum())
    can_dedupe = any(c["tipo"] == "identificador" for c in schema) or (len(schema) >= 5 and any(c["tipo"] == "fecha" for c in schema))
    log["duplicados_detectados"] = dups
    if can_dedupe:
        clean = clean.drop_duplicates().reset_index(drop=True)
        log["duplicados_eliminados"] = before - len(clean)
    else:
        log["duplicados_eliminados"] = 0
        if dups:
            log["acciones"].append(f"Se detectaron {dups} fila(s) idénticas, pero se CONSERVAN: sin identificador no se distingue un duplicado de un caso repetido legítimo.")
    if log["duplicados_eliminados"]:
        log["acciones"].append(f"Se eliminaron {log['duplicados_eliminados']} fila(s) duplicadas exactas.")
    # nulos ocultos
    hidden = {c["normalizado"]: c["tokens_nulo_ocultos"] for c in schema if c.get("tokens_nulo_ocultos")}
    if hidden:
        log["acciones"].append("Marcadores de nulo tratados como N/A (sin imputar): " + ", ".join(f"{k} ({v})" for k, v in hidden.items()) + ".")
    log["nulos_ocultos"] = hidden
    log["filas_originales"], log["filas_finales"] = before, len(clean)
    # post-calidad
    log["issues"], log["score"] = quality_issues(clean, schema, log, today)
    return clean, log


def _sev(p: float) -> str:
    return "alta" if p >= 50 else "media" if p >= 20 else "baja"


def quality_issues(clean: pd.DataFrame, schema: list[dict], log: dict, today: date) -> tuple[list[dict], dict]:
    issues: list[dict] = []
    n = max(len(clean), 1)
    null_pcts = []
    for col in schema:
        name = col["normalizado"]
        pct = round(float(clean[name].isna().mean() * 100), 2)
        null_pcts.append(pct)
        col["pct_nulos"] = pct
        col["nulos"] = int(clean[name].isna().sum())
        if pct >= 5:
            issues.append({"severidad": _sev(pct), "columna": name, "tipo": "nulos", "detalle": f"{pct}% de valores ausentes", "accion": "Se reportan como N/A; no se imputan valores."})
        if col["original"].strip() == "" or name.startswith("columna_sin_nombre"):
            issues.append({"severidad": "media", "columna": name, "tipo": "columna_sin_nombre", "detalle": "Encabezado vacío o genérico", "accion": f"Nombre asignado: {name}."})
        if col["tipo"] == "fecha" and col.get("n_formatos", 1) > 1:
            issues.append({"severidad": "media", "columna": name, "tipo": "formato_mixto", "detalle": f"{col['n_formatos']} formatos de fecha: {', '.join(col['formatos'])}", "accion": "Estandarizado a AAAA-MM-DD."})
        if col["tipo"] == "numerico" and col.get("n_estilos", 1) > 1:
            issues.append({"severidad": "baja", "columna": name, "tipo": "formato_mixto", "detalle": f"Estilos numéricos mezclados: {', '.join(col['estilos'])}", "accion": "Unificado a número decimal."})
        if col["tipo"] == "fecha":
            s = clean[name].dropna()
            if len(s):
                fut = int((s.dt.date > today).sum())
                old = int((s.dt.year < 1990).sum())
                if fut:
                    issues.append({"severidad": "media", "columna": name, "tipo": "fechas_futuras", "detalle": f"{fut} fecha(s) posteriores a hoy", "accion": "Revisar con la fuente; se conservan."})
                if old:
                    issues.append({"severidad": "baja", "columna": name, "tipo": "fechas_antiguas", "detalle": f"{old} fecha(s) anteriores a 1990", "accion": "Revisar con la fuente."})
        if col["tipo"] == "numerico":
            s = clean[name].dropna()
            if len(s) > 10:
                if _name_has(name, MEASURE_NONNEG_HINTS) and int((s < 0).sum()):
                    issues.append({"severidad": "media", "columna": name, "tipo": "negativos_incoherentes", "detalle": f"{int((s < 0).sum())} valor(es) negativo(s) en variable que normalmente no lo es", "accion": "Se conservan y se señalan; verificar si son devoluciones/errores."})
                q1, q3 = s.quantile([0.25, 0.75])
                iqr = q3 - q1
                if iqr > 0:
                    ext = int(((s < q1 - 3 * iqr) | (s > q3 + 3 * iqr)).sum())
                    if ext / len(s) >= 0.002 and ext >= 2:
                        issues.append({"severidad": "baja", "columna": name, "tipo": "outliers_extremos", "detalle": f"{ext} valor(es) extremos (>3×IQR)", "accion": "Se conservan; las métricas robustas (mediana) se reportan junto a la media."})
        if col["tipo"] != "vacia" and col["rol"] not in ("descartable",) and clean[name].nunique(dropna=True) == 1 and len(clean) > 20:
            issues.append({"severidad": "baja", "columna": name, "tipo": "constante", "detalle": "La columna tiene un único valor", "accion": "Sin poder discriminante; se excluye del análisis comparativo."})
        if col["tipo"] == "vacia":
            issues.append({"severidad": "alta", "columna": name, "tipo": "vacia", "detalle": "Columna sin ningún valor", "accion": "Excluida del análisis."})
        if col["tipo"] == "identificador" and clean[name].notna().any():
            dup = int(clean[name].dropna().duplicated().sum())
            if dup:
                issues.append({"severidad": "media", "columna": name, "tipo": "id_duplicado", "detalle": f"{dup} identificador(es) repetidos con contenido distinto", "accion": "Verificar si son re-registros o actualizaciones."})
    if log["duplicados_eliminados"]:
        pct = round(100 * log["duplicados_eliminados"] / max(log["filas_originales"], 1), 2)
        issues.append({"severidad": "media" if pct >= 2 else "baja", "columna": "(filas)", "tipo": "duplicados", "detalle": f"{log['duplicados_eliminados']} fila(s) duplicadas ({pct}%)", "accion": "Eliminadas."})
    if log.get("duplicados_detectados") and not log["duplicados_eliminados"]:
        issues.append({"severidad": "baja", "columna": "(filas)", "tipo": "duplicados_conservados", "detalle": f"{log['duplicados_detectados']} fila(s) idénticas", "accion": "Conservadas: sin identificador no pueden distinguirse de casos repetidos legítimos."})
    if log.get("variantes_unificadas"):
        tot = sum(log["variantes_unificadas"].values())
        issues.append({"severidad": "baja", "columna": ", ".join(log["variantes_unificadas"]), "tipo": "categorias_inconsistentes", "detalle": f"{tot} variante(s) de escritura de una misma categoría", "accion": "Unificadas por forma canónica."})
    if log.get("nulos_ocultos"):
        issues.append({"severidad": "baja", "columna": ", ".join(log["nulos_ocultos"]), "tipo": "nulos_ocultos", "detalle": "Marcadores de nulo no estándar ('N/A', '-', '?', ...)", "accion": "Convertidos a N/A real."})
    nonempty_cols = max(sum(1 for c in schema if c["tipo"] != "vacia"), 1)
    sparse_rows = int((clean.isna().sum(axis=1) / max(clean.shape[1], 1) > 0.7).sum())
    if sparse_rows / n > 0.02:
        issues.append({"severidad": "media", "columna": "(filas)", "tipo": "filas_casi_vacias", "detalle": f"{sparse_rows} fila(s) con más de 70% de campos vacíos", "accion": "Se conservan; considerar excluirlas."})
    avg_null = float(np.mean(null_pcts)) if null_pcts else 0.0
    mixed = sum(1 for i in issues if i["tipo"] == "formato_mixto")
    unnamed = sum(1 for i in issues if i["tipo"] == "columna_sin_nombre")
    dup_pct = 100 * log["duplicados_eliminados"] / max(log["filas_originales"], 1)
    other = sum(1 for i in issues if i["tipo"] in ("negativos_incoherentes", "outliers_extremos", "fechas_futuras", "id_duplicado", "filas_casi_vacias", "vacia"))
    score = 100 - min(45, avg_null * 1.0) - min(15, dup_pct * 1.5) - min(15, mixed * 3) - min(10, unnamed * 2.5) - min(15, other * 2)
    score = int(round(max(0, min(100, score))))
    veredicto = "alta" if score >= 85 else "aceptable" if score >= 65 else "baja: usar con cautela" if score >= 40 else "crítica: resultados poco confiables"
    order = {"alta": 0, "media": 1, "baja": 2}
    issues.sort(key=lambda i: order[i["severidad"]])
    return issues, {"puntaje": score, "veredicto": veredicto, "pct_nulos_promedio": round(avg_null, 2), "columnas_con_nulos": sum(1 for p in null_pcts if p > 0)}
