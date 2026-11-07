# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Agente 5 (PLUS) · Consejero Estratégico y Líder-Analista.

Objetivo: que quien administra decida MEJOR. Cuestiona la decisión (abogado del diablo), contrasta con los datos,
detecta sesgos, propone alternativas y entrega un plan de liderazgo. Es adaptable a cualquier rol, sector y pregunta:
nada está cableado a un dominio; el lente se infiere del rol declarado, del dominio de los datos y del propio mensaje.

Con LLM disponible el modelo razona libremente (prompt 'estratega'); este módulo aporta las SEÑALES verificables
(entidades de los datos mencionadas, cifras de la decisión vs variabilidad real, sesgos) y el motor de respaldo.
"""
from __future__ import annotations

import re
import statistics

import numpy as np
import pandas as pd

from .analytics import _time_block, natural_agg, r2
from .offline import h, infer_domain
from .text_utils import STOPWORDS, clip, fmt_num as N, fmt_pct as P, norm_key, norm_text, strip_accents, tokens

# ------------------------------------------------------------------------------------------ lentes por rol
LENSES = {
    "finanzas": {"kw": ["cfo", "financ", "contador", "tesor", "presupuest", "controller", "contralor"],
                 "prioridad": "retorno, flujo de caja, riesgo y sensibilidad a escenarios", "kpis": ["margen", "flujo de caja", "retorno de la inversión", "costo por unidad"],
                 "stake": ["Dirección general", "Control interno / auditoría", "Áreas que ceden o reciben presupuesto"],
                 "com": "Presenta tres escenarios (base, optimista, pesimista) con el supuesto que más mueve el resultado y el punto de equilibrio."},
    "comercial": {"kw": ["comercial", "ventas", "marketing", "mercadeo", "retail", "tienda", "canal", "gerente de cuenta", "e-commerce", "ecommerce"],
                  "prioridad": "crecimiento, mezcla de ingresos, retención de clientes y rentabilidad por segmento", "kpis": ["ventas por segmento", "ticket promedio", "recompra", "margen por categoría"],
                  "stake": ["Equipo de ventas", "Clientes clave", "Operaciones / inventario", "Finanzas"],
                  "com": "Comunica la meta por segmento con su incentivo y qué se hará con los clientes afectados antes de que se enteren por terceros."},
    "operaciones": {"kw": ["operacion", "produccion", "planta", "logistic", "supply", "cadena", "manufactura", "mantenimiento", "jefe de turno", "almacen"],
                    "prioridad": "capacidad, calidad, tiempos de ciclo, costos y continuidad operativa", "kpis": ["tasa de defectos", "tiempo de paro", "rendimiento por turno", "costo por unidad"],
                    "stake": ["Operarios y supervisores", "Calidad", "Mantenimiento", "Compras / proveedores"],
                    "com": "Explica el cambio al piso de planta con el 'por qué' y un plazo de adaptación; los cambios operativos fallan por ejecución, no por diseño."},
    "servicio": {"kw": ["servicio al cliente", "servicio al ciudadano", "ciudadan", "atencion", "pqr", "calidad", "experiencia", "cliente", "usuario", "soporte", "call center", "contact center", "defensor"],
                 "prioridad": "experiencia del usuario, tiempos de respuesta, causa raíz de quejas y cumplimiento de plazos", "kpis": ["tiempo de respuesta", "% de quejas resueltas a la primera", "satisfacción", "reincidencia"],
                 "stake": ["Usuarios / clientes", "Agentes de atención", "Áreas responsables de la causa raíz", "Control interno"],
                 "com": "Comprométete públicamente con un plazo medible y reporta avances; en servicio la credibilidad se gana cumpliendo lo prometido."},
    "talento": {"kw": ["talento", "rrhh", "recursos humanos", "gestion humana", "personal", "nomina", "seleccion", "bienestar"],
                "prioridad": "clima, rotación, equidad interna y cumplimiento normativo", "kpis": ["rotación", "ausentismo", "tiempo de cobertura de vacantes", "clima laboral"],
                "stake": ["Colaboradores afectados", "Jefes directos", "Jurídico", "Sindicato / representantes"],
                "com": "Informa primero a los directamente afectados, con claridad y respeto; el rumor es más costoso que la mala noticia."},
    "publico": {"kw": ["secretari", "alcalde", "gobernad", "gobierno", "entidad", "ministeri", "sector publico", "concejal", "planeacion", "veedur", "director de entidad", "municipio"],
                "prioridad": "impacto social, equidad territorial, legalidad, transparencia y uso eficiente del recurso público", "kpis": ["cobertura", "brecha entre territorios", "ejecución presupuestal", "satisfacción ciudadana"],
                "stake": ["Ciudadanía beneficiaria", "Órganos de control", "Concejo / asamblea", "Otras secretarías"],
                "com": "Publica criterios y datos de la decisión; en el sector público la legitimidad depende de la transparencia y la rendición de cuentas."},
    "salud": {"kw": ["medic", "hospital", "clinica", "salud", "enfermer", "ips", "eps", "paciente", "epidemiolog"],
              "prioridad": "seguridad del paciente, oportunidad de la atención, capacidad instalada y sostenibilidad", "kpis": ["estancia promedio", "reingresos", "tiempo de espera", "mortalidad ajustada"],
              "stake": ["Pacientes y familias", "Personal asistencial", "Comité de calidad / ética", "Aseguradores"],
              "com": "Prioriza seguridad del paciente en el mensaje y consulta al comité clínico; evita decisiones solo financieras sobre procesos asistenciales."},
    "educacion": {"kw": ["rector", "docente", "profesor", "universidad", "decano", "academic", "colegio", "escuela", "coordinador", "facultad", "estudiante"],
                  "prioridad": "permanencia, aprendizaje, equidad de acceso y calidad académica", "kpis": ["deserción", "aprobación", "cobertura", "satisfacción estudiantil"],
                  "stake": ["Estudiantes", "Docentes", "Familias", "Consejo académico"],
                  "com": "Involucra a docentes y estudiantes en el diseño; las reformas académicas sin participación suelen revertirse."},
    "general": {"kw": [], "prioridad": "resultados medibles, riesgos, costo de oportunidad y capacidad de ejecución", "kpis": ["indicador principal de éxito", "costo", "tiempo de ejecución", "satisfacción de afectados"],
                "stake": ["Quienes ejecutan la decisión", "Quienes se ven afectados", "Quien financia"],
                "com": "Explica el problema, la evidencia, lo que NO se sabe y el criterio con el que se revisará la decisión."},
}

# ------------------------------------------------------------------------------------------ niveles jerárquicos (Agente 6)
COMPETENCIAS = ["Diagnóstico con datos", "Priorización de recursos", "Gestión del riesgo", "Comunicación y escalamiento", "Coordinación y ejecución", "Visión estratégica"]
NIVELES = {
    "Auxiliar": {"alcance": "ejecutas tareas operativas con precisión y escalas lo que excede tu autoridad",
                 "responsabilidad": "registrar con precisión y escalar a tiempo lo que observo", "siguiente": "Asistente", "lente": "servicio",
                 "importancia": {"Diagnóstico con datos": "media", "Priorización de recursos": "baja", "Gestión del riesgo": "media", "Comunicación y escalamiento": "alta", "Coordinación y ejecución": "alta", "Visión estratégica": "baja"}},
    "Asistente": {"alcance": "analizas información y preparas insumos confiables para quien decide",
                  "responsabilidad": "analizar la información y preparar insumos confiables para decidir", "siguiente": "Supervisor", "lente": "general",
                  "importancia": {"Diagnóstico con datos": "alta", "Priorización de recursos": "media", "Gestión del riesgo": "media", "Comunicación y escalamiento": "alta", "Coordinación y ejecución": "media", "Visión estratégica": "baja"}},
    "Supervisor": {"alcance": "coordinas equipos y conviertes las decisiones de la dirección en acciones con seguimiento",
                   "responsabilidad": "coordinar al equipo y ejecutar el plan con seguimiento", "siguiente": "Gerente", "lente": "operaciones",
                   "importancia": {"Diagnóstico con datos": "media", "Priorización de recursos": "alta", "Gestión del riesgo": "alta", "Comunicación y escalamiento": "alta", "Coordinación y ejecución": "alta", "Visión estratégica": "media"}},
    "Gerente": {"alcance": "defines prioridades y recursos, respondes por el resultado y comunicas la dirección",
                "responsabilidad": "decidir prioridades y recursos y responder por el resultado", "siguiente": None, "lente": "general",
                "importancia": {"Diagnóstico con datos": "alta", "Priorización de recursos": "alta", "Gestión del riesgo": "alta", "Comunicación y escalamiento": "alta", "Coordinación y ejecución": "media", "Visión estratégica": "alta"}},
}
# Qué tipo de respuesta es la mejor para cada nivel (1 = ideal; 0 = fuera de su alcance o impulsiva)
ALCANCE_SCORE = {
    "Auxiliar": {"escalar": 1.0, "analizar": 0.5, "coordinar": 0.25, "decidir": 0.0, "riesgosa": 0.0, "inaccion": 0.0},
    "Asistente": {"analizar": 1.0, "escalar": 0.5, "coordinar": 0.5, "decidir": 0.0, "riesgosa": 0.0, "inaccion": 0.0},
    "Supervisor": {"coordinar": 1.0, "escalar": 0.5, "analizar": 0.5, "decidir": 0.25, "riesgosa": 0.0, "inaccion": 0.0},
    "Gerente": {"decidir": 1.0, "coordinar": 0.5, "analizar": 0.25, "escalar": 0.0, "riesgosa": 0.0, "inaccion": 0.0},
}
RECOMENDACIONES = {
    "Diagnóstico con datos": {"Auxiliar": "Verifica cada cifra contra la fuente antes de reportarla y anota siempre fecha y origen del dato.",
                              "Asistente": "Fortalece el análisis: revisa nulos, atípicos y la diferencia entre media y mediana antes de presentar conclusiones.",
                              "Supervisor": "Pide a tu equipo el dato de respaldo y distingue correlación de causa antes de asignar acciones.",
                              "Gerente": "Exige calidad de datos y límites de cada cifra antes de decidir; evita decidir con una sola métrica."},
    "Priorización de recursos": {"Auxiliar": "Identifica qué tareas impactan más el resultado y consulta a tu jefe cuando haya conflicto de prioridades.",
                                 "Asistente": "Construye matrices impacto/esfuerzo para ordenar tus entregas y las de tu área.",
                                 "Supervisor": "Usa criterios explícitos (impacto, costo, urgencia) para asignar los recursos del equipo y comunícalos.",
                                 "Gerente": "Define criterios para asignar recursos escasos, protege lo que sostiene el ingreso y fija fechas de revisión."},
    "Gestión del riesgo": {"Auxiliar": "Reporta los riesgos apenas los detectes y con evidencia; no los corrijas en silencio.",
                           "Asistente": "Documenta supuestos y riesgos en cada análisis que prepares.",
                           "Supervisor": "Planea contingencias para tu equipo y define quién actúa si el plan falla.",
                           "Gerente": "Prefiere decisiones reversibles o por fases y fija de antemano el criterio de marcha atrás."},
    "Comunicación y escalamiento": {"Auxiliar": "Escala con hechos: qué pasó, desde cuándo, qué impacto y qué necesitas de tu jefe.",
                                    "Asistente": "Resume tus análisis en una página: conclusión, evidencia y recomendación.",
                                    "Supervisor": "Traduce las decisiones de la dirección en instrucciones claras y recoge las inquietudes del equipo.",
                                    "Gerente": "Comunica la situación, las medidas y los próximos pasos con transparencia; reconoce lo que aún no se sabe."},
    "Coordinación y ejecución": {"Auxiliar": "Sigue el procedimiento paso a paso y confirma que recibiste y entendiste las instrucciones.",
                                 "Asistente": "Coordina con otras áreas los datos que necesitas y confirma plazos por escrito.",
                                 "Supervisor": "Asigna responsable, plazo y criterio de éxito, y haz seguimiento semanal.",
                                 "Gerente": "Delega con responsable, plazo y métrica, y evita microgestionar la ejecución."},
    "Visión estratégica": {"Auxiliar": "Entiende cómo tu tarea contribuye a los objetivos de la empresa.",
                           "Asistente": "Relaciona tus análisis con los objetivos de la empresa para sugerir mejoras.",
                           "Supervisor": "Conecta las metas de tu equipo con la estrategia y anticipa efectos a 6-12 meses.",
                           "Gerente": "Evalúa el efecto a 12 meses, evita el sesgo del costo hundido y considera los efectos de segundo orden."},
}

ACTIONS = {
    "reducir": ["bajar", "reducir", "recortar", "disminuir", "eliminar", "cancelar", "cerrar", "descontinuar", "despedir", "suspender", "quitar", "congelar", "vender", "liquidar", "desvincular"],
    "ampliar": ["subir", "aumentar", "incrementar", "ampliar", "invertir", "contratar", "lanzar", "abrir", "comprar", "expandir", "crecer", "duplicar", "priorizar", "reforzar", "potenciar"],
    "cambiar": ["cambiar", "migrar", "automatizar", "implementar", "tercerizar", "trasladar", "reestructurar", "fusionar", "centralizar", "descentralizar", "reemplazar", "digitalizar", "externalizar", "reorganizar", "modificar", "adoptar"],
}
IRREVERSIBLE = {"cerrar", "eliminar", "despedir", "vender", "liquidar", "cancelar", "fusionar", "desvincular", "descontinuar", "tercerizar", "externalizar"}
DECISION_CUES = ["voy a", "vamos a", "quiero", "queremos", "pienso", "planeo", "planeamos", "decidi", "decidimos", "propongo", "proponemos", "debemos", "deberiamos", "deberia", "tengo que", "necesito", "hay que", "estoy pensando", "me gustaria", "estamos pensando", "se me ocurre", "creo que debemos", "mi plan", "mi decision", "optaria"]
QUESTION_CUES = ["que ", "como ", "cual", "por que", "cuanto", "cuantos", "donde", "quien", "cuando", "puedes", "podemos", "es verdad", "sera", "hay "]

BIASES = [
    ("Exceso de certeza", r"\b(seguro|segura|obvio|evidente|sin duda|claramente|no hay duda|100 ?%|siempre|nunca|todos|nadie|garantizado|imposible que)\b",
     "Pídete una cifra: ¿en qué proporción de los casos es cierto? Busca activamente un contraejemplo antes de decidir."),
    ("Evidencia anecdótica / disponibilidad", r"\b(un cliente me|me (dijo|dijeron|comento|comentaron|conto|contaron|aseguro|aseguraron)|escuche que|me parece|creo que|siento que|dicen que|vi que|el otro dia|me llego un caso|segun mi experiencia|intuicion)\b",
     "Contrasta la impresión con la base completa: ¿qué porcentaje de los registros la respalda?"),
    ("Costo hundido", r"\b(ya invertimos|ya gastamos|hemos invertido|no podemos echar atras|ya llevamos|tanto tiempo|ya pagamos|ya compramos|hemos gastado)\b",
     "Decide solo con costos y beneficios FUTUROS; lo ya gastado no cambia con ninguna opción."),
    ("Inercia / status quo", r"\b(siempre lo hemos|como siempre|asi ha funcionado|tradicionalmente|siempre se ha hecho|asi se hace)\b",
     "Pregunta: si empezáramos hoy desde cero, ¿elegiríamos esto?"),
    ("Presión de urgencia", r"\b(urgente|ya mismo|inmediatamente|no hay tiempo|lo antes posible|cuanto antes|de inmediato|esta semana|hoy mismo)\b",
     "La urgencia degrada la calidad de la decisión: ¿qué se pierde realmente si esperas dos semanas para un piloto o más datos?"),
    ("Autoridad / presión social", r"\b(el jefe|la junta|me pidieron|los accionistas|la gerencia quiere|todos lo hacen|la competencia lo|me ordenaron|el director quiere|el alcalde quiere|nos exigen)\b",
     "Separa quién lo pide de qué evidencia lo respalda; explicita qué dato haría cambiar de opinión a esa autoridad."),
    ("Causalidad apresurada", r"\b(por eso|debido a|es culpa de|causo|gracias a|la causa es|se debe a|provoco|esto explica)\b",
     "Correlación no es causalidad: ¿qué otra explicación produciría el mismo patrón? ¿Qué pasó antes y después del cambio?"),
    ("Sesgo de confirmación", r"\b(confirma|como ya sabia|lo que esperaba|tal como pensaba|demuestra que|prueba que|como suponia)\b",
     "Busca datos que contradigan tu hipótesis; si no los encuentras, pregúntate si los buscaste bien."),
    ("Optimismo / falacia de planificación", r"\b(facil|sin problema|sin riesgos?|no (tiene|tendra|hay|habra|existe|conlleva|implica)n? (ningun )?(riesgo|problema|costo|impacto)s?|va a funcionar|seguro funciona|rapido|en una semana|sin costo|sin impacto)\b",
     "Los proyectos tardan y cuestan más de lo previsto: duplica mentalmente plazo y costo y vuelve a evaluar."),
    ("Visión de túnel (una sola métrica)", r"\b(solo|unicamente|lo unico que importa|nada mas que|exclusivamente)\b",
     "Define al menos una métrica de equilibrio (calidad, satisfacción, costo) que no debe deteriorarse."),
    ("Falsa dicotomía", r"\b(o esto o|la unica opcion|no hay otra|o lo hacemos o|tenemos que elegir entre)\b",
     "Casi siempre hay una tercera vía: piloto, versión parcial, secuencia por fases."),
    ("Horizonte cortoplacista", r"\b(este mes|esta semana|este trimestre|a corto plazo|ahora mismo|este ano fiscal)\b",
     "Evalúa también el efecto a 12 meses: muchas decisiones mejoran el corto plazo y deterioran el largo."),
]


def _has(text: str, words) -> str | None:
    t = f" {norm_key(text)} "
    for w in words:
        if f" {w} " in t or t.find(f" {w}") >= 0 and len(w) > 5 and w in t:
            return w
    return None


def detect_lens(rol: str, message: str, dominio: str) -> tuple[str, str, bool]:
    """Devuelve (lente, etiqueta_rol, rol_declarado)."""
    label = (rol or "").strip()
    declared = bool(label)
    if not label:
        m = re.search(r"\b(?:soy|como|trabajo como|me desempeno como|actuo como|mi rol es)\s+(?:el |la |un |una |su )?([a-z ]{3,45}?)(?:[,.;:]| de la | de mi |$| y | quiero| voy| necesito| debo| tengo)", strip_accents(message.lower()))
        if m:
            label, declared = m.group(1).strip(), True
    t = norm_text(label)
    for key, lens in LENSES.items():  # coincidencia por INICIO de palabra: 'rector' no debe activarse con 'di-rector'
        if key != "general" and any(re.search(r"\b" + re.escape(k), t) for k in lens["kw"]):
            return key, label or key, declared
    # sin rol claro: lente por dominio de los datos
    dom_map = {"comercial": "comercial", "servicio": "servicio", "producción": "operaciones", "social": "publico", "salud": "salud", "financiero": "finanzas", "recursos": "talento", "educación": "educacion"}
    for k, v in dom_map.items():
        if k in dominio:
            return v, label or "administrador/a", declared
    return "general", label or "administrador/a", declared


def classify(message: str) -> dict:
    t = norm_key(message)
    verbs = {cat: [w for w in ws if re.search(rf"\b{w}\w*", t)] for cat, ws in ACTIONS.items()}
    cat = next((c for c in ("reducir", "ampliar", "cambiar") if verbs[c]), None)
    cue = next((c for c in DECISION_CUES if c in t), None)
    is_q = "?" in message or any(t.startswith(q) or f" {q}" in f" {t}"[:25] for q in QUESTION_CUES)
    if cat or cue:
        mode = "decision"
    elif is_q:
        mode = "pregunta"
    else:
        mode = "exploracion"
    verb = (verbs[cat][0] if cat else None)
    return {"modo": mode, "categoria_accion": cat, "verbo": verb, "irreversible": bool(verb and verb in IRREVERSIBLE) or any(re.search(rf"\b{w}\w*", t) for w in IRREVERSIBLE), "es_pregunta": is_q}


# ------------------------------------------------------------------------------------------ señales con datos
def variability(facts: dict) -> dict:
    out = {"variacion_tipica_pct": None, "desviacion_variacion_pct": None, "medida": facts.get("medida_principal")}
    t = (facts.get("tiempo") or [None])[0]
    if t and (t.get("n_medio_por_periodo") or 0) >= 20:  # con periodos de pocos registros la variación es ruido, se usa el CV
        key = "suma" if t["agregacion"] == "suma" else "media"
        vals = [p[key] for p in t["serie"] if p.get(key) is not None]
        if t["ultimo_periodo_parcial"] and len(vals) > 3:
            vals = vals[:-1]
        ch = [100 * (b - a) / abs(a) for a, b in zip(vals, vals[1:]) if a]
        if len(ch) >= 3:
            out["variacion_tipica_pct"] = r2(statistics.median(abs(c) for c in ch))
            out["multiplicador_reversion"] = 1.5
            out["umbral_reversion_pct"] = r2(1.5 * out["variacion_tipica_pct"])
            out["desviacion_variacion_pct"] = r2(statistics.pstdev(ch))
            out["n_periodos"] = len(vals)
    if out["variacion_tipica_pct"] is None:
        m = next((n for n in facts.get("numericas", []) if n["columna"] == facts.get("medida_principal")), None)
        if m and m["cv"] is not None:
            out["cv_pct"] = r2(100 * m["cv"])
    return out


def find_entities(run, message: str, limit: int = 3) -> list[dict]:
    df, f = run.clean, run.facts
    tn = f" {norm_text(message)} "
    found = []
    for c in run.schema:
        if c["tipo"] != "categorico":
            continue
        col = c["normalizado"]
        s = df[col].dropna().astype(str)
        if s.nunique() > 300:
            continue
        for v in s.unique():
            nv = norm_text(v)
            if len(nv) >= 3 and not nv.isdigit() and f" {nv} " in tn:
                found.append((len(nv), col, v))
    found.sort(reverse=True)
    out, used = [], set()
    for _, col, v in found:
        if (col, v) in used:
            continue
        used.add((col, v))
        out.append(entity_stats(run, col, v))
        if len(out) >= limit:
            break
    return out


def entity_stats(run, col: str, val: str) -> dict:
    df, f = run.clean, run.facts
    mask = df[col].astype(str) == val
    d = {"columna": col, "valor": val, "n": int(mask.sum()), "pct_registros": r2(100 * mask.mean())}
    m = f.get("medida_principal")
    if m:
        agg = natural_agg(m)
        sub = df.loc[mask, m].dropna()
        d["medida"] = m
        d["agregacion"] = agg
        if len(sub):
            d["media"] = r2(sub.mean())
            d["media_general"] = r2(df[m].mean())
            if df[m].mean():
                d["dif_vs_general_pct"] = r2(100 * (sub.mean() - df[m].mean()) / abs(df[m].mean()))
            if agg == "suma":
                d["suma"] = r2(sub.sum())
                d["pct_medida"] = r2(100 * sub.sum() / df[m].sum()) if df[m].sum() else None
            g = df.groupby(col)[m].agg("sum" if agg == "suma" else "mean").sort_values(ascending=False)
            if val in g.index:
                d["posicion"], d["de"] = int(list(g.index).index(val) + 1), int(len(g))
        fcol = f.get("fecha_principal")
        if fcol and mask.sum() >= 12:
            tb = _time_block(df[mask], fcol, m)
            if tb:
                d["variacion_ultimo_periodo_pct"] = tb["variacion_ultimo_vs_previo_pct"]
                d["tendencia_pct_periodo"] = tb["tendencia_pct_por_periodo"]
                tg = (f.get("tiempo") or [None])[0]
                if tg:
                    d["variacion_general_pct"] = tg["variacion_ultimo_vs_previo_pct"]
    seen_ind = set()
    for ib in f.get("indicadores", []):
        if ib["indicador"] in seen_ind:
            continue
        seen_ind.add(ib["indicador"])
        s = df.loc[mask, ib["indicador"]].dropna()
        if len(s) >= 10:
            d.setdefault("indicadores", []).append({"indicador": ib["indicador"], "pct": r2(100 * float(s.map(bool).mean())), "pct_general": ib["tasa_global_pct"], "n": int(len(s))})
    for tx in f.get("texto", [])[:1]:
        if tx["columna"] in df:
            from .text_utils import sentiment
            sub = df.loc[mask, tx["columna"]].dropna().astype(str)
            if len(sub) >= 10:
                d["pct_negativo_texto"] = r2(100 * float(np.mean([sentiment(x) == -1 for x in sub[:3000]])))
                d["pct_negativo_general"] = tx["sentimiento"]["pct_negativo"]
    return d


def parse_user_numbers(message: str, facts: dict, var: dict) -> list[dict]:
    out = []
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(%|por ciento|puntos porcentuales)", message):
        p = float(m.group(1).replace(",", "."))
        item = {"texto": m.group(0), "valor": p, "tipo": "porcentaje"}
        tip = var.get("variacion_tipica_pct")
        if tip:
            item["veces_variacion_tipica"] = r2(p / tip, 1)
            item["variacion_tipica_pct"] = tip
            item["desviacion_variacion_pct"] = var.get("desviacion_variacion_pct")
        elif var.get("cv_pct"):
            item["cv_pct"] = var["cv_pct"]
            item["veces_cv"] = r2(p / var["cv_pct"], 1)
        out.append(item)
    for m in re.finditer(r"(?:\$|cop|usd)\s*([\d.,]+)\s*(mil millones|millones|millon|mil|m)?|([\d.,]+)\s*(mil millones|millones|millon)\s*(?:de\s*)?(?:pesos|cop|usd|dolares)?", strip_accents(message.lower())):
        num = m.group(1) or m.group(3)
        unit = (m.group(2) or m.group(4) or "").strip()
        try:
            from .profiler import parse_number
            v = parse_number(num, ",")
        except Exception:  # noqa: BLE001
            v = None
        if v is None:
            continue
        v *= {"mil millones": 1e9, "millones": 1e6, "millon": 1e6, "m": 1e6, "mil": 1e3}.get(unit, 1)
        item = {"texto": m.group(0).strip(), "valor": v, "tipo": "monto"}
        mn = next((n for n in facts.get("numericas", []) if n["columna"] == facts.get("medida_principal") and n["agregacion_natural"] == "suma"), None)
        if mn and mn["suma"]:
            item["pct_de_total_observado"] = r2(100 * v / mn["suma"])
            item["medida"] = mn["columna"]
        out.append(item)
    for m in re.finditer(r"(\d+)\s*(dias|semanas|meses|anos|trimestres)", strip_accents(message.lower())):
        out.append({"texto": m.group(0), "valor": int(m.group(1)), "tipo": "horizonte", "unidad": m.group(2)})
    return out


def query_columns(run, text: str) -> dict:
    """Vincula palabras de la pregunta con columnas (por raíz de 5 letras) y precalcula las agrupaciones pedidas.

    Es lo que permite responder preguntas arbitrarias sobre CUALQUIER dataset sin reglas por dominio.
    """
    from .analytics import _interaction

    df, f = run.clean, run.facts
    stems = {t[:5] for t in tokens(text) if len(t) >= 4 and t not in STOPWORDS}

    def hit(col):
        return any(len(p) >= 4 and p[:5] in stems for p in col.split("_"))

    meds = [n["columna"] for n in f["numericas"] if hit(n["columna"])]
    dims = [c["normalizado"] for c in run.schema if c["tipo"] == "categorico" and hit(c["normalizado"]) and 2 <= df[c["normalizado"]].nunique() <= 100]
    out = {"medidas": meds[:2], "dimensiones": dims[:2], "interacciones": []}
    main = f.get("medida_principal")
    pairs = [(m, d) for m in (meds[:2] or ([main] if main and dims else [])) for d in dims[:2]]
    for m, d in pairs[:3]:
        it = _interaction(df, m, d)
        if it:
            out["interacciones"].append({k: it[k] for k in ("ref", "medida", "dimension", "agregacion", "mejor", "peor", "grupos", "media_general")})
    return out


def detect_biases(message: str) -> list[dict]:
    t = norm_key(message)
    out = []
    for name, rx, counter in BIASES:
        m = re.search(rx, t)
        if m:
            out.append({"sesgo": name, "senal": f"«{m.group(0).strip()}»", "contramedida": counter})
    return out


def gaps(schema: list[dict]) -> list[str]:
    names = " ".join(c["normalizado"] for c in schema)
    hints = {"costo/margen": ["costo", "margen", "utilidad", "gasto"], "meta u objetivo": ["meta", "objetivo", "presupuesto", "target"], "satisfacción o resultado del cliente/usuario": ["satisf", "nps", "calificacion", "csat"],
             "benchmark externo / competencia": ["competencia", "mercado", "benchmark"], "ubicación o segmento detallado": ["zona", "region", "segmento", "ciudad", "municipio"]}
    return [k for k, ws in hints.items() if not any(w in names for w in ws)]


def build_signals(run, message: str, rol: str = "", history: list | None = None) -> dict:
    f, schema = run.facts, run.schema
    dom = (run.outputs.get("interprete") or {}).get("dominio_inferido") or infer_domain(f, schema)
    cl = classify(message)
    eff = message
    follow = False
    prev_dec = next((m["texto"] for m in reversed(history or []) if m.get("rol") == "usuario" and classify(m["texto"])["modo"] == "decision"), None)
    if prev_dec and cl["modo"] != "decision" and len(message.split()) < 25:
        eff, follow = prev_dec + " " + message, True
        cl = classify(eff)
    lens, label, declared = detect_lens(rol, eff, dom["dominio"])
    var = variability(f)
    return {"clasificacion": cl, "seguimiento": follow, "lente": lens, "rol_etiqueta": label, "rol_declarado": declared, "dominio": dom["dominio"],
            "entidades": find_entities(run, eff), "consulta": query_columns(run, eff), "cifras_usuario": parse_user_numbers(eff, f, var), "variabilidad": var, "sesgos": detect_biases(eff),
            "huecos_de_datos": gaps(schema), "texto_efectivo": eff}


# ------------------------------------------------------------------------------------------ motor de respaldo
def _sev_pts(s):
    return {"alta": 2.0, "media": 1.0, "baja": 0.5}.get(s, 0.5)


def advise_offline(run, message: str, rol: str = "", history: list | None = None, signals: dict | None = None) -> dict:
    f = run.facts
    sg = signals or build_signals(run, message, rol, history)
    cl, lens_key = sg["clasificacion"], sg["lente"]
    lens = LENSES[lens_key]
    mode = cl["modo"]
    hallazgos = (run.outputs.get("interprete") or {}).get("hallazgos", [])
    q = f["calidad"]
    main = f.get("medida_principal")
    ents, nums, biases = sg["entidades"], sg["cifras_usuario"], sg["sesgos"]
    var = sg["variabilidad"]
    cuest, a_favor, en_contra = [], [], []
    verbo, cat = cl.get("verbo"), cl.get("categoria_accion")

    # --- 1) contraste con entidades de los datos
    for e in ents:
        nm = f"«{e['valor']}» ({h(e['columna'])})"
        line = f"{nm}: {N(e['n'])} registros ({P(e['pct_registros'])})"
        if e.get("pct_medida") is not None:
            line += f", {P(e['pct_medida'])} de {h(e['medida'])} acumulado"
        if e.get("posicion"):
            line += f", puesto {e['posicion']} de {e['de']}"
        if e.get("dif_vs_general_pct") is not None:
            line += f"; su promedio de {h(e['medida'])} ({N(e['media'])}) está {P(abs(e['dif_vs_general_pct']))} {'por encima' if e['dif_vs_general_pct'] > 0 else 'por debajo'} del general ({N(e['media_general'])})"
        line += "."
        strong = (e.get("pct_medida") or 0) >= 15 or (e.get("posicion") == 1) or (e.get("dif_vs_general_pct") or 0) > 10
        weak = (e.get("pct_medida") is not None and e["pct_medida"] < 8) or (e.get("dif_vs_general_pct") or 0) < -10 or (e.get("variacion_ultimo_periodo_pct") or 0) < -5
        if cat == "reducir":
            (en_contra if strong else a_favor).append(line)
        elif cat == "ampliar":
            (a_favor if strong else en_contra).append(line)
        else:
            (a_favor if strong else en_contra if weak else a_favor).append(line)
        if e.get("variacion_ultimo_periodo_pct") is not None:
            vv = e["variacion_ultimo_periodo_pct"]
            gen = e.get("variacion_general_pct")
            rel = (vv - gen) if gen is not None else vv  # se compara contra el comportamiento general, no contra cero
            tendencia = f"La tendencia reciente de {nm} es {P(vv)} frente al periodo previo" + (f" (general: {P(gen)}; {'peor' if rel < 0 else 'mejor'} que el conjunto)" if gen is not None else "") + "."
            ((a_favor if (rel < 0) == (cat == "reducir") else en_contra) if cat in ("reducir", "ampliar") else a_favor).append(tendencia)
        if e.get("pct_negativo_texto") is not None:
            a_favor.append(f"En {nm}, el {P(e['pct_negativo_texto'])} de los mensajes es negativo (general: {P(e['pct_negativo_general'])}).") if (cat == "ampliar" or cat == "cambiar") and e["pct_negativo_texto"] > e["pct_negativo_general"] else None
        for ind in e.get("indicadores", []):
            if abs(ind["pct"] - ind["pct_general"]) >= 5:
                cuest.append({"supuesto": f"Que la medida propuesta mejora el indicador «{h(ind['indicador'])}», que en {nm} se aparta del resto",
                              "por_que_importa": f"En {nm} la proporción de «Sí/verdadero» en {h(ind['indicador'])} es {P(ind['pct'])} frente a {P(ind['pct_general'])} en general (n={N(ind['n'])}). Una decisión que no actúe sobre esa brecha puede empeorarla.",
                              "prueba_que_lo_refutaria": "Comparar el indicador antes y después de la medida contra un grupo equivalente que no la reciba.", "severidad": "media"})
        if cat == "reducir" and e.get("posicion") and e.get("de") and e["posicion"] <= (e["de"] + 1) // 2 and (e.get("dif_vs_general_pct") or 0) > -10:
            cuest.append({"supuesto": f"Que {nm} tiene un desempeño bajo (premisa de la decisión)",
                          "por_que_importa": f"Los datos no respaldan del todo esa premisa: ocupa el puesto {e['posicion']} de {e['de']} en {h(e['medida'])}" + (f" y su promedio está {P(abs(e['dif_vs_general_pct']))} {'por encima' if e['dif_vs_general_pct'] > 0 else 'por debajo'} del general." if e.get("dif_vs_general_pct") is not None else "."),
                          "prueba_que_lo_refutaria": "Definir qué significa 'bajo' (umbral y métrica) y verificar que se cumple en al menos dos periodos distintos.", "severidad": "alta"})
        if cat == "reducir" and e.get("pct_medida"):
            cuest.append({"supuesto": f"Que {nm} puede reducirse o cerrarse sin afectar el resto del negocio",
                          "por_que_importa": f"Aporta {P(e['pct_medida'])} de {h(e['medida'])}; si no hay sustitución, ese volumen se pierde y los costos fijos se reparten entre menos.",
                          "prueba_que_lo_refutaria": "Si al excluirlo el resto no absorbe su volumen (clientes que migran) o si su contribución neta (después de costos) es positiva, la decisión empeora el resultado.",
                          "severidad": "alta" if e["pct_medida"] >= 10 else "media"})
        elif cat == "ampliar" and e.get("pct_medida") is not None:
            cuest.append({"supuesto": f"Que reforzar {nm} producirá retornos proporcionales a su desempeño pasado",
                          "por_que_importa": f"Hoy representa {P(e['pct_medida'])} de {h(e['medida'])}; el desempeño pasado no garantiza que más recursos escalen igual (rendimientos decrecientes, saturación).",
                          "prueba_que_lo_refutaria": "Un piloto en el que el aumento de recursos no mueva el indicador en el plazo acordado.", "severidad": "media"})
        elif e.get("n", 0) < 30:
            cuest.append({"supuesto": f"Que lo observado en {nm} es representativo", "por_que_importa": f"Solo hay {N(e['n'])} registros: la variación aleatoria puede explicar cualquier patrón.",
                          "prueba_que_lo_refutaria": "Ampliar el periodo o la muestra y verificar que el patrón persiste.", "severidad": "alta"})

    # --- 2) magnitud de la cifra planteada vs variabilidad real
    for n in nums:
        if n["tipo"] == "porcentaje":
            if n.get("veces_variacion_tipica") is not None:
                big = n["veces_variacion_tipica"] >= 3
                txt = f"El cambio de {P(n['valor'])} equivale a {N(n['veces_variacion_tipica'], 1)} veces la variación típica entre periodos de {h(var['medida'] or 'la medida principal')} ({P(n['variacion_tipica_pct'])})."
                (en_contra if big else a_favor).append(txt)
                cuest.append({"supuesto": f"Que un ajuste de {P(n['valor'])} es una magnitud razonable y alcanzable",
                              "por_que_importa": txt + (" Es un cambio fuera del rango normal: sus efectos son impredecibles con los datos históricos." if big else " Está en un rango compatible con la variación histórica."),
                              "prueba_que_lo_refutaria": "Una prueba en un subconjunto que muestre que la respuesta del indicador es mucho menor (o mayor) a la esperada.", "severidad": "alta" if big else "baja"})
            elif n.get("veces_cv") is not None:
                cuest.append({"supuesto": f"Que un cambio de {P(n['valor'])} es significativo frente al ruido natural de los datos",
                              "por_que_importa": f"El coeficiente de variación de {h(var['medida'])} es {P(n['cv_pct'])}: {'el cambio queda dentro del ruido' if n['valor'] < n['cv_pct'] else 'el cambio supera el ruido, pero hay que confirmar su efecto'}.",
                              "prueba_que_lo_refutaria": "Medir el indicador antes y después con un grupo de comparación.", "severidad": "media"})
        if n["tipo"] == "monto" and n.get("pct_de_total_observado") is not None:
            cuest.append({"supuesto": f"Que el monto de {n['texto']} es proporcional al beneficio esperado",
                          "por_que_importa": f"Equivale a {P(n['pct_de_total_observado'])} del total observado de {h(n['medida'])}; ¿qué retorno mínimo exige esa inversión y en cuánto tiempo?",
                          "prueba_que_lo_refutaria": "Un cálculo de punto de equilibrio que requiera supuestos de crecimiento superiores a la tendencia histórica.", "severidad": "alta" if n["pct_de_total_observado"] >= 10 else "media"})

    # --- 3) suficiencia y calidad de los datos
    n_rows = f["resumen"]["filas"]
    if q["puntaje"] < 65:
        cuest.append({"supuesto": "Que los datos son suficientemente confiables para decidir", "por_que_importa": f"La calidad es {q['veredicto']} (puntaje {q['puntaje']}/100; nulos promedio {P(q['pct_nulos_promedio'])}).",
                      "prueba_que_lo_refutaria": "Auditar una muestra contra la fuente: si más de un 10% difiere, no decidas con esta base.", "severidad": "alta"})
        en_contra.append(f"La calidad de datos es {q['veredicto']} (puntaje {q['puntaje']}/100).")
    elif q["puntaje"] >= 85:
        a_favor.append(f"La calidad de los datos es alta (puntaje {q['puntaje']}/100), lo que da base sólida al análisis.")
    if n_rows < 100:
        cuest.append({"supuesto": "Que el tamaño de muestra permite generalizar", "por_que_importa": f"Hay solo {N(n_rows)} filas.", "prueba_que_lo_refutaria": "Repetir el análisis con más periodos; si las conclusiones cambian, eran ruido.", "severidad": "alta"})
    t0 = (f.get("tiempo") or [None])[0]
    if t0 and t0["dias"] < 365:
        cuest.append({"supuesto": "Que el periodo observado es representativo del año completo", "por_que_importa": f"Los datos cubren {N(t0['dias'])} días: no se puede separar estacionalidad de tendencia.",
                      "prueba_que_lo_refutaria": "Comparar contra el mismo periodo del año anterior.", "severidad": "media"})
    if sg["huecos_de_datos"] and mode == "decision":
        cuest.append({"supuesto": "Que los datos disponibles contienen todo lo necesario para decidir", "por_que_importa": "Faltan variables que normalmente cambian la decisión: " + ", ".join(sg["huecos_de_datos"][:3]) + ".",
                      "prueba_que_lo_refutaria": "Incorporar esas variables; si la conclusión se invierte, la decisión estaba mal informada.", "severidad": "media"})
    # --- 4) causalidad / concentración / contrafactual
    if any(b["sesgo"] == "Causalidad apresurada" for b in biases) and f["correlaciones"]:
        c = f["correlaciones"][0]
        cuest.append({"supuesto": "Que la relación que percibes es causal", "por_que_importa": f"Los datos solo muestran asociación (p. ej. {h(c['a'])} vs {h(c['b'])}: r={N(c['r'], 2)}); puede haber un tercer factor.",
                      "prueba_que_lo_refutaria": "Un cambio controlado (piloto con grupo de comparación) que no reproduzca el efecto.", "severidad": "alta"})
    if t0 and t0.get("tendencia_pct_por_periodo") is not None and (t0.get("r2_tendencia") or 0) >= 0.3:
        cuest.append({"supuesto": "Que la situación actual cambiará si no se hace nada diferente",
                      "por_que_importa": f"La tendencia vigente es {P(t0['tendencia_pct_por_periodo'])} por {t0['granularidad']} (R²={N(t0['r2_tendencia'], 2)}). Ese es el escenario base contra el cual debe compararse cualquier intervención.",
                      "prueba_que_lo_refutaria": "Si la intervención no mejora el indicador por encima de esa tendencia, su efecto es nulo.", "severidad": "media"})
    if cl["irreversible"]:
        cuest.append({"supuesto": "Que la decisión puede corregirse si sale mal", "por_que_importa": f"'{verbo or 'esta acción'}' es de baja reversibilidad (puerta de una vía): exige más evidencia que una decisión reversible.",
                      "prueba_que_lo_refutaria": "Si existe una versión parcial, temporal o por fases que capture la mayor parte del beneficio con la mitad del riesgo, esa es preferible.", "severidad": "alta"})
    pareto = next((i for i in f["interacciones"] if i.get("pareto_top20_pct")), None)
    if pareto and pareto["pareto_top20_pct"] >= 60 and mode == "decision":
        cuest.append({"supuesto": "Que el efecto será parejo entre categorías", "por_que_importa": f"En {h(pareto['dimension'])}, el 20% superior de categorías aporta {P(pareto['pareto_top20_pct'])} de {h(pareto['medida'])}: el resultado depende de pocas piezas.",
                      "prueba_que_lo_refutaria": "Simular la decisión excluyendo las 2 categorías principales: si el resultado se derrumba, hay riesgo de concentración.", "severidad": "media"})
    # sesgos → cuestionamientos
    for b in biases[:4]:
        cuest.append({"supuesto": f"Tu planteamiento muestra señales de «{b['sesgo']}» ({b['senal']})", "por_que_importa": "Los sesgos no se sienten como sesgos: se sienten como sentido común.", "prueba_que_lo_refutaria": b["contramedida"], "severidad": "media"})

    # --- 5) hallazgos relevantes como evidencia (para preguntas / exploración)
    for hz in hallazgos[:3]:
        (en_contra if hz["tipo"] == "riesgo" else a_favor).append(f"{hz['titulo']}: {clip(hz['hallazgo'], 200)} [{', '.join(hz['evidencia'])}]") if mode != "decision" or not ents else None

    # --- 6) postura
    pts = sum(_sev_pts(c["severidad"]) for c in cuest) + 0.5 * len(biases) + (2 if cl["irreversible"] else 0) + 0.7 * len(en_contra) - 0.7 * len(a_favor)
    linked = bool(ents or nums)
    if mode == "decision":
        if q["puntaje"] < 40 or n_rows < 30 or (not linked and not hallazgos):
            postura = "evidencia insuficiente"
        elif pts >= 7:
            postura = "reconsiderar"
        elif pts >= 4 or cl["irreversible"]:
            postura = "pilotar primero"
        elif pts >= 2 or biases or len(cuest) >= 3 or not a_favor:  # 'proceder' a secas es excepcional: sin sesgos, sin objeciones y con evidencia a favor
            postura = "proceder con condiciones"
        else:
            postura = "proceder"
        conf = "alta" if (q["puntaje"] >= 85 and ents and n_rows >= 300 and not biases) else "media" if (q["puntaje"] >= 65 and linked) else "baja"
    elif mode == "pregunta":
        postura, conf = "responder con cautela", ("media" if q["puntaje"] >= 65 else "baja")
    else:
        postura, conf = "explorar antes de decidir", "media" if q["puntaje"] >= 65 else "baja"

    # --- 7) alternativas
    txt = norm_key(sg["texto_efectivo"])
    if re.search(r"\b(precio|tarifa|descuento|comision)\w*", txt):
        alts = [("Prueba A/B de precio en una categoría o sucursal", "Mide elasticidad real con riesgo acotado", "Requiere diseño y 4-8 semanas", "Cuando la elasticidad es desconocida"),
                ("Ajuste segmentado (solo productos/clientes menos sensibles)", "Protege volumen en los segmentos críticos", "Complejidad comercial y de comunicación", "Cuando hay segmentos con alta lealtad"),
                ("Actuar sobre descuentos y mezcla antes que sobre el precio base", "Más reversible, afecta menos la percepción", "Beneficio menor", "Cuando el descuento promedio es alto")]
    elif cl["irreversible"] or cat == "reducir":
        alts = [("Reducción gradual o congelamiento con umbral de activación", "Reversible; captura parte del ahorro", "Ahorro más lento", "Cuando la contribución real es incierta"),
                ("Reestructurar el modelo (más ligero) en lugar de eliminar", "Preserva ingresos y capacidad instalada", "Exige rediseño operativo", "Cuando la unidad aporta volumen o presencia"),
                ("No hacer nada y monitorear con criterios de salida predefinidos", "Costo de decisión nulo", "Costo de oportunidad si el deterioro es real", "Cuando la tendencia no es clara")]
    elif cat == "ampliar":
        alts = [("Piloto acotado (un segmento / una sede) con métrica de éxito", "Aprende barato; decisión de escalar con datos", "Tarda más en producir resultados", "Cuando el retorno es incierto"),
                ("Escalar por fases con hitos de continuación", "Limita la exposición", "Menos impacto inicial", "Cuando hay capacidad de ejecución limitada"),
                ("Mejorar productividad de lo existente antes de sumar capacidad", "Costo menor; revela cuellos de botella", "Puede ser insuficiente si hay saturación", "Cuando la utilización actual es baja")]
    elif cat == "cambiar":
        alts = [("Implementación en un área piloto con operación en paralelo", "Detecta fallas sin riesgo sistémico", "Doble esfuerzo temporal", "Cuando el cambio toca procesos críticos"),
                ("Gestión del cambio y capacitación primero", "Aumenta adopción", "Retrasa el beneficio", "Cuando hay resistencia previsible"),
                ("Mantener el proceso actual con mejoras incrementales", "Riesgo mínimo", "Puede perpetuar el problema de fondo", "Cuando el problema no está bien diagnosticado")]
    else:
        alts = [("Piloto de 30 días con métrica de éxito definida de antemano", "Evidencia propia con bajo costo", "Requiere disciplina de medición", "Siempre que la decisión sea reversible"),
                ("Atacar la causa raíz antes que el síntoma", "Soluciones más duraderas", "Necesita diagnóstico", "Cuando el problema se repite"),
                ("Esperar y medir con un umbral que dispare la acción", "Evita actuar por ruido", "Posible demora", "Cuando la señal aún es débil")]
    alternativas = [{"opcion": a, "pros": b, "contras": c, "cuando_elegirla": d} for a, b, c, d in alts]

    # --- 8) premortem y preguntas
    premortem = []
    if ents:
        premortem.append(f"La decisión se apoyó en «{ents[0]['valor']}» sin conocer su rentabilidad real (los datos no incluyen {', '.join(sg['huecos_de_datos'][:1]) or 'costos'}), y el efecto neto fue opuesto al esperado.")
    for b in biases[:2]:
        premortem.append(f"Se decidió bajo «{b['sesgo']}» y nadie pidió evidencia contraria a tiempo.")
    premortem += [f"Quienes debían ejecutar ({lens['stake'][0]}) no estaban alineados y la implementación se diluyó.",
                  "Un efecto de segundo orden no previsto (reacción de clientes, usuarios o competidores) anuló el beneficio.",
                  "No había una métrica de éxito ni un umbral de reversión, por lo que se persistió en la decisión cuando ya era claro que no funcionaba."]
    preguntas = []
    if not sg["rol_declarado"]:
        preguntas.append("¿Cuál es tu rol y qué autoridad tienes sobre esta decisión? Ajusto el lente según eso.")
    if mode == "decision":
        preguntas.append("¿Qué número concreto debe moverse, cuánto y en qué plazo para decir que la decisión funcionó?")
        preguntas.append("¿Qué evidencia, si apareciera en 30 días, te haría cambiar de opinión?")
        if sg["huecos_de_datos"]:
            preguntas.append(f"¿Tienes datos de {sg['huecos_de_datos'][0]}? Cambian la conclusión con alta probabilidad.")
        preguntas.append("¿Quién pierde con esta decisión y cómo va a reaccionar?")
    elif mode == "pregunta":
        preguntas += ["¿Qué decisión concreta depende de esta respuesta?", "¿Qué cifra o resultado te sorprendería y por qué?"]
    else:
        preguntas += ["¿Qué decisión estás evaluando tomar con esta información en el próximo trimestre?", "¿Qué metas o presupuestos hay que respetar?"]
    if any(b["sesgo"].startswith("Evidencia anecdótica") for b in biases):
        preguntas.insert(0, "¿Cuántos casos documentados respaldan lo que percibes, de cuántos totales?")
    prev_q = {norm_key(m["texto"]) for m in (history or []) if m.get("rol") == "asesor"}
    preguntas = [x for x in preguntas if norm_key(x) not in prev_q][:4]

    # --- 9) plan de liderazgo
    kpis = []
    if main:
        agg = natural_agg(main)
        kpis.append(f"{h(main)} ({'acumulado' if agg == 'suma' else 'promedio'}) por {t0['granularidad'] if t0 else 'periodo'}")
    for e in ents[:1]:
        kpis.append(f"{h(e['medida']) if e.get('medida') else 'indicador'} en «{e['valor']}»")
    kpis += lens["kpis"][:2]
    if f["texto"]:
        kpis.append(f"% de mensajes negativos (base: {P(f['texto'][0]['sentimiento']['pct_negativo'])})")
    tip = var.get("variacion_tipica_pct")
    reversion = (f"Si {h(main) if main else 'el indicador principal'} cae más de {P(var['umbral_reversion_pct'])} por periodo (1,5× la variación típica de {P(tip)}) durante dos periodos seguidos, o no mejora en el plazo pactado, se revierte o se replantea."
                 if tip else "Definir antes de empezar un umbral numérico y una fecha de revisión; si no se cumple, se revierte sin culpas.")
    plan = {"primeros_pasos": ["Escribir la hipótesis en una frase: 'Si hacemos X, el indicador Y cambiará en Z en N semanas'.", "Fijar la línea base con los datos actuales (este informe sirve de punto de partida).",
                               f"Alinear a: {', '.join(lens['stake'][:3])}; pedir a cada uno que nombre el mayor riesgo.", "Diseñar el piloto o la versión parcial y su grupo de comparación." if mode == "decision" else "Elegir la decisión priorizada y repetir la consulta con ella formulada."],
            "kpis": kpis[:5], "stakeholders": lens["stake"], "comunicacion": lens["com"], "criterio_de_reversion": reversion}

    # --- 10) respuesta directa
    if mode == "decision":
        top_against = en_contra[0] if en_contra else (cuest[0]["por_que_importa"] if cuest else "No hay evidencia en contra en los datos disponibles")
        top_for = a_favor[0] if a_favor else "Los datos disponibles no aportan evidencia directa a favor"
        direct = f"Mi postura: **{postura}** (confianza {conf}). A favor: {clip(top_for, 220)} En contra: {clip(top_against, 220)}"
        if postura == "evidencia insuficiente":
            direct += " Antes de decidir, consigue el dato mínimo que falta (ver 'datos que faltan')."
    elif mode == "pregunta":
        direct = answer_question(run, sg)
    else:
        sugeridas = [hz for hz in hallazgos if hz["impacto"] in ("alto", "medio")][:3]
        direct = "Estas son las decisiones que los datos sugieren y lo que yo cuestionaría de cada una: " + " | ".join(f"{i}) {hz['accion_sugerida']} → ¿qué evidencia mostraría que {hz['titulo'].lower()} es la causa y no un síntoma?" for i, hz in enumerate(sugeridas, 1)) if sugeridas else "Los datos no muestran una palanca clara; empieza por definir qué decisión quieres apoyar."
        for hz in sugeridas:
            cuest.append({"supuesto": f"Que «{hz['titulo']}» es el problema a resolver", "por_que_importa": clip(hz["hallazgo"], 200), "prueba_que_lo_refutaria": "Si al segmentar por otra dimensión el patrón desaparece, era un artefacto de mezcla.", "severidad": "media"})

    if mode == "pregunta":
        for it in (f["interacciones"][:1]):
            cuest.append({"supuesto": "Que la pregunta presupone una relación o un hecho que ya está confirmado", "por_que_importa": "Una pregunta bien formulada ya contiene una hipótesis; si es falsa, la respuesta correcta puede inducir a error.",
                          "prueba_que_lo_refutaria": f"Reformular sin la presuposición y verificar con una segunda dimensión (p. ej. {h(it['dimension'])}).", "severidad": "baja"})
        if q["puntaje"] < 85:
            cuest.append({"supuesto": "Que los datos son suficientes para responder con precisión", "por_que_importa": f"Calidad {q['veredicto']} ({q['puntaje']}/100).", "prueba_que_lo_refutaria": "Revisar la cobertura y los nulos de las variables usadas.", "severidad": "media"})

    reform = {"decision": f"Decisión a evaluar: {clip(sg['texto_efectivo'], 160)} → La pregunta de fondo es si la evidencia muestra que ese es el problema/palanca correcta y que la acción mejora el resultado sin dañar lo que hoy funciona.",
              "pregunta": f"Pregunta: {clip(sg['texto_efectivo'], 160)} → Antes de responder: ¿qué decisión depende de esto y qué cifra la cambiaría?",
              "exploracion": "Exploración abierta: identificar qué decisiones valen la pena y cuáles son sus supuestos más frágiles."}[mode]
    rol_txt = (f"Como {sg['rol_etiqueta']}, tu lente natural es {lens['prioridad']}. Te cuestionaré con ese lente y con el de quienes no están en la sala: {', '.join(lens['stake'][:3])}."
               if sg["rol_declarado"] else f"No indicaste tu rol; uso un lente de gestión {('de ' + lens_key) if lens_key != 'general' else 'general'} inferido de los datos ({sg['dominio']}). Dime tu rol y tu margen de decisión y afino el análisis.")
    if sg["seguimiento"]:
        rol_txt += " (Incorporé tu respuesta a la decisión que veníamos discutiendo.)"
    sev_order = {"alta": 0, "media": 1, "baja": 2}
    cuest = sorted({c["supuesto"]: c for c in cuest}.values(), key=lambda c: sev_order[c["severidad"]])[:7]
    conds = []
    if postura in ("proceder con condiciones", "pilotar primero", "reconsiderar"):
        conds = ["Definir métrica de éxito, plazo y umbral de reversión por escrito antes de ejecutar.", "Ejecutar primero en una unidad acotada o con grupo de comparación.",
                 *(["Obtener el dato que falta: " + sg["huecos_de_datos"][0] + "."] if sg["huecos_de_datos"] else [])]
    datos = [f"Falta información sobre: {x}." for x in sg["huecos_de_datos"][:4]] + ([f"Cobertura temporal limitada ({N(t0['dias'])} días)."] if t0 and t0["dias"] < 365 else [])
    return {"modo": mode, "reformulacion": reform, "lectura_del_rol": rol_txt, "respuesta_directa": direct, "evidencia_a_favor": list(dict.fromkeys(a_favor))[:5], "evidencia_en_contra": list(dict.fromkeys(en_contra))[:5],
            "cuestionamientos": cuest, "sesgos_detectados": biases, "premortem": premortem[:5], "alternativas": alternativas,
            "recomendacion": {"postura": postura, "confianza": conf, "condiciones": conds}, "plan_liderazgo": plan, "preguntas_para_el_administrador": preguntas, "datos_que_faltan": datos}


def answer_question(run, sg: dict) -> str:
    f = run.facts
    t = norm_key(sg["texto_efectivo"])
    parts = []
    for e in sg["entidades"][:2]:
        s = f"«{e['valor']}» ({h(e['columna'])}): {N(e['n'])} registros ({P(e['pct_registros'])})"
        if e.get("pct_medida") is not None:
            s += f", {P(e['pct_medida'])} de {h(e['medida'])}"
        if e.get("media") is not None:
            s += f"; promedio de {h(e['medida'])} {N(e['media'])} (general {N(e['media_general'])})"
        parts.append(s + ".")
    worst_q = bool(re.search(r"\b(peor|menor|menos|minim\w*|bajo|rezag\w*)\b", t))
    for it in sg["consulta"]["interacciones"][:2]:  # pregunta vinculada a columnas concretas del dataset
        pick, other = (it["peor"], it["mejor"]) if worst_q else (it["mejor"], it["peor"])
        key = "suma" if it["agregacion"] == "suma" else "media"
        parts.append(f"{'El menor' if worst_q else 'El mayor'} {'total' if key == 'suma' else 'promedio'} de {h(it['medida'])} por {h(it['dimension'])} está en «{pick['categoria']}» ({N(pick[key])}); el extremo opuesto es «{other['categoria']}» ({N(other[key])}).")
    if not parts and sg["consulta"]["medidas"]:
        for m in sg["consulta"]["medidas"]:
            n = next((x for x in f["numericas"] if x["columna"] == m), None)
            if n:
                parts.append(f"{h(m).capitalize()}: suma {N(n['suma'])}, media {N(n['media'])}, mediana {N(n['mediana'])}, máximo {N(n['max'])}, mínimo {N(n['min'])} (n={N(n['n'])}).")
    inter = f["interacciones"][:1]
    if not sg["consulta"]["interacciones"] and re.search(r"\b(mejor|mayor|mas|lider|top|principal)\b", t) and inter:
        it = inter[0]
        parts.append(f"En {h(it['dimension'])}, lidera «{it['grupos'][0]['categoria']}» en {h(it['medida'])} ({N(it['grupos'][0]['suma'] if it['agregacion'] == 'suma' else it['grupos'][0]['media'])}).")
    if not sg["consulta"]["interacciones"] and worst_q and inter:
        it = inter[0]
        parts.append(f"El menor valor en {h(it['dimension'])} es «{it['peor']['categoria']}» ({N(it['peor']['suma'] if it['agregacion'] == 'suma' else it['peor']['media'])}).")
    tm = (f.get("tiempo") or [None])[0]
    if re.search(r"\b(tendencia|crece|crecimiento|evolucion|cae|cayo|aumento|baja|subio|mes|periodo)\w*", t) and tm and tm["variacion_ultimo_vs_previo_pct"] is not None:
        parts.append(f"Variación del último periodo completo: {P(tm['variacion_ultimo_vs_previo_pct'])}; pendiente {P(tm['tendencia_pct_por_periodo']) if tm['tendencia_pct_por_periodo'] is not None else 'N/A'} por {tm['granularidad']}.")
    if f["texto"] and re.search(r"\b(queja|sentimiento|satisf|insatisf|negativ|opinion|comentario|reclamo)\w*", t):
        s = f["texto"][0]["sentimiento"]
        parts.append(f"Sentimiento: {P(s['pct_negativo'])} negativo, {P(s['pct_positivo'])} positivo, {P(s['pct_neutro'])} neutro.")
    if not parts:
        hz = (run.outputs.get("interprete") or {}).get("hallazgos", [])[:3]
        parts = [f"{x['titulo']}: {clip(x['hallazgo'], 180)}" for x in hz] or ["No encuentro en los datos una respuesta directa a esa pregunta."]
    return " ".join(parts)
