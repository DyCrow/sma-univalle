# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Ingesta agnóstica: CSV / TSV / TXT / Excel / JSON / JSON-Lines -> DataFrame de TEXTO CRUDO.

Todo se lee como texto (str) para que el Auditor/Limpiador decida los tipos con evidencia.
No se asume esquema, delimitador, codificación ni presencia de encabezado.
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd

csv.field_size_limit(10_000_000)
MAX_ROWS = 500_000


def _cell(v) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(v, (datetime, pd.Timestamp)):
        return v.date().isoformat() if (v.hour, v.minute, v.second) == (0, 0, 0) else v.isoformat(sep=" ")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v).strip()


_NUM_RE = re.compile(r"^[\s$€£]*[-+(]?[\s$€£]*\d[\d.,\s]*\)?\s*%?$")
_DATE_RE = re.compile(r"^\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}")


def _datalike(s: str) -> bool:
    s = s.strip()
    return bool(s) and (bool(_NUM_RE.match(s)) or bool(_DATE_RE.match(s)))


def _looks_headerless(first: list[str], second: list[str] | None) -> bool:
    cells = [c for c in first if c.strip()]
    if not cells:
        return False
    frac = sum(_datalike(c) for c in cells) / len(cells)
    return frac >= 0.5


def _rows_to_df(rows: list[list[str]], notes: list[str]) -> pd.DataFrame:
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if not rows:
        raise ValueError("El archivo no contiene filas con datos.")
    # Filas de título encima del encabezado real (típico de Excel institucional)
    skipped = 0
    while len(rows) > 2 and sum(1 for c in rows[0] if str(c).strip()) == 1 and sum(1 for c in rows[1] if str(c).strip()) >= 2:
        rows = rows[1:]
        skipped += 1
    if skipped:
        notes.append(f"Se omitieron {skipped} fila(s) de título sobre el encabezado.")
    width = max(len(r) for r in rows)
    rows = [list(r) + [""] * (width - len(r)) for r in rows]
    # descartar columnas completamente vacías (sin encabezado ni datos)
    keep = [j for j in range(width) if any(str(r[j]).strip() for r in rows)]
    if len(keep) < width:
        notes.append(f"Se descartaron {width - len(keep)} columna(s) totalmente vacía(s).")
    rows = [[r[j] for j in keep] for r in rows]
    width = len(keep)
    headerless = _looks_headerless(rows[0], rows[1] if len(rows) > 1 else None)
    if headerless:
        header = [f"columna_{i + 1}" for i in range(width)]
        notes.append("No se detectó fila de encabezado: se asignaron nombres genéricos (columna_1, columna_2, ...).")
        body = rows
    else:
        header, body = rows[0], rows[1:]
    df = pd.DataFrame(body, columns=[str(h).strip() for h in header], dtype=object)
    return df.reset_index(drop=True)


def _decode(data: bytes, notes: list[str]) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            txt = data.decode(enc)
            if enc not in ("utf-8-sig", "utf-8"):
                notes.append(f"Codificación detectada: {enc} (no era UTF-8).")
            return txt
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _sniff_delimiter(text: str) -> str:
    lines = [l for l in text.splitlines()[:40] if l.strip()]
    best, best_score = "\x1f", -1.0  # por defecto: una sola columna (sin delimitador)
    for d in [",", ";", "\t", "|"]:
        counts = []
        for row in csv.reader(lines, delimiter=d):
            counts.append(len(row))
        if not counts:
            continue
        mode = max(set(counts), key=counts.count)
        if mode < 2 or counts[0] != mode:  # el encabezado también debe contener el delimitador (si no, es texto con comas internas)
            continue
        score = (counts.count(mode) / len(counts)) * (1 + min(mode, 30) / 30)
        if score > best_score:
            best, best_score = d, score
    return best


def _read_csv(data: bytes, notes: list[str]) -> pd.DataFrame:
    text = _decode(data, notes)
    delim = _sniff_delimiter(text)
    names = {",": "coma", ";": "punto y coma", "\t": "tabulación", "|": "barra vertical", "\x1f": "ninguno (archivo de una sola columna)"}
    notes.append(f"Delimitador detectado: {names[delim]}.")
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim)]
    if len(rows) > MAX_ROWS:
        notes.append(f"Archivo truncado a {MAX_ROWS} filas.")
        rows = rows[:MAX_ROWS]
    # filas ragged: se informan
    if rows:
        w = max(len(r) for r in rows[:50])
        bad = sum(1 for r in rows if r and len(r) != w)
        if bad:
            notes.append(f"{bad} fila(s) con número de campos distinto al esperado ({w}); se rellenaron/truncaron.")
        rows = [(r + [""] * (w - len(r)))[:w] for r in rows]
    return _rows_to_df([[_cell(c) for c in r] for r in rows], notes)


def _read_excel(data: bytes, notes: list[str]) -> pd.DataFrame:
    sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, header=None, dtype=object)
    if not sheets:
        raise ValueError("El libro de Excel no tiene hojas.")
    best = max(sheets.items(), key=lambda kv: kv[1].shape[0] * max(kv[1].shape[1], 1))
    if len(sheets) > 1:
        notes.append(f"El libro tiene {len(sheets)} hojas; se analizó la de mayor tamaño: '{best[0]}'.")
    rows = [[_cell(c) for c in r] for r in best[1].values.tolist()]
    return _rows_to_df(rows, notes)


def _read_json(data: bytes, notes: list[str]) -> pd.DataFrame:
    text = _decode(data, notes).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        objs = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                objs.append(json.loads(line))
        obj = objs
        notes.append("Formato JSON Lines (un objeto por línea).")

    def find_records(o):
        if isinstance(o, list):
            if o and all(isinstance(x, dict) for x in o):
                return o
            if o and all(not isinstance(x, (dict, list)) for x in o):
                return [{"valor": x} for x in o]
            return None
        if isinstance(o, dict):
            cands = [(k, find_records(v)) for k, v in o.items() if isinstance(v, (list, dict))]
            cands = [(k, c) for k, c in cands if c]
            if cands:
                k, c = max(cands, key=lambda kc: len(kc[1]))
                notes.append(f"Registros localizados bajo la clave '{k}'.")
                return c
            if all(isinstance(v, list) and len(v) == len(next(iter(o.values()))) for v in o.values()):
                return [dict(zip(o.keys(), vals)) for vals in zip(*o.values())]
            return [o]
        return None

    recs = find_records(obj)
    if not recs:
        raise ValueError("No se encontraron registros tabulares en el JSON.")
    df = pd.json_normalize(recs, sep=".")
    if any("." in c for c in df.columns):
        notes.append("Se aplanaron estructuras anidadas (clave.subclave).")
    df = df.astype(object).map(_cell)
    return df.reset_index(drop=True)


def load_bytes(data: bytes, filename: str) -> tuple[pd.DataFrame, list[str]]:
    """Carga cualquier archivo soportado. Devuelve (DataFrame de texto crudo, notas de ingesta)."""
    notes: list[str] = []
    ext = Path(filename).suffix.lower()
    head = data[:2000].lstrip()
    if ext in (".xlsx", ".xlsm", ".xls") or data[:2] == b"PK":
        df = _read_excel(data, notes)
        notes.insert(0, "Formato: Excel.")
    elif ext in (".json", ".jsonl", ".ndjson") or head[:1] in (b"{", b"["):
        df = _read_json(data, notes)
        notes.insert(0, "Formato: JSON.")
    else:
        df = _read_csv(data, notes)
        notes.insert(0, "Formato: texto delimitado (CSV/TSV/TXT).")
    if len(df) > MAX_ROWS:
        df = df.iloc[:MAX_ROWS]
    return df, notes


def load_path(path: str | Path) -> tuple[pd.DataFrame, list[str]]:
    p = Path(path)
    return load_bytes(p.read_bytes(), p.name)
