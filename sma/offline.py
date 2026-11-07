# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Motores deterministas de respaldo de los Agentes 1-4 (misma interfaz JSON que la versión LLM).

Sirven para: (1) operar sin conexión ni API key, (2) ser el piso de calidad ante fallas del LLM,
(3) permitir pruebas reproducibles. Toda cifra proviene del objeto 'hechos' (trazabilidad total).
"""
from __future__ import annotations

from .text_utils import clip, fmt_num as N, fmt_pct as P, norm_key

DOMAINS = {
    "comercial / ventas": ["venta", "ventas", "total", "precio", "producto", "cliente", "sucursal", "descuento", "cantidad", "factura", "pedido", "vendedor", "categoria", "pago", "ingreso", "tienda", "sku"],
    "servicio al ciudadano / PQR": ["radicado", "pqr", "queja", "reclamo", "peticion", "solicitud", "canal", "descripcion", "estado", "respuesta", "usuario", "area", "responsable", "sugerencia", "felicitacion"],
    "producción / operaciones": ["produccion", "maquina", "turno", "planta", "defect", "defectuosas", "paro", "producidas", "operario", "orden", "lote", "mantenimiento", "linea"],
    "social / territorial": ["municipio", "departamento", "poblacion", "pobreza", "desempleo", "cobertura", "homicidios", "indicador", "region", "hab", "educativa", "multidimensional"],
    "salud / hospitalario": ["paciente", "diagnostico", "estancia", "urgencias", "alta", "hospital", "cirugia", "pediatria", "ginecologia", "medicina", "remision", "fallecido", "neumonia", "dengue", "diabetes", "hipertension", "parto", "fractura"],
    "financiero": ["saldo", "credito", "interes", "cuenta", "deuda", "presupuesto", "gasto", "utilidad", "cartera", "mora", "inversion", "tasa"],
    "recursos humanos": ["empleado", "salario", "cargo", "nomina", "ausentismo", "rotacion", "contrato", "antiguedad", "vacaciones"],
    "educación": ["estudiante", "nota", "curso", "programa", "facultad", "asignatura", "matricula", "desercion", "docente", "promedio", "semestre"],
}
WORSE_IF_HIGH = ("queja", "defect", "costo", "gasto", "merma", "mora", "desercion", "paro", "demora", "dias", "tiempo", "homicidio", "pobreza", "desempleo", "mortalidad", "error", "retraso")


def h(col: str) -> str:
    return str(col).replace("_", " ")


TIPO_LBL = {"valor_atipico": "valor atípico", "pico_o_caida_periodo": "pico o caída del periodo"}


def tl(t: str) -> str:
    return TIPO_LBL.get(t, t.replace("_", " "))


def infer_domain(facts: dict, schema: list[dict]) -> dict:
    bag = [norm_key(c["normalizado"]).replace(" ", "_") for c in schema]
    toks = {t for b in bag for t in b.split("_")}
    vals = set()
    for c in facts.get("categoricas", []):
        for t in c["top"][:8]:
            vals.add(norm_key(t["valor"]))
    for t in facts.get("texto", []):
        vals |= {w["palabra"] for w in t["palabras_top"][:10]}
    vtoks = {w for v in vals for w in v.split()}
    scores = {}
    ev = {}
    for dom, kw in DOMAINS.items():
        hit_cols = sorted({k for k in kw if k in toks or any(k in b for b in bag if len(k) > 4)})
        hit_vals = sorted({k for k in kw if k in vtoks or k in vals})
        scores[dom] = len(hit_cols) * 1.0 + len(hit_vals) * 0.7
        ev[dom] = hit_cols + [f"valor:{v}" for v in hit_vals]
    best = max(scores, key=scores.get)
    ordered = sorted(scores.values(), reverse=True)
    top, second = ordered[0], ordered[1] if len(ordered) > 1 else 0
    if top < 1.5:
        return {"dominio": "genérico (no determinado)", "confianza": "baja", "evidencia": ["Los nombres y valores de las variables no coinciden con un dominio conocido."], "puntajes": {}}
    conf = "alta" if top >= 4 and top >= 1.5 * second else "media" if top >= 2.4 else "baja"
    return {"dominio": best, "confianza": conf, "evidencia": ev[best][:6], "puntajes": {k: round(v, 1) for k, v in scores.items() if v}}


# =============================================================================== AGENTE 1
def offline_auditor(p: dict) -> dict:
    schema = p["esquema_preliminar"]
    mapeo = []
    for c in schema:
        d = {"original": c["original"], "normalizado": c["normalizado"], "tipo": c["tipo"], "rol": c["rol"], "pct_nulos": c.get("pct_nulos", 0.0), "detalle": c.get("detalle", "")}
        mapeo.append(d)
    reglas = list(p.get("acciones_limpieza", []))
    ren = [e for e in p.get("log_encabezados", []) if e["original"] != e["normalizado"]]
    if ren:
        reglas.insert(0, f"Encabezados normalizados a snake_case sin tildes ({len(ren)} renombrados).")
    adv = list(p.get("ingesta", []))
    n = p.get("n_filas_crudas", 0)
    if n < 30:
        adv.append(f"Muestra pequeña ({n} filas): las conclusiones estadísticas tienen baja potencia.")
    q = p["calidad"]
    return {"mapeo_columnas": mapeo, "problemas": p.get("problemas_detectados", []), "reglas_limpieza": reglas,
            "calidad_global": {"puntaje": q["puntaje"], "veredicto": q["veredicto"]}, "advertencias": adv}


# =============================================================================== AGENTE 2
def offline_analista(p: dict) -> dict:
    f = p["hechos"]
    nums = f["numericas"]
    main = f["medida_principal"]
    ordered = sorted([x for x in nums if x["columna"] != main], key=lambda x: (-x["n"], -(x["cv"] or 0)))
    top3 = ([x for x in nums if x["columna"] == main] + ordered)[:3]
    resumen = [{k: x[k] for k in ("columna", "n", "media", "mediana", "min", "max", "suma", "desv")} for x in top3]
    inter = []
    for it in f["interacciones"][:6]:
        g0 = it["grupos"][0]
        if it["agregacion"] == "suma":
            hz = f"{h(it['medida'])} por {h(it['dimension'])}: «{g0['categoria']}» lidera con {N(g0['suma'])}" + (f" ({P(g0['pct_total'])} del total)" if g0.get("pct_total") is not None else "") + f"; «{it['peor']['categoria']}» es el menor ({N(it['peor']['suma'])})."
        else:
            hz = f"{h(it['medida'])} por {h(it['dimension'])}: mayor promedio en «{it['mejor']['categoria']}» ({N(it['mejor']['media'])}) y menor en «{it['peor']['categoria']}» ({N(it['peor']['media'])})."
        if it.get("brecha_media_pct") is not None:
            hz += f" Brecha de promedios: {P(it['brecha_media_pct'])}."
        inter.append({"ref": it["ref"], "medida": it["medida"], "dimension": it["dimension"], "hallazgo": clip(hz, 260), "mejor": it["mejor"], "peor": it["peor"], "eta2": it["eta2"]})
    tend = []
    for t in f["tiempo"][:2]:
        d = f"{h(t['medida'] or 'registros')} ({t['agregacion']}) entre {t['desde']} y {t['hasta']} en {t['n_periodos']} periodos ({t['granularidad']})."
        if t["variacion_ultimo_vs_previo_pct"] is not None:
            d += f" Variación del último periodo completo frente al previo: {P(t['variacion_ultimo_vs_previo_pct'])}."
        if t["tendencia_pct_por_periodo"] is not None:
            d += f" Pendiente: {P(t['tendencia_pct_por_periodo'])} por periodo (R²={N(t['r2_tendencia'], 2)})."
        if t["ultimo_periodo_parcial"]:
            d += " El último periodo es parcial y se excluyó de la comparación."
        tend.append({"ref": t["ref"], "columna": t["columna"], "descripcion": clip(d, 320), "variacion_pct": t["variacion_ultimo_vs_previo_pct"], "tendencia_pct_periodo": t["tendencia_pct_por_periodo"]})
    corr = []
    for c in f["correlaciones"][:4]:
        fz = "fuerte" if abs(c["r"]) >= 0.7 else "moderada"
        corr.append({"ref": c["ref"], "a": c["a"], "b": c["b"], "r": c["r"], "lectura": f"Correlación {fz} {'positiva' if c['r'] > 0 else 'negativa'} (r={N(c['r'], 2)}, n={N(c['n'])}); no implica causalidad."})
    cat_all = []
    for cat in f["categoricas"]:
        if cat["columna"] in f["dimensiones_analizadas"][:2]:
            cat_all += [{"variable": cat["columna"], "valor": t["valor"], "n": t["n"], "pct": t["pct"]} for t in cat["top"][:3]]
    # AJ-03: máximo 5 categorías con frecuencia explícita
    top_cats = cat_all[:5]
    sent = temas = None
    if f["texto"]:
        tx = f["texto"][0]
        sent = {**tx["sentimiento"], "variable": tx["columna"]}
        temas = [{"tema": t["tema"], "n": t["n"], "pct": t["pct"]} for t in tx["temas"][:5]]
    anom = [{"ref": a["ref"], "descripcion": f"{tl(a['tipo'])} en {h(a['columna'])}: valor {N(a['valor'])} (z={N(a['z'], 1)}) en {a['id']}."} for a in f["anomalias"]]
    lim = []
    if f["resumen"]["filas"] < 30:
        lim.append(f"Solo {f['resumen']['filas']} filas: resultados exploratorios, no concluyentes.")
    if not f["tiempo"]:
        lim.append("No se detectó columna de fecha: no se evaluaron tendencias ni estacionalidad.")
    if not nums:
        lim.append("No hay variables cuantitativas utilizables: el análisis es solo de frecuencias.")
    if main and str(main).startswith("columna_"):
        lim.append(f"Los nombres de columna no son informativos: se asumió «{main}» como medida principal por ser la variable aditiva de mayor magnitud acumulada.")
    if f["calidad"]["puntaje"] < 65:
        lim.append(f"Calidad de datos {f['calidad']['veredicto']} (puntaje {f['calidad']['puntaje']}/100): interpretar con cautela.")
    for t in f["tiempo"][:1]:
        if t["dias"] < 365 and t["granularidad"] == "mes":
            lim.append(f"La cobertura temporal es de {N(t['dias'])} días (< 1 año): no se puede separar estacionalidad de tendencia.")
    return {"variables_clave": {"cuantitativas": [x["columna"] for x in top3], "categoricas": f["dimensiones_analizadas"], "temporales": [t["columna"] for t in f["tiempo"]], "texto": [t["columna"] for t in f["texto"]]},
            "resumen_cuantitativo": resumen, "interacciones": inter, "tendencias": tend, "correlaciones": corr,
            "analisis_cualitativo": {"top_categorias": top_cats, "sentimiento": sent, "temas": temas or []}, "anomalias": anom, "limitaciones": lim}


# =============================================================================== AGENTE 3
IMPACT_ORD = {"alto": 0, "medio": 1, "bajo": 2}
ACCIONES = {
    "concentracion": {"comercial / ventas": "Proteger el segmento líder (inventario, servicio, retención) y definir un plan para desarrollar los segmentos rezagados.",
                      "servicio al ciudadano / PQR": "Asignar un responsable de causa raíz al área/categoría que concentra la mayor carga.",
                      "producción / operaciones": "Priorizar mantenimiento y control de calidad en el recurso que concentra la producción.",
                      "default": "Revisar la dependencia de la categoría dominante y definir un plan de mitigación."},
    "brecha": {"default": "Investigar qué practica o condición diferencia al mejor grupo y evaluar si es replicable en el peor."},
    "texto": {"servicio al ciudadano / PQR": "Atacar primero el tema dominante en las comunicaciones negativas y publicar un compromiso de tiempos de respuesta.",
              "default": "Priorizar el tema dominante en los comentarios negativos y medir su evolución mensual."},
}


def _acc(kind, dom):
    d = ACCIONES[kind]
    return d.get(dom, d["default"])


def offline_interprete(p: dict) -> dict:
    f, a2, sch = p["hechos"], p["analisis"], p["esquema"]
    dom = infer_domain(f, sch)
    D = dom["dominio"]
    H = []

    def add(titulo, texto, refs, impacto, tipo, accion):
        H.append({"id": f"H{len(H) + 1}", "titulo": titulo, "hallazgo": clip(texto, 420), "evidencia": refs, "impacto": impacto, "tipo": tipo, "accion_sugerida": accion})

    main = f["medida_principal"]
    for it in [i for i in f["interacciones"] if i["medida"] == main][:2]:
        g0 = it["grupos"][0]
        if it["agregacion"] == "suma" and g0.get("pct_total") is not None:
            txt = f"En {h(it['dimension'])}, «{g0['categoria']}» concentra {P(g0['pct_total'])} de {h(main)} ({N(g0['suma'])})."
            if it.get("pareto_top20_pct") is not None:
                txt += f" El 20% superior de las categorías aporta {P(it['pareto_top20_pct'])} del total."
            add(f"Concentración de {h(main)} por {h(it['dimension'])}", txt, [it["ref"]], "alto" if g0["pct_total"] >= 35 else "medio", "riesgo" if g0["pct_total"] >= 40 else "neutro", _acc("concentracion", D))
        else:
            worse_high = any(w in main for w in WORSE_IF_HIGH)
            txt = f"El promedio de {h(main)} es mayor en «{it['mejor']['categoria']}» ({N(it['mejor']['media'])}) y menor en «{it['peor']['categoria']}» ({N(it['peor']['media'])}); promedio general {N(it['media_general'])}."
            add(f"Diferencias de {h(main)} entre {h(it['dimension'])}", txt, [it["ref"]], "alto" if (it.get("brecha_media_pct") or 0) >= 30 else "medio", "riesgo" if worse_high else "oportunidad", _acc("brecha", D))
        if it["eta2"] is not None and it["eta2"] >= 0.02:
            nivel = "alta" if it["eta2"] >= 0.14 else "moderada" if it["eta2"] >= 0.06 else "baja pero detectable"
            add(f"{h(it['dimension']).capitalize()} como factor explicativo", f"La variable {h(it['dimension'])} explica una parte {nivel} de la variación de {h(main)} (η²={N(it['eta2'], 3)}). Es asociación, no causa.", [it["ref"]], "medio", "neutro", "Explorar con un análisis controlado si esta dimensión es un factor accionable.")
    for t in f["tiempo"][:1]:
        v, s = t["variacion_ultimo_vs_previo_pct"], t["tendencia_pct_por_periodo"]
        if v is not None:
            sentido = "creció" if v > 0 else "cayó" if v < 0 else "se mantuvo"
            txt = f"{h(t['medida'] or 'El volumen de registros').capitalize()} {sentido} {P(abs(v))} en el último periodo completo frente al previo."
            if s is not None and t["r2_tendencia"] is not None:
                txt += f" La pendiente promedio es {P(s)} por {t['granularidad']} (R²={N(t['r2_tendencia'], 2)})."
            if t["mejor_periodo"]:
                txt += f" Mejor periodo: {t['mejor_periodo']['periodo']} ({N(t['mejor_periodo']['valor'])}); menor: {t['peor_periodo']['periodo']} ({N(t['peor_periodo']['valor'])})."
            bad = (v > 0) == any(w in (t["medida"] or "") for w in WORSE_IF_HIGH)
            if t["variacion_confiable"]:
                add("Dinámica temporal", txt, [t["ref"]], "alto" if abs(v) >= 15 else "medio", "riesgo" if (bad and abs(v) >= 5) else "oportunidad" if v > 5 else "neutro",
                    "Confirmar con la fuente si el cambio es estructural y ajustar metas/capacidad en consecuencia.")
            else:  # periodos con pocos registros: la variación es ruido muestral, no una señal
                add("Dinámica temporal (no concluyente)", txt + f" Con solo {N(t['n_medio_por_periodo'], 1)} registros por {t['granularidad']} en promedio, esta variación es ruido muestral y no debe usarse para decidir.", [t["ref"]], "bajo", "neutro",
                    "Agrupar en periodos más largos o ampliar la muestra antes de leer tendencias.")
        if t["dia_semana_top"]:
            add("Patrón semanal", f"El día con mayor actividad es el {t['dia_semana_top']['dia']} ({P(t['dia_semana_top']['pct'])} de los registros).", [t["ref"]], "bajo", "oportunidad", "Alinear turnos, inventario o atención con el día pico.")
    for tx in f["texto"][:1]:
        s = tx["sentimiento"]
        lead = tx["temas"][0] if tx["temas"] else None
        txt = f"En el campo de texto «{h(tx['columna'])}» el {P(s['pct_negativo'])} de los mensajes es negativo ({N(s['negativo'])} de {N(tx['n_analizados'])}), el {P(s['pct_positivo'])} positivo y el {P(s['pct_neutro'])} neutro."
        if lead:
            txt += f" Tema más frecuente: {lead['tema']} ({P(lead['pct'])})."
        add("Sentimiento y temas en el texto libre", txt, [tx["ref"]], "alto" if s["pct_negativo"] >= 30 else "medio", "riesgo" if s["pct_negativo"] >= 30 else "neutro", _acc("texto", D))
    for cx in f["texto_x_dimension"][:1]:
        add(f"Dónde se concentra la insatisfacción ({h(cx['dimension'])})", f"«{cx['peor']['categoria']}» tiene el mayor porcentaje de mensajes negativos ({P(cx['peor']['pct_negativo'])}) frente a «{cx['mejor']['categoria']}» ({P(cx['mejor']['pct_negativo'])}).", [cx["ref"]], "alto", "riesgo",
            f"Intervenir primero en «{cx['peor']['categoria']}» con un plan de 30 días y medir el cambio del indicador.")
    for ib in f.get("indicadores", [])[:2]:
        gap = ib["mejor"]["pct"] - ib["peor"]["pct"]
        add(f"Proporción de «{h(ib['indicador'])}» por {h(ib['dimension'])}",
            f"La proporción de «Sí/verdadero» en {h(ib['indicador'])} es {P(ib['tasa_global_pct'])} en general, pero llega a {P(ib['mejor']['pct'])} en «{ib['mejor']['categoria']}» frente a {P(ib['peor']['pct'])} en «{ib['peor']['categoria']}».",
            [ib["ref"]], "alto" if gap >= 10 else "medio", "riesgo" if gap >= 10 else "neutro", f"Entender por qué «{ib['mejor']['categoria']}» se separa del resto antes de tomar medidas generales.")
    for n in sorted(f["numericas"], key=lambda x: -(x["outliers_pct"] or 0))[:1]:
        if (n["outliers_pct"] or 0) >= 0.5:
            add(f"Valores extremos en {h(n['columna'])}", f"Hay {N(n['outliers'])} valores atípicos ({P(n['outliers_pct'])}); la media ({N(n['media'])}) y la mediana ({N(n['mediana'])}) difieren, por lo que conviene usar medidas robustas.", [n["ref"]], "medio", "riesgo", "Validar los casos extremos con la fuente antes de usarlos en metas o pronósticos.")
    for a in f["anomalias"][:2]:
        add("Anomalía a verificar", f"{tl(a['tipo']).capitalize()} en {h(a['columna'])}: valor {N(a['valor'])} (z={N(a['z'], 1)}), identificador {a['id']}.", [a["ref"]], "medio", "riesgo", "Revisar el registro original: puede ser un error de captura o un evento real relevante.")
    for r in f["relaciones_aritmeticas"][:1]:
        add("Consistencia aritmética entre variables", f"La relación {r['expr']} se cumple en {P(r['cobertura_pct'])} de las filas: los campos derivados son coherentes con sus componentes.", [r["ref"]], "bajo", "neutro", "Usar la relación para detectar capturas inconsistentes.")
    for c in f["correlaciones"][:1]:
        add("Relación entre variables cuantitativas", f"{h(c['a'])} y {h(c['b'])} muestran correlación {'positiva' if c['r'] > 0 else 'negativa'} (r={N(c['r'], 2)}); es consistente con una relación, no prueba causalidad.", [c["ref"]], "medio", "neutro", "Evaluar si palancas sobre una de las variables mueven la otra mediante una prueba piloto.")
    for a in f["asociaciones_cat"][:1]:
        add("Asociación entre categorías", f"{h(a['a'])} y {h(a['b'])} están asociadas (V de Cramér={N(a['cramers_v'], 2)}); la combinación más frecuente es «{a['celda_top']['a']}» con «{a['celda_top']['b']}» ({P(a['celda_top']['pct'])}).", [a["ref"]], "medio", "neutro", "Segmentar las decisiones por esta combinación en lugar de usar promedios generales.")
    cal = f["calidad"]
    if cal["puntaje"] < 85 or f["resumen"]["filas"] < 30:
        add("Confiabilidad de los datos", f"Calidad {cal['veredicto']} (puntaje {cal['puntaje']}/100; nulos promedio {P(cal['pct_nulos_promedio'])}; {f['resumen']['filas']} filas)." + (" La muestra es pequeña." if f["resumen"]["filas"] < 30 else ""), ["calidad"], "alto" if cal["puntaje"] < 65 else "medio", "riesgo", "Corregir la captura en origen y reanalizar antes de tomar decisiones irreversibles.")
    if not H:
        add("Sin hallazgos concluyentes", "Los datos no muestran patrones diferenciables con el volumen y la estructura disponibles.", ["calidad"], "bajo", "neutro", "Ampliar el periodo o las variables registradas.")
    # orden de relevancia: impacto > riesgo antes que neutro > el texto libre (voz del usuario) antes que agregados numéricos
    H.sort(key=lambda x: (IMPACT_ORD.get(x["impacto"], 3), 0 if x["tipo"] == "riesgo" else 1, 0 if any(r.startswith("texto") for r in x["evidencia"]) else 1))
    for i, x in enumerate(H, 1):
        x["id"] = f"H{i}"
    alertas = []
    for c in sch:
        if c.get("pct_nulos", 0) >= 5:
            full = c["tipo"] == "vacia"
            alertas.append({"columna": c["normalizado"], "pct_nulos": "N/A" if full else c["pct_nulos"], "impacto": "No se imputaron valores; los estadísticos usan solo registros presentes."})
    riesgos = [f"{x['titulo']}: {clip(x['hallazgo'], 140)}" for x in H if x["tipo"] == "riesgo"][:5]
    oport = [f"{x['titulo']}: {clip(x['hallazgo'], 140)}" for x in H if x["tipo"] == "oportunidad"][:5]
    if not oport:
        oport = ["Mejorar la calidad y granularidad del registro para habilitar análisis más finos."]
    preg = ["¿Qué decisión concreta debe apoyar este análisis y quién la toma?", "¿Existen metas, presupuestos o benchmarks contra los cuales comparar estos valores?",
            "¿El periodo observado es representativo (campañas, cambios de proceso, eventos atípicos)?"]
    if f["texto"]:
        preg.append("¿Los mensajes negativos se corresponden con casos que efectivamente se resolvieron mal?")
    return {"dominio_inferido": {"dominio": D, "confianza": dom["confianza"], "evidencia": dom["evidencia"] or ["Sin términos reconocibles"]}, "hallazgos": H, "riesgos": riesgos, "oportunidades": oport, "alertas_datos_faltantes": alertas, "preguntas_abiertas": preg}


# =============================================================================== AGENTE 4
def offline_informe(p: dict) -> dict:
    f, a1, a2, a3 = p["hechos"], p["auditoria"], p["analisis"], p["interpretacion"]
    dom = a3["dominio_inferido"]
    H = sorted(a3["hallazgos"], key=lambda x: IMPACT_ORD.get(x["impacto"], 3))
    per = f["tiempo"][0] if f["tiempo"] else None
    ctx = f"Se analizaron {N(f['resumen']['filas'])} registros y {N(f['resumen']['columnas'])} variables" + (f", del {per['desde']} al {per['hasta']}" if per else "") + f". Dominio inferido: {dom['dominio']} (confianza {dom['confianza']})."
    words, parts = 0, []
    for s in [ctx] + [x["hallazgo"] for x in H[:3]] + [f"Calidad de datos {a1['calidad_global']['veredicto']} ({a1['calidad_global']['puntaje']}/100)."]:
        w = len(s.split())
        if words + w > 118 and parts:
            break
        parts.append(s)
        words += w
    resumen = " ".join(parts)
    if H:  # AJ-06: comenzar por la conclusión más importante
        resumen = f"{H[0]['titulo']}: {H[0]['hallazgo']} " + " ".join(x for x in parts if x != H[0]["hallazgo"])
        resumen = " ".join(resumen.split()[:118])
    recs = []
    seen = set()
    for x in H:
        if x["accion_sugerida"] in seen:
            continue
        seen.add(x["accion_sugerida"])
        recs.append({"prioridad": len(recs) + 1, "accion": x["accion_sugerida"], "justificacion": x["titulo"] + f" (impacto {x['impacto']}; evidencia {', '.join(x['evidencia'])})", "plazo": "30 días" if x["impacto"] == "alto" else "60-90 días"})
        if len(recs) == 5:
            break
    sec = []
    sec.append({"titulo": "Contexto y alcance", "contenido_md": ctx + "\n\nMétodo: cuatro agentes especializados en cadena (auditoría → estadística → interpretación → informe), con herramientas deterministas para el cálculo exacto y verificación automática de cifras."})
    sec.append({"titulo": "Hallazgos clave", "contenido_md": "\n".join(f"{i}. **{x['titulo']}** — {x['hallazgo']} _(impacto {x['impacto']}; evidencia: {', '.join(x['evidencia'])})_" for i, x in enumerate(H[:7], 1))})
    ro = ["**Riesgos**"] + [f"- {r}" for r in a3["riesgos"]] + ["", "**Oportunidades**"] + [f"- {o}" for o in a3["oportunidades"]]
    sec.append({"titulo": "Riesgos y oportunidades", "contenido_md": "\n".join(ro)})
    q = [f"Puntaje de calidad: **{a1['calidad_global']['puntaje']}/100** ({a1['calidad_global']['veredicto']})."]
    q += [f"- [{x['severidad']}] {x['columna']}: {x['detalle']} → {x['accion']}" for x in a1["problemas"][:10]]
    if a3["alertas_datos_faltantes"]:
        q += ["", "**Datos faltantes (reportados como N/A, sin imputar):**"] + [f"- {x['columna']}: {x['pct_nulos'] if x['pct_nulos'] == 'N/A' else P(x['pct_nulos'])}" for x in a3["alertas_datos_faltantes"][:12]]
    if a2["limitaciones"]:
        q += ["", "**Limitaciones del análisis:**"] + [f"- {l}" for l in a2["limitaciones"]]
    sec.append({"titulo": "Calidad de datos y limitaciones", "contenido_md": "\n".join(q)})
    viz = []
    main, dim = f["medida_principal"], f["dimension_principal"]
    if f["tiempo"]:
        t = f["tiempo"][0]
        viz.append({"id": "v1", "tipo": "linea", "titulo": f"{h(main or 'Registros').capitalize()} por {t['granularidad']}", "columna_x": t["columna"], "columna_y": main, "agregacion": "suma" if t["agregacion"] == "suma" else "media" if main else "conteo", "top": 36, "motivo": "Mostrar tendencia y estacionalidad."})
    if dim:
        agg = "suma" if (main and f["numericas"] and next((n for n in f["numericas"] if n["columna"] == main), {}).get("agregacion_natural") == "suma") else "media" if main else "conteo"
        viz.append({"id": "v2", "tipo": "barras", "titulo": f"{h(main or 'Registros').capitalize()} por {h(dim)}", "columna_x": dim, "columna_y": main, "agregacion": agg, "top": 8, "motivo": "Comparar categorías y detectar concentración."})
    if main:
        viz.append({"id": "v3", "tipo": "histograma", "titulo": f"Distribución de {h(main)}", "columna_x": main, "columna_y": None, "agregacion": "conteo", "top": 20, "motivo": "Evaluar dispersión, asimetría y valores extremos."})
    if f["texto"]:
        viz.append({"id": "v4", "tipo": "pastel", "titulo": "Sentimiento del texto libre", "columna_x": f["texto"][0]["columna"], "columna_y": None, "agregacion": "sentimiento", "top": 3, "motivo": "Dimensionar la insatisfacción."})
        if f["texto"][0]["temas"]:
            viz.append({"id": "v5", "tipo": "barras", "titulo": "Temas más frecuentes en el texto", "columna_x": f["texto"][0]["columna"], "columna_y": None, "agregacion": "temas", "top": 5, "motivo": "Priorizar causas."})
    elif len(f["dimensiones_analizadas"]) > 1:
        d2 = f["dimensiones_analizadas"][1]
        viz.append({"id": "v4", "tipo": "pastel", "titulo": f"Composición por {h(d2)}", "columna_x": d2, "columna_y": None, "agregacion": "conteo", "top": 6, "motivo": "Ver la mezcla de categorías."})
    viz.append({"id": "v9", "tipo": "barras", "titulo": "% de nulos por columna", "columna_x": "__nulos__", "columna_y": None, "agregacion": "nulos", "top": 10, "motivo": "Transparentar la calidad."})
    return {"titulo": f"Informe ejecutivo · {dom['dominio']}", "resumen_ejecutivo": resumen, "recomendaciones": recs, "secciones": sec, "visualizaciones": viz}
