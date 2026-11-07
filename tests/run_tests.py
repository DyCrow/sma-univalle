"""FASE 4 · Testeo, control de calidad y resiliencia.

Ejecuta el protocolo empírico completo y genera la Matriz de Auditoría (docs/matriz_auditoria.md):
  Prueba A (cuantitativa/comercial) · Prueba B (cualitativa/PQR) · Prueba de Resiliencia (ruido)
  + datasets adicionales (JSON anidado, Excel, base sorpresa sin encabezado, muestra diminuta)
  + pruebas del Agente 5 (consejero) en 6 sectores/roles distintos
  + sondas de alucinación con un LLM simulado (valida los guardrails)
  + prueba de generalidad: mismo código y mismos prompts para todos los datasets.

Uso:  py tests/run_tests.py [--con-llm]
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import make_datasets as md  # noqa: E402
from sma.guardrails import validate  # noqa: E402
from sma.llm import NullLLM, ScriptedLLM, llm_from_env  # noqa: E402
from sma.pipeline import MultiAgentSystem  # noqa: E402
from sma.prompts import SCHEMAS, catalog_hash  # noqa: E402
from sma.report import render_directive, render_html  # noqa: E402
from sma.text_utils import sentiment  # noqa: E402

DATA, DOCS = ROOT / "data", ROOT / "docs"
RESULTS: list[dict] = []


def check(cid, dataset, agente, esperado, cond, detalle=""):
    RESULTS.append({"id": cid, "dataset": dataset, "agente": agente, "esperado": esperado, "ok": bool(cond), "detalle": str(detalle)[:300]})
    print(f"  [{'PASS' if cond else 'FAIL'}] {cid} · {agente}: {esperado}" + ("" if cond else f"  → {detalle}"))
    return bool(cond)


def code_hash() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / "sma").glob("*.py")):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def unverified(run) -> list:
    return [x for t in run.trace for x in t["cifras_no_verificadas"]]


def inter(run, medida, dim):
    return next((i for i in run.facts["interacciones"] if i["medida"] == medida and i["dimension"] == dim), None)


def schema_of(run):
    return {c["normalizado"]: c for c in run.schema}


def main():
    use_llm = "--con-llm" in sys.argv
    llm = llm_from_env() if use_llm else NullLLM()
    sysm = MultiAgentSystem(llm)
    truth = json.loads((DATA / "verdad_de_terreno.json").read_text(encoding="utf-8"))
    md.main()  # regenera datasets (mismos datos: semilla fija)
    truth = json.loads((DATA / "verdad_de_terreno.json").read_text(encoding="utf-8"))
    h_prompts0, h_code0 = catalog_hash(), code_hash()
    print(f"Motor: {llm.name} | huella prompts {h_prompts0} | huella código {h_code0}")

    files = {"A": "A_ventas_transaccionales.csv", "B": "B_pqr_texto_libre.csv", "C": "C_ruido_nulos_formatos_mixtos.csv", "D": "D_produccion_anidado.json",
             "E": "E_indicadores_sociales.xlsx", "F": "F_base_sorpresa_hospital.csv", "G": "G_muestra_diminuta.csv", "H": "H_recursos_humanos.csv", "I": "I_encuesta_una_columna.csv"}
    runs, times = {}, {}
    for k, fn in files.items():
        t0 = time.time()
        runs[k] = sysm.analyze_path(DATA / fn)
        times[k] = time.time() - t0
    print(f"{len(runs)} datasets procesados en {sum(times.values()):.1f} s\n")

    # ================================================================ PRUEBA A
    print("PRUEBA A · Cuantitativa / comercial")
    r = runs["A"]; sch = schema_of(r); t = truth["A"]
    gt, _ = md.gen_ventas()
    cl = r.clean.set_index("id_transaccion")
    ok_dates = bool((cl["fecha"].dt.strftime("%Y-%m-%d") == gt.set_index("id_transaccion")["fecha"].dt.strftime("%Y-%m-%d")).all())
    check("A-01", "A", "Agente 1 (Limpiador)", "Fechas en 2 formatos (ISO y DD/MM/AAAA) estandarizadas a AAAA-MM-DD, idénticas a la verdad de terreno en el 100% de las filas",
          sch["fecha"]["tipo"] == "fecha" and sch["fecha"]["n_formatos"] == 2 and ok_dates, f"tipo={sch['fecha']['tipo']} formatos={sch['fecha'].get('formatos')} identicas={ok_dates}")
    check("A-02", "A", "Agente 1 (Limpiador)", "Suma de 'total' idéntica a la verdad de terreno", abs(r.clean["total"].sum() - t["total_ventas"]) < 1, f"{r.clean['total'].sum()} vs {t['total_ventas']}")
    i_s, i_c = inter(r, "total", "sucursal"), inter(r, "total", "categoria")
    check("A-03", "A", "Agente 2 (Analista)", "Identifica la sucursal y la categoría líderes en ventas", bool(i_s and i_c and i_s["grupos"][0]["categoria"] == t["top_sucursal"] and i_c["grupos"][0]["categoria"] == t["top_categoria"]),
          f"{i_s and i_s['grupos'][0]['categoria']} / {i_c and i_c['grupos'][0]['categoria']} vs {t['top_sucursal']} / {t['top_categoria']}")
    found_ids = {a["id"] for a in r.facts["anomalias"]}
    check("A-04", "A", "Agente 2 (Analista)", "Detecta las 3 transacciones atípicas plantadas (x40)", set(t["ids_top3_totales"]) <= found_ids, f"detectadas={found_ids}")
    tm = r.facts["tiempo"][0]
    check("A-05", "A", "Agente 2 (Analista)", f"Mes pico de ventas = {t['mes_pico']}", tm["mejor_periodo"]["periodo"] == t["mes_pico"], tm["mejor_periodo"])
    check("A-06", "A", "Agente 2 (Analista)", "Descubre la relación aritmética total ≈ cantidad × precio × (1 − descuento) sin conocerla de antemano", any("total" in x["expr"] and "cantidad" in x["expr"] and "precio_unitario" in x["expr"] for x in r.facts["relaciones_aritmeticas"]), r.facts["relaciones_aritmeticas"])
    a2 = r.outputs["analista"]
    check("A-07", "A", "Agente 2 (Analista)", "Máximo 5 categorías con frecuencia numérica explícita (n y %)", len(a2["analisis_cualitativo"]["top_categorias"]) <= 5 and all("n" in c and "pct" in c for c in a2["analisis_cualitativo"]["top_categorias"]))
    check("A-08", "A", "Agente 3 (Intérprete)", "Dominio comercial inferido y 0 cifras no verificadas en toda la cadena", "comercial" in r.outputs["interprete"]["dominio_inferido"]["dominio"] and not unverified(r), f"{r.outputs['interprete']['dominio_inferido']} {unverified(r)}")
    a4 = r.outputs["informe"]; svgs = [render_directive(v, r) for v in a4["visualizaciones"]]
    check("A-09", "A", "Agente 4 (Informe)", "Resumen ≤120 palabras, ≥4 gráficos renderizados y sin marcas de cifra no verificada",
          len(a4["resumen_ejecutivo"].split()) <= 120 and sum(1 for s in svgs if s) >= 4 and "[cifra no verificada]" not in render_html(r), f"palabras={len(a4['resumen_ejecutivo'].split())} graficos={sum(1 for s in svgs if s)}")
    hz_a = r.outputs["interprete"]["hallazgos"]
    check("A-11", "A", "Agente 2 (Analista)", "La primera dimensión analizada es de gestión (sucursal), no el método de pago", r.facts["dimension_principal"] == "sucursal", r.facts["dimensiones_analizadas"])
    check("A-12", "A", "Agente 3 (Intérprete)", "Sin redundancias: con <10 categorías no repite el '20% superior' como segunda cifra de concentración", not any("20% superior" in h["hallazgo"] for h in hz_a), [h["hallazgo"][:80] for h in hz_a if "20% superior" in h["hallazgo"]])
    rec = [x["accion"] for x in a4["recomendaciones"]]
    check("A-10", "A", "Agente 4 (Informe)", "Recomendaciones priorizadas, sin duplicados", len(rec) >= 2 and len(set(rec)) == len(rec), rec)

    # ================================================================ PRUEBA B
    print("\nPRUEBA B · Cualitativa / PQR / texto libre")
    r = runs["B"]; sch = schema_of(r); t = truth["B"]
    labels = json.loads((DATA / "B_etiquetas_reales.json").read_text())
    raw = pd.read_csv(DATA / files["B"])
    pred = ["neg" if sentiment(x) == -1 else "pos" if sentiment(x) == 1 else "neu" for x in raw["descripcion"]]
    acc = float(np.mean(np.array(pred) == np.array(labels)))
    check("B-01", "B", "Agente 1 (Limpiador)", "Variantes de escritura (queja/QUEJA/'Queja '/Quejá…) unificadas en 4 tipos de solicitud", r.clean["tipo_solicitud"].nunique() == 4, f"{r.clean['tipo_solicitud'].nunique()} → {sorted(r.clean['tipo_solicitud'].dropna().unique())}")
    check("B-02", "B", "Agente 1 (Limpiador)", "Detecta 'descripcion' como texto libre y 'dias_respuesta' como medida con nulos reportados como N/A (sin imputar)", sch["descripcion"]["tipo"] == "texto_libre" and sch["dias_respuesta"]["rol"] == "medida" and r.clean["dias_respuesta"].isna().sum() > 0)
    check("B-03", "B", "Agente 2 (Analista)", "Exactitud del sentimiento ≥ 85% frente a las etiquetas reales", acc >= 0.85, f"exactitud={acc:.3f}")
    pn = r.facts["texto"][0]["sentimiento"]["pct_negativo"]
    check("B-04", "B", "Agente 2 (Analista)", "% de mensajes negativos dentro de ±8 puntos de la realidad", abs(pn - t["pct_negativo_real"]) <= 8, f"{pn} vs {t['pct_negativo_real']:.1f}")
    a2 = r.outputs["analista"]
    check("B-05", "B", "Agente 2 (Analista)", "Salida cualitativa concisa: ≤5 categorías y ≤5 temas con frecuencia numérica", len(a2["analisis_cualitativo"]["top_categorias"]) <= 5 and len(a2["analisis_cualitativo"]["temas"]) <= 5 and all(isinstance(x["n"], (int, float)) for x in a2["analisis_cualitativo"]["temas"]))
    cx = next((c for c in r.facts["texto_x_dimension"] if c["dimension"] == "area_responsable"), None)
    check("B-06", "B", "Agente 3 (Intérprete)", f"Área con más insatisfacción = {t['area_mas_negativa']}", bool(cx and cx["peor"]["categoria"] == t["area_mas_negativa"]), cx and cx["peor"])
    ia = inter(r, "dias_respuesta", "area_responsable")
    check("B-07", "B", "Agente 3 (Intérprete)", f"Área más lenta en responder = {t['area_mas_lenta']}", bool(ia and ia["mejor"]["categoria"] == t["area_mas_lenta"]), ia and ia["mejor"])
    check("B-08", "B", "Agente 3 (Intérprete)", "Dominio PQR inferido y 0 cifras no verificadas", "PQR" in r.outputs["interprete"]["dominio_inferido"]["dominio"] and not unverified(r), r.outputs["interprete"]["dominio_inferido"]["dominio"])
    check("B-09", "B", "Agente 4 (Informe)", "Gráficos de sentimiento y temas generados", any(v["agregacion"] == "sentimiento" for v in r.outputs["informe"]["visualizaciones"]) and any(v["agregacion"] == "temas" for v in r.outputs["informe"]["visualizaciones"]))

    # ================================================================ RESILIENCIA (C)
    print("\nPRUEBA DE RESILIENCIA · Dataset con ruido (hasta 30% de nulos)")
    r = runs["C"]; sch = schema_of(r); t = truth["C"]
    sa = schema_of(runs["A"])
    diffs = {c: abs(sch[c]["pct_nulos"] - p) for c, p in t["nulos_inyectados_pct"].items() if c in sch}
    check("C-01", "C", "Agente 1 (Auditor)", "% de nulos reportado por columna dentro de ±1,5 puntos del inyectado (incluye marcadores N/A, -, ?, 'sin dato', NULL)", max(diffs.values()) <= 1.5, {k: round(v, 2) for k, v in diffs.items() if v > 1.5} or f"máx desvío {max(diffs.values()):.2f}")
    sin_nombre = [c for c in sch if c.startswith("columna_sin_nombre")]
    check("C-02", "C", "Agente 1 (Auditor)", "Columnas sin nombre ('', 'Unnamed: 12') nombradas sin perder datos", len(sin_nombre) == t["columnas_sin_nombre"], sin_nombre)
    check("C-03", "C", "Agente 1 (Limpiador)", "60 duplicados exactos detectados y eliminados", r.clean_log["duplicados_eliminados"] == t["duplicados_inyectados"], r.clean_log["duplicados_eliminados"])
    check("C-04", "C", "Agente 1 (Limpiador)", "4 formatos de fecha mixtos (incl. '5 de marzo de 2024') unificados con ≥99% de parseo", sch["fecha"]["tipo"] == "fecha" and sch["fecha"]["n_formatos"] == 4 and sch["fecha"]["tasa_parseo"] >= 0.99, f"{sch['fecha'].get('formatos')} parseo={sch['fecha'].get('tasa_parseo')}")
    check("C-05", "C", "Agente 1 (Limpiador)", "Importes con '$', miles con punto y ',00' normalizados: suma idéntica a la original", sch["total"]["tipo"] == "numerico" and abs(r.clean["total"].sum() - t["total_suma_original"]) / t["total_suma_original"] < 1e-6, f"{r.clean['total'].sum()} vs {t['total_suma_original']}")
    check("C-06", "C", "Agente 1 (Limpiador)", "Variantes 'NORTE'/'norte ' unificadas: sucursal ≤ 5 categorías", r.clean["sucursal"].nunique() <= 5, r.clean["sucursal"].nunique())
    issues = {i["tipo"] for i in r.clean_log["issues"]}
    check("C-07", "C", "Agente 1 (Auditor)", "Reporta negativos incoherentes, nulos ocultos, formato mixto, duplicados y columnas sin nombre", {"negativos_incoherentes", "nulos_ocultos", "formato_mixto", "duplicados", "columna_sin_nombre"} <= issues, sorted(issues))
    check("C-08", "C", "Agente 1 (Auditor)", "Puntaje de calidad bajo (<75) y menor que el de la base limpia (A)", r.facts["calidad"]["puntaje"] < 75 and r.facts["calidad"]["puntaje"] < runs["A"].facts["calidad"]["puntaje"], f"C={r.facts['calidad']['puntaje']} A={runs['A'].facts['calidad']['puntaje']}")
    al = {a["columna"]: a["pct_nulos"] for a in r.outputs["interprete"]["alertas_datos_faltantes"]}
    esperadas = {c for c, p in t["nulos_inyectados_pct"].items() if p >= 5 and c in sch}
    check("C-09", "C", "Agente 3 (Intérprete)", "Alerta de datos faltantes por cada columna con ≥5% de nulos, sin imputar valores", esperadas <= set(al), sorted(esperadas - set(al)))
    nulls_after = int(r.clean["cantidad"].isna().sum()); expected_null = round(t["nulos_inyectados_pct"]["cantidad"] * 3000 / 100)
    check("C-10", "C", "Agente 3 (Intérprete)", "Nulos no imputados: los nulos de 'cantidad' siguen siendo nulos (≈ inyectados)", abs(nulls_after - expected_null) <= 45, f"{nulls_after} vs ≈{expected_null}")
    check("C-11", "C", "Agente 3 (Intérprete)", "0 alucinaciones de cifras en el informe de la base ruidosa", not unverified(r), unverified(r))
    check("C-12", "C", "Agente 4 (Informe)", "El informe declara explícitamente la baja calidad y las limitaciones", "Calidad de datos y limitaciones" in [s["titulo"] for s in r.outputs["informe"]["secciones"]] and any("Calidad" in x for x in r.outputs["analista"]["limitaciones"]), r.outputs["analista"]["limitaciones"])

    # ================================================================ D · JSON anidado
    print("\nDATASET D · JSON anidado (producción)")
    r = runs["D"]; sch = schema_of(r)
    check("D-01", "D", "Agente 1 (Limpiador)", "Aplana el JSON anidado y ubica los registros bajo 'registros' (1500 filas, columnas orden_planta, operario_nombre…)", len(r.clean) == 1500 and {"orden_planta", "operario_nombre", "orden_id"} <= set(sch), sorted(sch))
    check("D-02", "D", "Agente 1 (Auditor)", "'operario_antiguedad_anios' es una MEDIDA (duración), no una dimensión de calendario", sch["operario_antiguedad_anios"]["rol"] == "medida", sch["operario_antiguedad_anios"]["rol"])
    idd = inter(r, "unidades_defectuosas", "maquina")
    check("D-03", "D", "Agente 2 (Analista)", "Identifica la máquina con más unidades defectuosas (M-03)", bool(idd and idd["grupos"][0]["categoria"] == truth["D"]["maquina_mas_defectos"]), idd and idd["grupos"][0])
    h = " ".join(x["hallazgo"] for x in r.outputs["interprete"]["hallazgos"])
    check("D-04", "D", "Agente 3 (Intérprete)", "Dominio 'producción' inferido sin que ningún prompt lo mencione; sin '[cifra no verificada]' en los hallazgos", "producción" in r.outputs["interprete"]["dominio_inferido"]["dominio"] and "[cifra no verificada]" not in h, r.outputs["interprete"]["dominio_inferido"]["dominio"])

    # ================================================================ E · Excel
    print("\nDATASET E · Excel con fila de título y 2 hojas")
    r = runs["E"]; sch = schema_of(r)
    pm = r.facts["numericas"] and next((n for n in r.facts["numericas"] if n["columna"].startswith("pobreza")), None)
    check("E-01", "E", "Agente 1 (Limpiador)", "Omite la fila de título, elige la hoja principal y lee 48 filas × 8 columnas", r.clean.shape == (48, 8) and "municipio" in sch, r.clean.shape)
    check("E-02", "E", "Agente 1 (Limpiador)", "Porcentajes con coma decimal y signo % ('12,5%') convertidos a número (pobreza media entre 10 y 60)", bool(pm) and 10 < pm["media"] < 60, pm and pm["media"])
    check("E-03", "E", "Agente 3 (Intérprete)", "Dominio social/territorial inferido", "social" in r.outputs["interprete"]["dominio_inferido"]["dominio"], r.outputs["interprete"]["dominio_inferido"]["dominio"])
    check("E-04", "E", "Agente 1 (Auditor)", "'ano' tratado como dimensión de periodo (código numérico), no como medida", sch["ano"]["rol"] == "dimension", sch["ano"]["rol"])

    # ================================================================ F · base sorpresa
    print("\nDATASET F · Base sorpresa (sin encabezado, latin-1, ';', coma decimal)")
    r = runs["F"]; sch = schema_of(r)
    check("F-01", "F", "Agente 1 (Limpiador)", "Detecta ausencia de encabezado, codificación cp1252 y delimitador ';'", "columna_1" in sch and any("cp1252" in n for n in r.ingest_notes) and any("punto y coma" in n for n in r.ingest_notes), r.ingest_notes)
    tipos = [c["tipo"] for c in r.schema]
    check("F-02", "F", "Agente 1 (Auditor)", "Infiere ≥1 fecha, ≥3 numéricas y ≥3 categóricas sin nombres de columna", tipos.count("fecha") >= 1 and tipos.count("numerico") >= 3 and tipos.count("categorico") >= 3, tipos)
    check("F-03", "F", "Agente 2 (Analista)", "Elige como medida principal la variable de costo (mayor magnitud acumulada), no la edad", r.facts["medida_principal"] == "columna_8", r.facts["medida_principal"])
    check("F-04", "F", "Agente 3 (Intérprete)", "Infiere dominio salud/hospitalario SOLO a partir de los valores de las categorías", "salud" in r.outputs["interprete"]["dominio_inferido"]["dominio"], r.outputs["interprete"]["dominio_inferido"])
    check("F-05", "F", "Agente 4 (Informe)", "Declara la limitación de nombres de columna no informativos", any("no son informativos" in x for x in r.outputs["analista"]["limitaciones"]), r.outputs["analista"]["limitaciones"])

    # ================================================================ G · muestra diminuta
    print("\nDATASET G · Muestra diminuta (12 filas)")
    r = runs["G"]; sch = schema_of(r)
    check("G-01", "G", "Agente 1 (Auditor)", "'region' con valores N/S se trata como categoría (no como booleano)", sch["region"]["tipo"] == "categorico", sch["region"]["tipo"])
    check("G-02", "G", "Agente 3 (Intérprete)", "Advierte explícitamente el tamaño de muestra pequeño", any("Muestra pequeña" in a or "pequeña" in a for a in r.outputs["auditor"]["advertencias"] + [h["hallazgo"] for h in r.outputs["interprete"]["hallazgos"]]) and any("filas" in x and "no concluyentes" in x for x in r.outputs["analista"]["limitaciones"]), r.outputs["analista"]["limitaciones"])

    # ================================================================ K · bases inéditas (HR y una sola columna)
    print("\nDATASETS H e I · bases inéditas añadidas tras una exploración 'sorpresa' (HR latin-1 y archivo de una sola columna)")
    r = runs["H"]; sch = schema_of(r)
    check("K-01", "H", "Agente 1 (Limpiador)", "RR. HH. (latin-1, ';', encabezados con tildes y '¿?', '$ 3.200.000', fechas DD/MM/AAAA): esquema correcto y salario medio coherente (2,5-4 millones)",
          sch["renuncio"]["tipo"] == "booleano" and sch["fecha_de_ingreso"]["tipo"] == "fecha" and sch["salario_mensual"]["tipo"] == "numerico" and 2.5e6 < r.clean["salario_mensual"].mean() < 4e6, [(k, v["tipo"]) for k, v in sch.items()])
    check("K-02", "H", "Agente 3 (Intérprete)", "Dominio 'recursos humanos' inferido y hallazgo de la tasa de renuncia por cargo con Soporte como el más alto", "recursos humanos" in r.outputs["interprete"]["dominio_inferido"]["dominio"] and any(i["indicador"] == "renuncio" and i["dimension"] == "cargo" and i["mejor"]["categoria"] == "Soporte" for i in r.facts["indicadores"]), r.facts.get("indicadores", [])[:1])
    din = [x for x in r.outputs["interprete"]["hallazgos"] if x["titulo"].startswith("Dinámica temporal")]
    check("K-03", "H", "Agente 3 (Intérprete)", "Una serie por fecha de ingreso con ~9 registros/periodo se marca como NO concluyente (impacto bajo), no como hallazgo de alto impacto", all("no concluyente" in x["titulo"] and x["impacto"] == "bajo" for x in din), [(x["titulo"], x["impacto"]) for x in din])
    r = runs["I"]; sch = schema_of(r)
    raw_i = pd.read_csv(DATA / files["I"])
    lab_i = json.loads((DATA / "I_etiquetas_reales.json").read_text())
    acc_i = float(np.mean([("neg" if sentiment(x) == -1 else "pos" if sentiment(x) == 1 else "neu") == y for x, y in zip(raw_i["comentario"], lab_i)]))
    check("K-04", "I", "Agente 1 (Limpiador)", "Archivo de UNA columna con comas internas: no inventa delimitador y conserva los 80 comentarios (comentarios idénticos no son duplicados sin identificador)", r.clean.shape == (80, 1) and sch["comentario"]["tipo"] == "texto_libre" and r.clean_log["duplicados_eliminados"] == 0, (r.clean.shape, [c["tipo"] for c in r.schema], r.clean_log["duplicados_eliminados"]))
    check("K-05", "I", "Agente 2 (Analista)", "Sentimiento del archivo de una columna con exactitud ≥ 85%", acc_i >= 0.85 and bool(r.facts["texto"]), f"exactitud={acc_i:.3f}")

    # ================================================================ H · Consejero estratégico
    print("\nAGENTE 5 · Consejero estratégico (6 sectores/roles + casos límite)")
    A, B_, C_, D_, E_, F_ = (runs[k] for k in "ABCDEF")
    adv = lambda run, msg, rol="": sysm.advise(run, msg, rol, history=[])  # noqa: E731
    m1 = adv(A, "Voy a subir los precios 25% en todas las sucursales porque seguro nadie lo va a notar, es urgente para este trimestre.", "CFO")
    sg = m1["_meta"]["senales"]
    check("H-01", "H", "Agente 5 (Consejero)", "CFO + subir precios 25%: modo decisión, lente finanzas, ≥3 sesgos, magnitud contrastada con la variación real, ≥3 cuestionamientos y NO responde 'proceder'",
          sg["clasificacion"]["modo"] == "decision" and sg["lente"] == "finanzas" and len(m1["sesgos_detectados"]) >= 3 and any("veces la variación típica" in c["por_que_importa"] or "veces la variación" in " ".join(m1["evidencia_en_contra"] + m1["evidencia_a_favor"]) for c in m1["cuestionamientos"]) and len(m1["cuestionamientos"]) >= 3 and m1["recomendacion"]["postura"] != "proceder",
          {"modo": sg["clasificacion"]["modo"], "lente": sg["lente"], "sesgos": [s["sesgo"] for s in m1["sesgos_detectados"]], "postura": m1["recomendacion"]["postura"]})
    check("H-02", "H", "Agente 5 (Consejero)", "Propone alternativa tipo prueba A/B para una decisión de precios", any("A/B" in a["opcion"] for a in m1["alternativas"]), [a["opcion"] for a in m1["alternativas"]])
    m2 = adv(A, "Voy a cerrar la sucursal Occidente porque vende poco.", "Gerente comercial")
    check("H-03", "H", "Agente 5 (Consejero)", "Cerrar 'Occidente': enlaza la entidad con los datos, marca irreversibilidad y no recomienda 'proceder'", "sucursal=Occidente" in m2["_meta"]["entidades"] and any("reversib" in c["por_que_importa"] for c in m2["cuestionamientos"]) and m2["recomendacion"]["postura"] in ("pilotar primero", "reconsiderar", "evidencia insuficiente"),
          {"entidades": m2["_meta"]["entidades"], "postura": m2["recomendacion"]["postura"]})
    m2b = adv(A, "Voy a cerrar la sucursal Centro, vende poco.", "Gerente comercial")
    check("H-04", "H", "Agente 5 (Consejero)", "No complaciente: ante cerrar 'Centro' (30% de las ventas) muestra la evidencia en contra con su porcentaje", any("Centro" in x and "%" in x for x in m2b["evidencia_en_contra"]) and m2b["recomendacion"]["postura"] not in ("proceder", "proceder con condiciones"), {"contra": m2b["evidencia_en_contra"][:2], "postura": m2b["recomendacion"]["postura"]})
    m3 = adv(B_, "Soy el director de servicio al ciudadano. Quiero contratar 10 agentes más para Logística.")
    check("H-05", "H", "Agente 5 (Consejero)", "Sector PQR: rol detectado en el texto, lente servicio, entidad 'Logística' enlazada y preguntas de vuelta al administrador", m3["_meta"]["senales"]["lente"] == "servicio" and "area_responsable=Logística" in m3["_meta"]["entidades"] and len(m3["preguntas_para_el_administrador"]) >= 2 and m3["_meta"]["senales"]["rol_declarado"],
          {"lente": m3["_meta"]["senales"]["lente"], "ent": m3["_meta"]["entidades"], "rol": m3["_meta"]["senales"]["rol_etiqueta"]})
    m4 = adv(E_, "Como secretario de planeación voy a priorizar la inversión en Cali porque tiene más población.")
    check("H-06", "H", "Agente 5 (Consejero)", "Sector público: lente 'publico', entidad Cali enlazada, stakeholders de gobierno (ciudadanía/órganos de control)", m4["_meta"]["senales"]["lente"] == "publico" and "municipio=Cali" in m4["_meta"]["entidades"] and any("Ciudadan" in s for s in m4["plan_liderazgo"]["stakeholders"]), {"lente": m4["_meta"]["senales"]["lente"], "ent": m4["_meta"]["entidades"]})
    m5 = adv(F_, "Estoy seguro de que reducir la estancia a 3 días es obvio y no tiene riesgos, un médico me dijo que funciona.", "Director médico")
    check("H-07", "H", "Agente 5 (Consejero)", "Salud con datos sin encabezado: detecta exceso de certeza, optimismo y evidencia anecdótica; lente salud", {"Exceso de certeza", "Evidencia anecdótica / disponibilidad"} <= {s["sesgo"] for s in m5["sesgos_detectados"]} and m5["_meta"]["senales"]["lente"] == "salud", [s["sesgo"] for s in m5["sesgos_detectados"]])
    m6 = adv(D_, "¿Qué máquina tiene más defectos?", "Jefe de planta")
    check("H-08", "H", "Agente 5 (Consejero)", "Pregunta abierta sobre producción: la respuesta directa nombra la máquina con más unidades defectuosas (M-03)", m6["modo"] == "pregunta" and "M-03" in m6["respuesta_directa"], m6["respuesta_directa"][:200])
    m7 = adv(A, "¿Cuál es la sucursal que más vende?", "Gerente")
    check("H-09", "H", "Agente 5 (Consejero)", "Pregunta comercial: responde con la sucursal líder y además cuestiona la presuposición/calidad", m7["modo"] == "pregunta" and truth["A"]["top_sucursal"] in m7["respuesta_directa"] and len(m7["cuestionamientos"]) >= 1, m7["respuesta_directa"][:200])
    m8 = adv(A, "")
    check("H-10", "H", "Agente 5 (Consejero)", "Sin mensaje: modo exploración, propone decisiones sugeridas por los datos y las cuestiona", m8["modo"] == "exploracion" and len(m8["cuestionamientos"]) >= 1 and "Estas son las decisiones" in m8["respuesta_directa"], m8["respuesta_directa"][:160])
    hist = [{"rol": "usuario", "texto": "Voy a cerrar la sucursal Occidente porque vende poco."}, {"rol": "asesor", "texto": "…"}]
    m9 = sysm.advise(A, "El margen de esa sucursal es de 5%.", "Gerente comercial", history=hist)
    check("H-11", "H", "Agente 5 (Consejero)", "Seguimiento conversacional: recuerda la decisión previa (Occidente) al recibir un dato nuevo", m9["_meta"]["senales"]["clasificacion"]["modo"] == "decision" and "sucursal=Occidente" in m9["_meta"]["entidades"], m9["_meta"])
    mr1 = adv(A, "Voy a reducir el presupuesto de Occidente.", "Director financiero")
    mr2 = adv(A, "Voy a reducir el presupuesto de Occidente.", "Jefe de gestión humana")
    check("H-12", "H", "Agente 5 (Consejero)", "Adaptabilidad al rol: misma decisión, distinto lente, stakeholders y comunicación según el rol", mr1["plan_liderazgo"]["stakeholders"] != mr2["plan_liderazgo"]["stakeholders"] and mr1["lectura_del_rol"] != mr2["lectura_del_rol"] and mr1["_meta"]["senales"]["lente"] != mr2["_meta"]["senales"]["lente"], (mr1["_meta"]["senales"]["lente"], mr2["_meta"]["senales"]["lente"]))
    m10 = adv(C_, "Voy a invertir en inventario de Electrónica en Norte.", "Gerente de operaciones")
    check("H-13", "H", "Agente 5 (Consejero)", "Sobre datos ruidosos: advierte la baja calidad de los datos como cuestionamiento de alta severidad", any("confiables" in c["supuesto"] and c["severidad"] == "alta" for c in m10["cuestionamientos"]), [c["supuesto"] for c in m10["cuestionamientos"]][:4])
    H_ = runs["H"]
    m11 = adv(H_, "Soy la directora de talento humano y voy a congelar los aumentos salariales en Soporte porque seguro el problema es el clima, un jefe me dijo que están desmotivados.")
    check("H-15", "H", "Agente 5 (Consejero)", "Base RR. HH. inédita: detecta el rol en el texto (lente talento), enlaza 'Soporte', marca ≥2 sesgos, confronta la tasa de renuncia de Soporte con la general y NO responde 'proceder' (antes lo hacía)",
          m11["_meta"]["senales"]["lente"] == "talento" and "cargo=Soporte" in m11["_meta"]["entidades"] and len(m11["sesgos_detectados"]) >= 2 and any("renuncio" in c["supuesto"] for c in m11["cuestionamientos"]) and m11["recomendacion"]["postura"] not in ("proceder",),
          {"lente": m11["_meta"]["senales"]["lente"], "ent": m11["_meta"]["entidades"], "postura": m11["recomendacion"]["postura"], "sesgos": [s["sesgo"] for s in m11["sesgos_detectados"]], "cuest": [c["supuesto"][:60] for c in m11["cuestionamientos"]]})
    m12 = adv(H_, "¿En qué cargo hay más ausentismo?")
    check("H-16", "H", "Agente 5 (Consejero)", "Pregunta sobre una base inédita: responde con la agrupación pedida (ausentismo por cargo)", m12["modo"] == "pregunta" and "ausentismo" in m12["respuesta_directa"] and "cargo" in m12["respuesta_directa"], m12["respuesta_directa"][:160])
    memos = [m1, m2, m2b, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12]
    bad_schema = [validate(SCHEMAS["estratega"], {k: v for k, v in m.items() if k != "_meta"}) for m in memos]
    check("H-14", "H", "Agente 5 (Consejero)", "Las 13 salidas del consejero cumplen el esquema JSON estricto y contienen 0 cifras no verificadas", not any(bad_schema) and not any(m["_meta"]["cifras_no_verificadas"] for m in memos), [b for b in bad_schema if b][:2] or [m["_meta"]["cifras_no_verificadas"] for m in memos if m["_meta"]["cifras_no_verificadas"]])

    # ================================================================ L · Agente 6 · Simulador de crisis
    print("\nAGENTE 6 · Simulador de Crisis y Evaluación Directiva")
    for cid, ag, esp, ok, det in test_simulator(sysm, runs):
        check(cid, "Agente 6", ag, esp, ok, det)

    # ================================================================ I · sondas de alucinación
    print("\nSONDAS DE ALUCINACIÓN · LLM simulado (valida los guardrails)")
    probe_results = probe_guardrails(files)
    for cid, ag, esp, ok, det in probe_results:
        check(cid, "Sonda", ag, esp, ok, det)

    # ================================================================ J · generalidad
    print("\nGENERALIDAD Y ADAPTABILIDAD")
    h_prompts1, h_code1 = catalog_hash(), code_hash()
    check("J-01", "Todos", "Arquitectura", "9 datasets de estructuras y dominios distintos procesados SIN modificar código ni prompts (huellas idénticas antes/después)", h_prompts0 == h_prompts1 and h_code0 == h_code1 and len(runs) == 9, f"{h_prompts0}/{h_prompts1} {h_code0}/{h_code1}")
    doms = {k: runs[k].outputs["interprete"]["dominio_inferido"]["dominio"] for k in runs}
    check("J-02", "Todos", "Agente 3 (Intérprete)", "Dominios inferidos distintos para ≥6 de los 9 datasets (no hay un dominio cableado)", len(set(doms.values())) >= 6, doms)
    check("J-03", "Todos", "Orquestador", "Cada dataset se procesa en <20 s", max(times.values()) < 20, {k: round(v, 1) for k, v in times.items()})
    from sma.cleaner import build_schema  # noqa: F401  (el sistema debe tolerar archivos vacíos/ilegibles con un error claro)
    try:
        sysm.analyze_bytes(b"", "vacio.csv")
        ok_empty = False
    except ValueError as e:
        ok_empty = "filas" in str(e)
    check("J-05", "Todos", "Ingesta", "Un archivo vacío produce un error claro en español (no una traza)", ok_empty)
    allp = [p.read_text(encoding="utf-8").lower() for p in [ROOT / "sma" / "prompts.py"]][0]
    check("J-04", "Todos", "Prompts", "Ningún prompt menciona columnas ni dominios concretos de los datasets de prueba", not any(w in allp for w in ("sucursal", "dias_respuesta", "radicado", "unidades_producidas", "pobreza")), "")

    write_matrix(runs, times)
    fails = [x for x in RESULTS if not x["ok"]]
    print(f"\nRESUMEN: {len(RESULTS) - len(fails)}/{len(RESULTS)} verificaciones aprobadas" + (f" · FALLAN: {[f['id'] for f in fails]}" if fails else ""))
    return 1 if fails else 0


# =============================================================================== Agente 6
def _best(sim):
    out = {}
    for q in sim.preguntas:
        k = q["clave"]
        out[q["id"]] = k["mejor"] if q["formato"] == "opcion_multiple" else k["respuesta"] if q["formato"] == "verdadero_falso" else k["correcto"] if q["formato"] == "emparejamiento" else k["huecos"]
    return out


def _worst(sim):
    out = {}
    for q in sim.preguntas:
        k, c = q["clave"], q["contenido"]
        if q["formato"] == "opcion_multiple":
            out[q["id"]] = min(k["puntajes"], key=k["puntajes"].get)
        elif q["formato"] == "verdadero_falso":
            out[q["id"]] = not k["respuesta"]
        elif q["formato"] == "emparejamiento":
            sols = [s["id"] for s in c["soluciones"]]
            out[q["id"]] = {cid: next(s for s in sols if s != sid) for cid, sid in k["correcto"].items()}
        else:
            out[q["id"]] = {h["id"]: next(o["id"] for o in h["opciones"] if o["id"] != k["huecos"][h["id"]]) for h in c["huecos"]}
    return out


def test_simulator(sysm, runs):
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer

    from sma import simulator as simu
    from sma import web
    from sma.strategist import NIVELES

    R = []
    A = runs["A"]
    sims = {rol: sysm.simulate_start(A, rol, "auto", "mixta", 8, seed=11) for rol in NIVELES}
    ok1, det1 = True, {}
    for rol, s in sims.items():
        fm = {q["formato"] for q in s.preguntas}
        mcs = [q for q in s.preguntas if q["formato"] == "opcion_multiple"]
        one_best = all(len(q["contenido"]["opciones"]) == 4 and sorted(o["id"] for o in q["contenido"]["opciones"]) == list("ABCD") and sum(1 for v in q["clave"]["puntajes"].values() if v == 1.0) == 1 for q in mcs)
        pub = json.dumps(simu.public_view(s), ensure_ascii=False)
        no_leak = not any(w in pub for w in ('"clave"', '"puntajes"', '"explicaciones"', '"correcto"', '"respuesta"', '"mejor"'))
        good = fm == set(simu.FORMATOS) and one_best and no_leak and len(s.preguntas) == 8
        ok1 &= good
        det1[rol] = (sorted(fm), one_best, no_leak, len(s.preguntas))
    R.append(("L-01", "Agente 6", "Para cada rol (Auxiliar, Asistente, Supervisor, Gerente) genera 8 preguntas con los 4 formatos; opción múltiple con A-D y una sola mejor respuesta; la vista pública NO filtra la clave", ok1, det1))
    sc = {}
    for rol, s in sims.items():
        sc[rol] = (sysm.simulate_grade(A, s, _best(s))["puntaje_pct"], sysm.simulate_grade(A, s, _worst(s))["puntaje_pct"], sysm.simulate_grade(A, s, {})["puntaje_pct"])
    R.append(("L-02", "Agente 6", "Calificación aritmética: mejores respuestas = 100%, peores ≤ 25%, sin responder = 0% (4 roles)", all(b == 100.0 and w <= 25 and e == 0.0 for b, w, e in sc.values()), sc))
    ctx = simu.build_ctx(A, "quiebra", "Auxiliar")
    sit = simu._situaciones(ctx)[0]
    rng = __import__("random").Random(5)
    best_txt = {}
    for rol in NIVELES:
        q = simu._mc(ctx, sit, rol, rng)
        best_txt[rol] = next(o["texto"] for o in q["contenido"]["opciones"] if o["id"] == q["clave"]["mejor"])
    ger_best_for_aux = None
    qa = simu._mc(ctx, sit, "Auxiliar", rng)
    for o in qa["contenido"]["opciones"]:
        if o["texto"] == best_txt["Gerente"]:
            ger_best_for_aux = qa["clave"]["puntajes"][o["id"]]
    R.append(("L-03", "Agente 6", "Calibración por rol: la mejor respuesta a la MISMA situación es distinta en los 4 roles y la ideal del Gerente puntúa 0 para un Auxiliar (excede su autoridad)", len(set(best_txt.values())) == 4 and ger_best_for_aux == 0.0, {"mejor_por_rol": {k: v[:50] for k, v in best_txt.items()}, "gerente_para_aux": ger_best_for_aux}))
    esc_exp = {"A": "quiebra", "B": "operativa"}
    ok4, det4 = True, {}
    for k, run in runs.items():
        s = sysm.simulate_start(run, "Supervisor", "auto", "mixta", 8, seed=2)
        tr = next(t for t in reversed(run.trace) if "Agente 6 · Simulador" in t["etapa"])
        good = len(s.preguntas) >= 6 and all(simu.valid_question(q) for q in s.preguntas) and not tr["cifras_no_verificadas"] and not tr["correcciones_guardrail"] and bool(s.contexto["datos_clave"])
        if k in esc_exp:
            good &= s.escenario == esc_exp[k]
        ok4 &= good
        det4[k] = (s.escenario, len(s.preguntas), tr["cifras_no_verificadas"], tr["correcciones_guardrail"][:1])
    R.append(("L-04", "Agente 6", "Adaptativo: genera una simulación válida y sin cifras inventadas para los 9 datasets (el escenario automático elige 'quiebra' para ventas en caída y 'operativa' para PQR con 62% de mensajes negativos)", ok4, det4))
    ok5 = True
    for fmt in simu.FORMATOS:
        s = sysm.simulate_start(A, "Gerente", "inopia", fmt, 6, seed=4)
        ok5 &= len(s.preguntas) >= 3 and all(q["formato"] == fmt for q in s.preguntas) and s.escenario == "inopia"
    R.append(("L-05", "Agente 6", "La dinámica elegida (un solo formato) se respeta; el escenario elegido (inopia) también", ok5, ""))
    rb, rw = sysm.simulate_grade(A, sims["Gerente"], _best(sims["Gerente"])), sysm.simulate_grade(A, sims["Auxiliar"], _worst(sims["Auxiliar"]))
    campos = {"puntaje_pct", "exito_decisiones_pct", "nivel_desempeno", "diagnostico_rol", "competencias", "recomendaciones", "revision", "preparacion_para_el_rol", "decisiones_optimas"}
    R.append(("L-06", "Agente 6", "Reporte Final: puntaje 0-100, % de éxito de decisiones, diagnóstico por rol, competencias, recomendaciones y revisión pregunta por pregunta; coherente con el desempeño (best→Sobresaliente, worst→Requiere refuerzo con ≥2 recomendaciones)",
              campos <= set(rb) and rb["nivel_desempeno"] == "Sobresaliente" and rb["exito_decisiones_pct"] == 100.0 and "Gerente" in rb["diagnostico_rol"] and rw["nivel_desempeno"] == "Requiere refuerzo" and len(rw["recomendaciones"]) >= 2 and "Auxiliar" in rw["diagnostico_rol"] and len(rw["revision"]) == 8,
              {"best": (rb["puntaje_pct"], rb["nivel_desempeno"]), "worst": (rw["puntaje_pct"], rw["nivel_desempeno"], len(rw["recomendaciones"]))}))
    # sonda con LLM simulado que entrega preguntas defectuosas y cifras inventadas
    def bad_llm(system, user):
        if "Diseñador de Simulaciones" not in system:
            raise RuntimeError("no")
        mc3 = {"id": "x1", "formato": "opcion_multiple", "competencia": "Gestión del riesgo", "tipo_eval": "decision", "enunciado": "Solo 3 opciones", "contenido": {"opciones": [{"id": "A", "texto": "a"}, {"id": "B", "texto": "b"}, {"id": "C", "texto": "c"}]}, "clave": {"mejor": "A", "puntajes": {"A": 1, "B": 0, "C": 0}}, "explicacion": "x"}
        mc_bad = {"id": "x2", "formato": "opcion_multiple", "competencia": "Competencia inventada", "tipo_eval": "decision", "enunciado": "Competencia inválida", "contenido": {"opciones": [{"id": i, "texto": i} for i in "ABCD"]}, "clave": {"mejor": "A", "puntajes": {"A": 1, "B": 0, "C": 0, "D": 0}}, "explicacion": "x"}
        vf = {"id": "x3", "formato": "verdadero_falso", "competencia": "Diagnóstico con datos", "tipo_eval": "conocimiento", "enunciado": "VF", "contenido": {"afirmacion": "La dirección es siempre la responsable."}, "clave": {"respuesta": False}, "explicacion": "x"}
        return json.dumps({"contexto": {"titulo": "Crisis", "narrativa": "Las ventas cayeron 87,5% el último mes y perdimos 12.345.678 pesos.", "datos_clave": ["d"], "supuestos": ["s"]}, "preguntas": [mc3, mc_bad, vf]}, ensure_ascii=False)
    s_llm = MultiAgentSystem(ScriptedLLM(bad_llm))
    run_b = runs["B"]
    sim = s_llm.simulate_start(run_b, "Supervisor", "operativa", "mixta", 6, seed=1)
    tr = next(t for t in reversed(run_b.trace) if "Agente 6 · Simulador" in t["etapa"])
    R.append(("L-07", "Agente 6", "LLM defectuoso: descarta preguntas con 3 opciones o competencia inventada, conserva la válida, completa con preguntas de respaldo hasta 6 y enmascara las cifras inventadas del contexto",
              tr["motor"] == "llm" and len(sim.preguntas) == 6 and all(simu.valid_question(q) for q in sim.preguntas) and "87,5" not in sim.contexto["narrativa"] and "12.345.678" not in sim.contexto["narrativa"] and "[cifra no verificada]" in sim.contexto["narrativa"] and sum(1 for c in tr["correcciones_guardrail"] if "descartada" in c) == 2,
              {"motor": tr["motor"], "n": len(sim.preguntas), "corr": tr["correcciones_guardrail"][:3], "nv": tr["cifras_no_verificadas"]}))
    # servidor real: ciclo completo por HTTP
    web.SYSTEM = MultiAgentSystem(NullLLM())
    srv = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{port}"

    def call(path, body=None):
        req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), method="POST" if body is not None else "GET", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
    try:
        st0, page = call("/")
        st1, cfg = call("/api/simulador/config")
        st2, d = call("/api/demo?archivo=H_recursos_humanos.csv", {})
        rid = json.loads(d)["id"]
        st3, ini = call("/api/simulador/iniciar", {"id": rid, "rol": "Gerente", "escenario": "auto", "dinamica": "mixta", "n": 8})
        pub = json.loads(ini)
        st4, rep = call("/api/simulador/evaluar", {"sim_id": pub["sim_id"], "respuestas": {}})
        rep = json.loads(rep)
        st5, _ = call("/api/simulador/iniciar", {"id": rid, "rol": "Presidente"})
        st6, _ = call("/api/simulador/evaluar", {"sim_id": "no-existe", "respuestas": {}})
        txt = page.decode("utf-8")
        ui = all(s in txt for s in ("Instrucciones de Uso del Simulador", "Selecciona tu Rol", "Iniciar Simulación de Crisis", 'name="rol"', "sim-esc", "wm-in", "@media print", "DOCUMENTO CONFIDENCIAL"))
        ok8 = (st0, st1, st2, st3, st4) == (200,) * 5 and ui and len(pub["preguntas"]) == 8 and rep["puntaje_pct"] == 0.0 and rep["sin_responder"] == 8 and st5 == 400 and st6 == 400 and len(json.loads(cfg)["roles"]) == 4
        det8 = {"estados": [st0, st1, st2, st3, st4, st5, st6], "ui": ui}
    except Exception as e:  # noqa: BLE001
        ok8, det8 = False, repr(e)
    finally:
        srv.shutdown()
    R.append(("L-08", "Agente 6", "Servidor HTTP real: la página incluye instrucciones, selector de rol y escenario; ciclo iniciar→evaluar funciona; rol inválido y simulación inexistente devuelven 400", ok8, det8))
    import re as _re
    js = _re.search(r"<script>(.*)</script>", web.PAGE, _re.S).group(1)
    R.append(("L-09", "Agente 6", "Interfaz: el contador de respondidas tiene id propio (no pisa otros textos) y cada formato tiene control interactivo (radio, desplegable, completar inline)",
              'id="sim-count"' in js and "#sim-play .hint'" not in js and "type=\"radio\"" in js and "select class=\"sel-in\" data-c" in js and "select class=\"sel-in inline\" data-h" in js, ""))
    qs = simu._match_bank(simu.build_ctx(runs["A"], "inopia", "Gerente"), __import__("random").Random(1))
    texto = " ".join(c["texto"] for q in qs for c in q["contenido"]["causas"])
    R.append(("L-10", "Agente 6", "Coherencia con los datos: con calidad alta (95/100) ninguna pregunta plantea 'datos con vacíos' como causa de la crisis", "Datos con vacíos" not in texto and runs["A"].facts["calidad"]["puntaje"] >= 85, texto[:120]))
    return R


# =============================================================================== sondas
def probe_guardrails(files):
    """LLM simulado que miente a propósito. Verifica que el sistema lo detecta y corrige."""
    from sma import offline
    out = []
    state = {"calls": 0}
    path = DATA / files["B"]

    def agent_of(system):
        return "auditor" if "Auditor de Calidad" in system else "analista" if "Analista Experto" in system else "interprete" if "Consultor de Negocio" in system else "informe" if "Redactor Ejecutivo" in system else "estratega"

    def payload_of(user):
        return json.loads(user.split("PAYLOAD (JSON):\n", 1)[1])

    # I-01 reintento por JSON inválido
    def r1(system, user):
        state["calls"] += 1
        if agent_of(system) != "analista":
            raise RuntimeError("sin red")
        if state["calls"] % 2 == 1:
            return "Claro, aquí tienes el análisis: {resumen: sin comillas"
        return json.dumps(offline.offline_analista(payload_of(user)), ensure_ascii=False)
    llm1 = ScriptedLLM(r1)
    run = MultiAgentSystem(llm1).analyze_path(path)
    tr = next(t for t in run.trace if "Agente 2" in t["etapa"])
    out.append(("I-01", "Agente 2", "JSON inválido del LLM → reintento con retroalimentación del error y éxito en el 2.º intento", tr["motor"] == "llm" and tr["intentos"] == 2 and tr["problemas_validacion"], tr))
    t1 = next(t for t in run.trace if "Agente 1" in t["etapa"])
    out.append(("I-02", "Orquestador", "LLM caído (excepción) → respaldo determinista; la cadena completa termina", t1["motor"] == "llm→respaldo determinista" and "informe" in run.outputs, t1["motor"]))

    # I-03/I-04 alucinaciones del analista, intérprete e informe
    def r3(system, user):
        ag = agent_of(system)
        p = payload_of(user)
        if ag == "analista":
            o = offline.offline_analista(p)
            o["resumen_cuantitativo"][0]["media"] = 999.99          # cifra inventada
            o["resumen_cuantitativo"].append({"columna": "ingresos_fantasma", "n": 10, "media": 1, "mediana": 1, "min": 0, "max": 2, "suma": 10, "desv": 1})
            o["interacciones"].append({"ref": "inter:inventada|x", "medida": "x", "dimension": "y", "hallazgo": "Dato falso"})
            o["analisis_cualitativo"]["top_categorias"] = (o["analisis_cualitativo"]["top_categorias"] * 3)[:9] or [{"variable": "v", "valor": str(i), "n": i, "pct": i} for i in range(9)]
            return json.dumps(o, ensure_ascii=False)
        if ag == "interprete":
            o = offline.offline_interprete(p)
            o["hallazgos"][0]["hallazgo"] += " Además las quejas crecieron 87,5% el último mes y ahorran 12.345.678 pesos."
            o["hallazgos"].append({"id": "HX", "titulo": "Hallazgo sin evidencia", "hallazgo": "Los clientes prefieren la marca Z.", "evidencia": ["ref:inexistente"], "impacto": "alto", "tipo": "oportunidad", "accion_sugerida": "Invertir"})
            o["alertas_datos_faltantes"] = []
            return json.dumps(o, ensure_ascii=False)
        if ag == "informe":
            o = offline.offline_informe(p)
            o["visualizaciones"].append({"id": "vx", "tipo": "barras", "titulo": "Fantasma", "columna_x": "columna_que_no_existe", "columna_y": None, "agregacion": "conteo", "top": 5, "motivo": "x"})
            o["visualizaciones"].append({"id": "vy", "tipo": "radar", "titulo": "Tipo no permitido", "columna_x": None, "columna_y": None, "agregacion": "conteo", "top": 5, "motivo": "x"})
            o["resumen_ejecutivo"] = " ".join(["palabra"] * 200)
            return json.dumps(o, ensure_ascii=False)
        raise RuntimeError("no")
    run = MultiAgentSystem(ScriptedLLM(r3)).analyze_path(path)
    t2 = next(t for t in run.trace if "Agente 2" in t["etapa"])
    t3 = next(t for t in run.trace if "Agente 3" in t["etapa"])
    t4 = next(t for t in run.trace if "Agente 4" in t["etapa"])
    nums = {n["columna"]: n for n in run.facts["numericas"]}
    fixed = run.outputs["analista"]["resumen_cuantitativo"]
    out.append(("I-03", "Agente 2", "Estadístico inventado (media=999,99), variable fantasma y 'ref' inexistente → corregidos con el valor medido o descartados",
                all(x["columna"] in nums for x in fixed) and fixed[0]["media"] == nums[fixed[0]["columna"]]["media"] and all(i["ref"] in set(run.facts["refs"]) for i in run.outputs["analista"]["interacciones"]) and len(t2["correcciones_guardrail"]) >= 3
                and len(run.outputs["analista"]["analisis_cualitativo"]["top_categorias"]) <= 5, t2["correcciones_guardrail"][:3]))
    hall = " ".join(h["hallazgo"] for h in run.outputs["interprete"]["hallazgos"])
    out.append(("I-04", "Agente 3", "Cifras inventadas (87,5%; 12.345.678) enmascaradas como '[cifra no verificada]'; hallazgo sin evidencia descartado",
                "87,5" not in hall and "12.345.678" not in hall and "[cifra no verificada]" in hall and all(h["id"] != "HX" for h in run.outputs["interprete"]["hallazgos"]), t3["cifras_no_verificadas"]))
    out.append(("I-05", "Agente 3", "Alertas de datos faltantes omitidas por el LLM → restituidas por el guardrail", any("Alerta de nulos añadida" in c for c in t3["correcciones_guardrail"]) or not any(c.get("pct_nulos", 0) >= 5 for c in run.schema), t3["correcciones_guardrail"][:2]))
    ids = {v["id"] for v in run.outputs["informe"]["visualizaciones"]}
    out.append(("I-06", "Agente 4", "Gráficos con columna inexistente o tipo no permitido descartados; resumen de 200 palabras recortado a ≤120",
                "vx" not in ids and "vy" not in ids and len(run.outputs["informe"]["resumen_ejecutivo"].split()) <= 120, t4["correcciones_guardrail"]))

    # I-07 el LLM propone un tipo incorrecto en el esquema
    def r7(system, user):
        if agent_of(system) == "auditor":
            o = offline.offline_auditor(payload_of(user))
            for m in o["mapeo_columnas"]:
                if m["normalizado"] == "canal":
                    m["tipo"] = "numerico"
                    m["rol"] = "medida"
                if m["normalizado"] == "dias_respuesta":
                    m["pct_nulos"] = 0.0
            o["mapeo_columnas"] = o["mapeo_columnas"][:-1]  # omite una columna
            return json.dumps(o, ensure_ascii=False)
        raise RuntimeError("no")
    run = MultiAgentSystem(ScriptedLLM(r7)).analyze_path(path)
    sc = schema_of(run); t1 = next(t for t in run.trace if "Agente 1" in t["etapa"])
    out.append(("I-07", "Agente 1", "El LLM tipifica 'canal' (texto) como numérico, falsea % de nulos y omite una columna → la herramienta rechaza el tipo, restituye lo medido y la columna omitida",
                sc["canal"]["tipo"] == "categorico" and len(run.outputs["auditor"]["mapeo_columnas"]) == len(run.schema) and any("restituida" in c for c in t1["correcciones_guardrail"]), t1["correcciones_guardrail"][:3]))
    return out


# =============================================================================== matriz
def write_matrix(runs, times):
    bit = json.loads((DOCS / "bitacora_fallas.json").read_text(encoding="utf-8")) if (DOCS / "bitacora_fallas.json").exists() else []
    byid = {r["id"]: r for r in RESULTS}
    L = ["# Matriz de Auditoría y Control de Testeo (Fase 4)", "",
         f"_Generada automáticamente por `tests/run_tests.py` el {time.strftime('%Y-%m-%d %H:%M')}. Huella prompts: `{catalog_hash()}`._", "",
         "## 1. Registro de fallas detectadas y ajustes aplicados", "",
         "Cada fila es una falla **real** observada durante las pruebas (primera ejecución), el ajuste aplicado y la **re-verificación automática** de la prueba que la cubre.", "",
         "| # | Dataset de prueba | Agente auditado | Esperado vs. Obtenido (primera ejecución) | Ajuste aplicado | Regla de prompt | Re-verificación |", "|---|---|---|---|---|---|---|"]
    for b in bit:
        chk = [byid.get(c) for c in b["checks"]]
        st = "✅ " + ", ".join(b["checks"]) if all(c and c["ok"] for c in chk) else "❌ " + ", ".join(b["checks"])
        L.append(f"| {b['id']} | {b['dataset']} | {b['agente']} | **Esperado:** {b['esperado']}<br>**Obtenido:** {b['obtenido']} | {b['ajuste']} | {b.get('regla_prompt', '—')} | {st} |")
    L += ["", f"**Fallas registradas: {len(bit)}** · todas con re-verificación: {sum(1 for b in bit if all(byid.get(c, {}).get('ok') for c in b['checks']))}/{len(bit)} aprobadas.", "",
          "## 2. Resultados de la batería completa (estado actual)", "", "| ID | Dataset | Agente auditado | Resultado esperado | Estado |", "|---|---|---|---|---|"]
    for r in RESULTS:
        L.append(f"| {r['id']} | {r['dataset']} | {r['agente']} | {r['esperado']} | {'✅ PASA' if r['ok'] else '❌ FALLA — ' + r['detalle'][:80]} |")
    ok = sum(1 for r in RESULTS if r["ok"])
    L += ["", f"**Total: {ok}/{len(RESULTS)} verificaciones aprobadas.**", "", "## 3. Tiempos de procesamiento", "", "| Dataset | Segundos |", "|---|---|"]
    L += [f"| {k} | {v:.1f} |" for k, v in times.items()]
    (DOCS / "matriz_auditoria.md").write_text("\n".join(L), encoding="utf-8")
    (DOCS / "matriz_auditoria.json").write_text(json.dumps({"fallas": bit, "resultados": RESULTS}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
