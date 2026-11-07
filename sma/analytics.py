# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Cómputo determinista de hechos (facts) sobre el dataset limpio.

Es la 'caja de herramientas' del Agente 2 (Analista): produce estadísticos exactos que luego el agente
selecciona, ordena e interpreta. Todo número que aparezca en un informe debe poder rastrearse a este objeto.
"""
from __future__ import annotations

import calendar
import itertools
import math
from collections import Counter

import numpy as np
import pandas as pd

from .profiler import _name_has
from .text_utils import STOPWORDS, intent_of, sentiment, themes_of, tokens

ADDITIVE_HINTS = ("total", "venta", "ventas", "ingreso", "ingresos", "monto", "importe", "valor", "cantidad", "unidades", "costo", "costos", "gasto",
                  "produccion", "volumen", "poblacion", "casos", "pedidos", "toneladas", "kg", "litros", "horas")
MEASURE_PRIORITY = ("total", "venta", "ventas", "ingreso", "ingresos", "monto", "importe", "valor", "costo", "gasto", "produccion", "volumen", "casos", "cantidad", "unidades")
RATE_HINTS = ("tasa", "porcentaje", "pct", "indice", "promedio", "media", "ratio", "dias", "tiempo", "edad", "nota", "puntaje", "precio", "unitario", "score", "calificacion", "temperatura")
DIM_HINTS = ("sucursal", "region", "ciudad", "municipio", "departamento", "categoria", "producto", "area", "tipo", "canal", "estado", "medio",
             "segmento", "linea", "zona", "sede", "programa", "facultad", "cliente", "vendedor", "proveedor", "turno", "planta", "maquina", "motivo", "genero", "sexo")


def r2(x, d=2):
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return round(x, d)


def _first(xs):
    return xs[0] if xs else None


def pick_measure(num_cols: list[str], df: pd.DataFrame | None = None) -> str | None:
    if not num_cols:
        return None
    if df is not None and not any(_name_has(c, MEASURE_PRIORITY, exact=True) for c in num_cols):
        # nombres genéricos (p. ej. columna_7): se prefiere la variable de mayor magnitud acumulada
        return max(num_cols, key=lambda c: abs(float(df[c].sum())))

    def score(c):
        toks = c.split("_")
        s = 0
        for i, h in enumerate(MEASURE_PRIORITY):
            if h in toks or h in c:
                s = max(s, 100 - i)
        if _name_has(c, RATE_HINTS):
            s -= 30
        return s

    return max(num_cols, key=lambda c: score(c))


def natural_agg(col: str) -> str:
    toks = col.split("_")
    if any(h in toks for h in RATE_HINTS):
        return "media"
    if any(h in toks or h in col for h in ADDITIVE_HINTS):
        return "suma"
    return "media"


def pick_dims(df: pd.DataFrame, schema: list[dict], limit: int = 4) -> list[str]:
    cands = []
    for c in schema:
        if c["tipo"] == "categorico" and c["rol"] in ("dimension",):
            nu = df[c["normalizado"]].nunique(dropna=True)
            if 2 <= nu <= 60 and c["pct_nulos"] < 60:
                toks = c["normalizado"].split("_")
                hint = next((i for i, hnt in enumerate(DIM_HINTS) if hnt in toks), 99 if not _name_has(c["normalizado"], DIM_HINTS) else 50)
                cands.append((hint, nu if nu > 2 else 99, c["normalizado"]))
    cands.sort()
    return [c[2] for c in cands[:limit]]


def _group(df, measure, dim, agg):
    g = df.groupby(dim, dropna=True)[measure].agg(["sum", "mean", "count"]).reset_index()
    g = g[g["count"] > 0]
    return g


def _interaction(df, measure, dim) -> dict | None:
    sub = df[[measure, dim]].dropna()
    if len(sub) < 10:
        return None
    agg = natural_agg(measure)
    g = _group(sub, measure, dim, agg)
    if len(g) < 2:
        return None
    key = "sum" if agg == "suma" else "mean"
    g = g.sort_values(key, ascending=False)
    total = float(g["sum"].sum())
    grupos = []
    for _, row in g.head(8).iterrows():
        d = {"categoria": str(row[dim]), "suma": r2(row["sum"]), "media": r2(row["mean"]), "n": int(row["count"])}
        if agg == "suma" and total:
            d["pct_total"] = r2(100 * row["sum"] / total)
        grupos.append(d)
    best, worst = g.iloc[0], g.iloc[-1]
    gm = float(sub[measure].mean())
    brecha = r2(100 * (best["mean"] - worst["mean"]) / abs(worst["mean"])) if worst["mean"] else None
    sst = float(((sub[measure] - gm) ** 2).sum())
    ssb = float((g["count"] * (g["mean"] - gm) ** 2).sum())
    eta2 = r2(ssb / sst, 3) if sst > 0 else 0.0
    cum = g[key].cumsum() / g[key].sum() if g[key].sum() else None
    pareto = None
    if agg == "suma" and cum is not None and len(g) >= 10:  # con menos categorías el 20% superior es una sola y duplica al líder
        k = max(1, int(math.ceil(0.2 * len(g))))
        pareto = r2(100 * float(g[key].head(k).sum() / g[key].sum()))
    return {
        "ref": f"inter:{measure}|{dim}", "medida": measure, "dimension": dim, "agregacion": agg, "n_categorias": int(len(g)),
        "grupos": grupos, "mejor": {"categoria": str(best[dim]), "media": r2(best["mean"]), "suma": r2(best["sum"])},
        "peor": {"categoria": str(worst[dim]), "media": r2(worst["mean"]), "suma": r2(worst["sum"])},
        "brecha_media_pct": brecha, "eta2": eta2, "pareto_top20_pct": pareto, "media_general": r2(gm),
    }


def _cramers_v(a: pd.Series, b: pd.Series) -> float | None:
    ct = pd.crosstab(a, b)
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return None
    obs = ct.values.astype(float)
    n = obs.sum()
    if n < 30:
        return None
    exp = np.outer(obs.sum(1), obs.sum(0)) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum((obs - exp) ** 2 / exp)
    k = min(ct.shape) - 1
    return float(math.sqrt(chi2 / (n * k))) if k > 0 else None


def _time_block(df, fcol, measure) -> dict | None:
    s = df[fcol].dropna()
    if len(s) < 5:
        return None
    dmin, dmax = s.min(), s.max()
    days = int((dmax - dmin).days)
    gran = "mes" if days > 120 else "semana" if days > 21 else "dia"
    if gran == "mes":
        key = df[fcol].dt.to_period("M").astype(str)
    elif gran == "semana":
        key = df[fcol].dt.to_period("W").astype(str).str[:10]
    else:
        key = df[fcol].dt.strftime("%Y-%m-%d")
    tmp = pd.DataFrame({"periodo": key})
    if measure:
        tmp[measure] = df[measure]
        g = tmp.dropna(subset=["periodo"]).groupby("periodo")[measure].agg(["sum", "mean", "count"]).reset_index()
    else:
        g = tmp.dropna(subset=["periodo"]).groupby("periodo").size().rename("count").reset_index()
        g["sum"] = g["count"].astype(float)
        g["mean"] = g["count"].astype(float)
    g = g.sort_values("periodo")
    agg = natural_agg(measure) if measure else "suma"
    val = "sum" if agg == "suma" else "mean"
    serie = [{"periodo": r.periodo, "n": int(r["count"]), "suma": r2(r["sum"]), "media": r2(r["mean"])} for _, r in g.iterrows()]
    n_medio = r2(float(g["count"].mean()), 1)
    parcial = False
    if gran == "mes" and dmax.day < calendar.monthrange(dmax.year, dmax.month)[1] - 3:
        parcial = True
    eff = g.iloc[:-1] if (parcial and len(g) > 2) else g
    var = None
    if len(eff) >= 2 and eff[val].iloc[-2] not in (0, np.nan):
        prev = float(eff[val].iloc[-2])
        var = r2(100 * (float(eff[val].iloc[-1]) - prev) / abs(prev)) if prev else None
    slope_pct = r2_ = None
    if len(eff) >= 4:
        y = eff[val].astype(float).values
        x = np.arange(len(y))
        b, a = np.polyfit(x, y, 1)
        pred = a + b * x
        ss_res = float(((y - pred) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2_ = r2(1 - ss_res / ss_tot, 3) if ss_tot > 0 else 0.0
        slope_pct = r2(100 * b / y.mean()) if y.mean() else None
    confiable = bool(len(eff) >= 2 and int(eff["count"].iloc[-1]) >= 20 and int(eff["count"].iloc[-2]) >= 20)
    best = eff.loc[eff[val].idxmax()] if len(eff) else None
    worst = eff.loc[eff[val].idxmin()] if len(eff) else None
    dow = None
    if days > 14:
        dows = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        d = df[fcol].dropna().dt.dayofweek.value_counts()
        if len(d):
            dow = {"dia": dows[int(d.index[0])], "pct": r2(100 * d.iloc[0] / d.sum())}
    return {
        "ref": f"tiempo:{fcol}", "columna": fcol, "desde": dmin.strftime("%Y-%m-%d"), "hasta": dmax.strftime("%Y-%m-%d"), "dias": days,
        "granularidad": gran, "n_periodos": int(len(g)), "n_medio_por_periodo": n_medio, "variacion_confiable": confiable, "medida": measure, "agregacion": agg, "serie": serie[-36:],
        "ultimo_periodo_parcial": parcial, "variacion_ultimo_vs_previo_pct": var, "tendencia_pct_por_periodo": slope_pct, "r2_tendencia": r2_,
        "mejor_periodo": {"periodo": best["periodo"], "valor": r2(best[val])} if best is not None else None,
        "peor_periodo": {"periodo": worst["periodo"], "valor": r2(worst[val])} if worst is not None else None,
        "dia_semana_top": dow,
    }


def _text_block(df, tcol, dims) -> tuple[dict | None, list[dict]]:
    s = df[tcol].dropna().astype(str)
    if len(s) < 5:
        return None, []
    sample = s if len(s) <= 20000 else s.sample(20000, random_state=1)
    sent = sample.map(sentiment)
    cnt = Counter(sent.tolist())
    n = len(sample)
    words = Counter(w for t in sample for w in tokens(t) if len(w) > 3 and w not in STOPWORDS and not w.isdigit())
    th = Counter(t for txt in sample for t in themes_of(txt))
    it = Counter(intent_of(txt) for txt in sample)
    neg_examples = [x[:140] for x in sample[sent == -1].head(3).tolist()]
    block = {
        "ref": f"texto:{tcol}", "columna": tcol, "n": int(len(s)), "n_analizados": int(n), "long_media": r2(s.str.len().mean(), 1),
        "palabras_top": [{"palabra": w, "n": c} for w, c in words.most_common(10)],
        "sentimiento": {"positivo": cnt.get(1, 0), "negativo": cnt.get(-1, 0), "neutro": cnt.get(0, 0),
                        "pct_positivo": r2(100 * cnt.get(1, 0) / n), "pct_negativo": r2(100 * cnt.get(-1, 0) / n), "pct_neutro": r2(100 * cnt.get(0, 0) / n)},
        "temas": [{"tema": t, "n": c, "pct": r2(100 * c / n)} for t, c in th.most_common(5)],
        "intenciones": [{"intencion": t, "n": c, "pct": r2(100 * c / n)} for t, c in it.most_common(5)],
        "ejemplos_negativos": neg_examples,
    }
    cross = []
    for d in dims[:3]:
        tmp = pd.DataFrame({"s": df[tcol].map(lambda x: sentiment(x) if isinstance(x, str) else np.nan), "d": df[d]}).dropna()
        if len(tmp) < 30:
            continue
        g = tmp.groupby("d")["s"].agg(n="count", neg=lambda x: float((x == -1).mean() * 100)).reset_index()
        g = g[g["n"] >= 10].sort_values("neg", ascending=False)
        if len(g) < 2:
            continue
        cross.append({"ref": f"textodim:{tcol}|{d}", "texto": tcol, "dimension": d,
                      "grupos": [{"categoria": str(r.d), "n": int(r.n), "pct_negativo": r2(r.neg)} for r in g.head(6).itertuples()],
                      "peor": {"categoria": str(g.iloc[0]["d"]), "pct_negativo": r2(g.iloc[0]["neg"])},
                      "mejor": {"categoria": str(g.iloc[-1]["d"]), "pct_negativo": r2(g.iloc[-1]["neg"])}})
    return block, cross


def compute_facts(df: pd.DataFrame, schema: list[dict], quality: dict, log: dict) -> dict:
    by_role: dict[str, list[str]] = {"medidas": [], "dimensiones": [], "fechas": [], "textos": [], "identificadores": [], "indicadores": []}
    for c in schema:
        r = {"medida": "medidas", "dimension": "dimensiones", "fecha": "fechas", "texto": "textos", "identificador": "identificadores", "indicador": "indicadores"}.get(c["rol"])
        if r:
            by_role[r].append(c["normalizado"])
    measures = [c for c in by_role["medidas"] if pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().sum() >= 5]
    measure = pick_measure(measures, df)
    dims = pick_dims(df, schema)
    fcol = _first(sorted(by_role["fechas"], key=lambda c: -df[c].notna().sum()))
    tcol = _first(sorted(by_role["textos"], key=lambda c: -df[c].notna().sum()))

    facts: dict = {
        "resumen": {"filas": int(len(df)), "columnas": int(df.shape[1]), "filas_originales": log["filas_originales"], "duplicados_eliminados": log["duplicados_eliminados"]},
        "roles": by_role, "medida_principal": measure, "dimension_principal": _first(dims), "dimensiones_analizadas": dims,
        "fecha_principal": fcol, "texto_principal": tcol,
        "calidad": {"puntaje": quality["puntaje"], "veredicto": quality["veredicto"], "pct_nulos_promedio": quality["pct_nulos_promedio"], "n_problemas": len(log["issues"])},
    }
    num = []
    for c in measures:
        s = df[c].dropna().astype(float)
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        out = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum()) if iqr > 0 else 0
        mean = float(s.mean())
        num.append({
            "ref": f"num:{c}", "columna": c, "n": int(len(s)), "nulos_pct": r2(100 * (1 - len(s) / len(df))), "suma": r2(s.sum()), "media": r2(mean),
            "mediana": r2(s.median()), "desv": r2(s.std()), "min": r2(s.min()), "max": r2(s.max()), "p25": r2(q1), "p75": r2(q3), "p95": r2(s.quantile(0.95)),
            "cv": r2(float(s.std() / mean)) if mean else None, "asimetria": r2(s.skew(), 2) if len(s) > 2 else None, "outliers": out, "outliers_pct": r2(100 * out / len(s)),
            "agregacion_natural": natural_agg(c),
        })
    facts["numericas"] = num
    cat = []
    for c in by_role["dimensiones"] + by_role["indicadores"]:
        s = df[c].dropna()
        if s.empty:
            continue
        vc = s.astype(str).value_counts()
        top = [{"valor": str(k), "n": int(v), "pct": r2(100 * v / len(s))} for k, v in vc.head(10).items()]
        cat.append({"ref": f"cat:{c}", "columna": c, "n": int(len(s)), "n_unicos": int(vc.size), "nulos_pct": r2(100 * (1 - len(s) / len(df))), "top": top,
                    "top3_pct": r2(sum(t["pct"] for t in top[:3])), "moda": top[0]["valor"]})
    facts["categoricas"] = cat
    facts["tiempo"] = [t for t in [_time_block(df, f, measure) for f in by_role["fechas"][:2]] if t]
    inter = []
    for m in ([measure] if measure else []) + [x["columna"] for x in sorted(num, key=lambda z: -(z["cv"] or 0)) if x["columna"] != measure][:2]:
        for d in dims[:3]:
            it = _interaction(df, m, d)
            if it:
                inter.append(it)
    facts["interacciones"] = inter
    # indicadores binarios (Sí/No, verdadero/falso): tasa del estado positivo por dimensión (p. ej. renuncia, aprobación, reincidencia)
    ind_blocks = []
    for c in by_role["indicadores"]:
        s = df[c]
        if s.dropna().nunique() != 2:
            continue
        flag = s.map(lambda v: np.nan if v is None or (isinstance(v, float) and np.isnan(v)) else float(bool(v)))
        for d in dims[:3]:
            tmp = pd.DataFrame({"x": flag, "d": df[d]}).dropna()
            if len(tmp) < 30:
                continue
            g = tmp.groupby("d")["x"].agg(["mean", "count"]).reset_index()
            g = g[g["count"] >= 10].sort_values("mean", ascending=False)
            if len(g) < 2:
                continue
            ind_blocks.append({"ref": f"ind:{c}|{d}", "indicador": c, "dimension": d, "tasa_global_pct": r2(100 * float(tmp["x"].mean())),
                               "grupos": [{"categoria": str(r.d), "pct": r2(100 * r.mean), "n": int(r.count)} for r in g.head(6).itertuples()],
                               "mejor": {"categoria": str(g.iloc[0]["d"]), "pct": r2(100 * g.iloc[0]["mean"])}, "peor": {"categoria": str(g.iloc[-1]["d"]), "pct": r2(100 * g.iloc[-1]["mean"])}})
    facts["indicadores"] = ind_blocks
    # asociaciones categoría×categoría
    asoc = []
    for a, b in itertools.combinations(dims[:4], 2):
        sub = df[[a, b]].dropna()
        v = _cramers_v(sub[a], sub[b]) if len(sub) else None
        if v is not None and v >= 0.15:
            ct = pd.crosstab(sub[a], sub[b]).stack().sort_values(ascending=False)
            (ka, kb), nn = ct.index[0], int(ct.iloc[0])
            asoc.append({"ref": f"asoc:{a}|{b}", "a": a, "b": b, "cramers_v": r2(v, 3), "celda_top": {"a": str(ka), "b": str(kb), "n": nn, "pct": r2(100 * nn / len(sub))}})
    facts["asociaciones_cat"] = sorted(asoc, key=lambda x: -x["cramers_v"])[:4]
    # correlaciones y relaciones aritméticas
    corr, rel = [], []
    ncols = [x["columna"] for x in num][:10]
    if len(ncols) >= 2:
        cm = df[ncols].astype(float).corr()
        for a, b in itertools.combinations(ncols, 2):
            r = cm.loc[a, b]
            if not np.isnan(r) and abs(r) >= 0.3 and df[[a, b]].dropna().shape[0] >= 20:
                corr.append({"ref": f"corr:{a}|{b}", "a": a, "b": b, "r": r2(r, 3), "n": int(df[[a, b]].dropna().shape[0])})
        corr = sorted(corr, key=lambda x: -abs(x["r"]))[:5]
        for c in ncols[:8]:
            for a, b in itertools.combinations([x for x in ncols[:8] if x != c], 2):
                sub = df[[a, b, c]].dropna()
                sub = sub[sub[c].abs() > 0]
                if len(sub) < 20:
                    continue
                prod = sub[a] * sub[b]
                cov = float(((prod - sub[c]).abs() / sub[c].abs() < 0.02).mean() * 100)
                if cov >= 80:
                    rel.append({"ref": f"rel:{c}={a}*{b}", "expr": f"{c} ≈ {a} × {b}", "cobertura_pct": r2(cov)})
                    continue
                for d in [x for x in ncols[:8] if x not in (a, b, c)]:
                    dd = df.loc[sub.index, d]
                    if dd.notna().mean() < 0.9 or not dd.between(0, 100).all():
                        continue
                    f = (1 - dd / (100 if dd.max() > 1 else 1)) if dd.notna().all() else None
                    if f is None:
                        continue
                    cov2 = float((((prod * f) - sub[c]).abs() / sub[c].abs() < 0.02).mean() * 100)
                    if cov2 >= 80:
                        rel.append({"ref": f"rel:{c}={a}*{b}*(1-{d})", "expr": f"{c} ≈ {a} × {b} × (1 − {d})", "cobertura_pct": r2(cov2)})
                        break
    facts["correlaciones"] = corr
    facts["relaciones_aritmeticas"] = rel[:3]
    # texto
    textos, textodim = [], []
    for t in by_role["textos"][:2]:
        tb, cross = _text_block(df, t, dims)
        if tb:
            textos.append(tb)
            textodim += cross
    facts["texto"] = textos
    facts["texto_x_dimension"] = textodim
    # anomalías
    anom = []
    if measure:
        s = df[measure].dropna()
        if len(s) > 20:
            z = (s - s.mean()) / (s.std() or 1)
            idcol = _first(by_role["identificadores"])
            for idx in z.abs().sort_values(ascending=False).head(3).index:
                if abs(z[idx]) >= 3:
                    anom.append({"ref": f"anom:{measure}:{int(idx)}", "tipo": "valor_atipico", "columna": measure, "valor": r2(s[idx]), "z": r2(z[idx]),
                                 "id": str(df.loc[idx, idcol]) if idcol else f"fila {int(idx) + 2}"})
    for t in facts["tiempo"][:1]:
        vals = [p["suma"] if t["agregacion"] == "suma" else p["media"] for p in t["serie"] if p["suma"] is not None]
        if len(vals) >= 6:
            arr = np.array(vals, dtype=float)
            z = (arr - arr.mean()) / (arr.std() or 1)
            for i in np.argsort(-np.abs(z))[:1]:
                if abs(z[i]) >= 2:
                    anom.append({"ref": f"anom:periodo:{t['serie'][-len(vals):][i]['periodo']}", "tipo": "pico_o_caida_periodo", "columna": t["columna"], "valor": r2(arr[i]), "z": r2(z[i]), "id": t["serie"][-len(vals):][i]["periodo"]})
    facts["anomalias"] = anom
    refs = ["calidad"] + [x["ref"] for k in ("numericas", "categoricas", "tiempo", "interacciones", "indicadores", "asociaciones_cat", "correlaciones", "relaciones_aritmeticas", "texto", "texto_x_dimension", "anomalias") for x in facts[k]]
    facts["refs"] = refs
    return facts


def collect_numbers(obj, out: set | None = None) -> set:
    """Todos los números presentes en facts (lista blanca para el guardrail anti-alucinación)."""
    if out is None:
        out = set()
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        if not (isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj))):
            out.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            collect_numbers(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            collect_numbers(v, out)
    elif isinstance(obj, str):
        import re
        for m in re.findall(r"\d{4}-\d{2}(?:-\d{2})?", obj):
            for p in m.split("-"):
                out.add(float(p))
    return out
