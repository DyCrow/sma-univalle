# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Agente 6 · Simulador de Crisis y Evaluación Directiva.

Genera, a partir de los DATOS cargados, un ejercicio de crisis (inopia, al borde de la quiebra o crisis operativa)
calibrado al rol jerárquico de la persona (Auxiliar, Asistente, Supervisor, Gerente), con cuatro formatos de pregunta
(opción múltiple, verdadero/falso, emparejamiento y completar con desplegable) y un Reporte de Desempeño Final.

* Generación: LLM (prompt 'simulador') con validación estricta de cada pregunta, o motor determinista de respaldo.
* Evaluación: SIEMPRE aritmética determinista (puntajes con crédito parcial): una nota no debe depender de un LLM.
* La clave de respuestas vive solo en el servidor; el cliente recibe únicamente la vista pública.
"""
from __future__ import annotations

import random
import secrets
import time
from dataclasses import dataclass, field

from .agents import Agent, NV, build_whitelist, scrub_numbers
from .llm import LLM
from .offline import h, infer_domain
from .prompts import SCHEMAS
from .strategist import ALCANCE_SCORE, COMPETENCIAS, NIVELES, RECOMENDACIONES
from .text_utils import fmt_num as N, fmt_pct as P

ROLES = list(NIVELES)
FORMATOS = {"opcion_multiple": "Opción múltiple (A, B, C, D)", "verdadero_falso": "Falso / Verdadero", "emparejamiento": "Emparejar causas y soluciones", "completar": "Completar la frase (desplegable)"}
ESCENARIOS = {
    "auto": {"nombre": "Automático (según mis datos)", "descripcion": "El sistema elige la crisis que mejor se ajusta a las señales de tus datos."},
    "inopia": {"nombre": "Inopia: crisis de liquidez", "descripcion": "La empresa se queda sin caja; hay que sostener la operación con poco dinero.", "choque": 30, "horizonte": 3, "titulo": "Crisis de liquidez: la empresa está en la inopia"},
    "quiebra": {"nombre": "Al borde de la quiebra", "descripcion": "Las deudas superan la capacidad de pago y hay semanas para reaccionar.", "choque": 50, "horizonte": 2, "titulo": "Al borde de la quiebra"},
    "operativa": {"nombre": "Crisis operativa crítica", "descripcion": "Un proceso clave se detiene o se deteriora y afecta a clientes y resultados.", "choque": 40, "horizonte": 1, "titulo": "Crisis operativa crítica"},
}
_ALC = ["escalar", "analizar", "coordinar", "decidir", "riesgosa", "inaccion"]
_RAZON = {
    "escalar": "comunicar con evidencia a quien tiene la autoridad evita decidir sin información y evita ocultar el problema",
    "analizar": "ordenar los datos y las causas es el insumo que necesita quien decide, aunque por sí solo no resuelve la crisis",
    "coordinar": "alinear al equipo con responsables y plazos convierte el diagnóstico en acción",
    "decidir": "fijar prioridades y recursos con criterios y condiciones de reversión es responsabilidad de quien responde por el resultado",
    "riesgosa": "actuar de forma impulsiva y sin evidencia puede agravar la crisis y es difícil de revertir",
    "inaccion": "esperar o ignorar la señal deja que el problema escale",
}


@dataclass
class Simulation:
    sim_id: str
    run_id: str
    rol: str
    escenario: str
    dinamica: str
    contexto: dict
    preguntas: list
    motor: str = "determinista"
    creada: float = field(default_factory=time.time)
    resultado: dict | None = None


# ============================================================================================== contexto
def pick_scenario(facts: dict, wanted: str) -> tuple[str, str]:
    if wanted in ("inopia", "quiebra", "operativa"):
        return wanted, "elegido por la persona"
    t = (facts.get("tiempo") or [None])[0]
    var = t["variacion_ultimo_vs_previo_pct"] if t and t.get("variacion_confiable") else None
    neg = facts["texto"][0]["sentimiento"]["pct_negativo"] if facts.get("texto") else None
    if neg is not None and neg >= 40:
        return "operativa", f"hay {P(neg)} de mensajes negativos en los datos (señal de crisis de servicio/operación)"
    if var is not None and var <= -10:
        return "quiebra", f"el último periodo completo cayó {P(abs(var))}"
    if var is not None and var < 0 or facts["calidad"]["puntaje"] < 65:
        return "inopia", "los datos muestran caída reciente o baja confiabilidad, típico de una crisis de caja"
    return "inopia", "no hay una señal dominante; se usa un escenario de liquidez por defecto"


def build_ctx(run, esc_key: str, rol: str) -> dict:
    f = run.facts
    m = f.get("medida_principal")
    ni = next((n for n in f["numericas"] if n["columna"] == m), None) if m else None
    it = next((i for i in f["interacciones"] if i["medida"] == m), None) if m else None
    t = (f.get("tiempo") or [None])[0]
    tx = f["texto"][0] if f.get("texto") else None
    sc = ESCENARIOS[esc_key]
    ctx = {
        "rol": rol, "escenario": esc_key, "choque": sc["choque"], "horizonte": sc["horizonte"], "filas": f["resumen"]["filas"],
        "dominio": (run.outputs.get("interprete") or {}).get("dominio_inferido", {}).get("dominio") or infer_domain(f, run.schema)["dominio"],
        "m": h(m) if m else "el volumen de registros", "tiene_medida": bool(m), "media": ni["media"] if ni else None, "suma": ni["suma"] if ni else None,
        "dim": h(it["dimension"]) if it else None, "agg": it["agregacion"] if it else None,
        "lider": it["grupos"][0]["categoria"] if it else None, "lider_pct": it["grupos"][0].get("pct_total") if it else None,
        "lider_val": (it["grupos"][0]["suma"] if it and it["agregacion"] == "suma" else it["grupos"][0]["media"]) if it else None,
        "peor": it["peor"]["categoria"] if it else None,
        "var": t["variacion_ultimo_vs_previo_pct"] if t and t.get("variacion_confiable") else None,
        "calidad": f["calidad"]["puntaje"], "veredicto": f["calidad"]["veredicto"],
        "pct_neg": tx["sentimiento"]["pct_negativo"] if tx else None, "tema": tx["temas"][0]["tema"] if tx and tx["temas"] else None,
        "anom": f["anomalias"][0] if f.get("anomalias") else None,
    }
    return ctx


def build_context_block(ctx: dict, razon_auto: str, esc_key: str) -> dict:
    sc, rol = ESCENARIOS[esc_key], ctx["rol"]
    lvl = NIVELES[rol]
    base = {"inopia": f"La empresa ({ctx['dominio']}) atraviesa una crisis de liquidez: la caja alcanza para pocas semanas. En este ejercicio se asume que {ctx['m']} cae {ctx['choque']}% durante los próximos {ctx['horizonte']} meses.",
            "quiebra": f"La empresa ({ctx['dominio']}) está al borde de la quiebra: las obligaciones superan la capacidad de pago y la dirección exige respuestas en semanas. Se asume que {ctx['m']} cae {ctx['choque']}% en los próximos {ctx['horizonte']} meses.",
            "operativa": f"La empresa ({ctx['dominio']}) enfrenta una crisis operativa crítica: un proceso clave se deteriora y la capacidad efectiva cae {ctx['choque']}% durante el próximo mes, con clientes y usuarios esperando."}[esc_key]
    datos = [f"{N(ctx['filas'])} registros reales analizados (dominio: {ctx['dominio']})"]
    if ctx["tiene_medida"]:
        datos.append(f"Medida principal: {ctx['m']}")
    if ctx["lider"] is not None:
        datos.append(f"En {ctx['dim']}, «{ctx['lider']}» lidera {ctx['m']}" + (f" con {P(ctx['lider_pct'])} del total" if ctx["lider_pct"] is not None else f" ({N(ctx['lider_val'])})"))
    if ctx["var"] is not None:
        datos.append(f"Variación del último periodo completo: {P(ctx['var'])}")
    datos.append(f"Calidad de los datos: {ctx['calidad']}/100")
    if ctx["pct_neg"] is not None:
        datos.append(f"Mensajes negativos de usuarios: {P(ctx['pct_neg'])}" + (f" (tema principal: {ctx['tema']})" if ctx["tema"] else ""))
    return {"titulo": sc["titulo"], "narrativa": base + f" Tu rol en este ejercicio: {rol}, es decir, {lvl['alcance']}. Los datos reales cargados son el punto de partida; el resto es un supuesto del ejercicio.",
            "datos_clave": datos, "supuestos": [f"El choque de {ctx['choque']}% en {ctx['horizonte']} mes(es) es HIPOTÉTICO (supuesto del ejercicio).", "Las cifras de «datos clave» provienen de tus datos reales.",
                                                "No se conocen costos, caja ni nombres reales: decide con la información disponible y pide la que falte.", f"Escenario: {sc['nombre']} ({razon_auto})."],
            "escenario": esc_key, "rol": rol}


# ============================================================================================== banco de preguntas
def _situaciones(c: dict) -> list[dict]:
    m, ch, hz = c["m"], c["choque"], c["horizonte"]
    S = []
    S.append({"id": "caida", "comp": "Gestión del riesgo", "enun": f"Se asume que {m} cae {ch}% en los próximos {hz} mes(es). Eres de los primeros en ver la señal en los reportes. ¿Qué haces primero?",
              "op": {"escalar": "Documentar la señal con las cifras del reporte y avisar de inmediato a mi jefe directo con la evidencia.",
                     "analizar": "Preparar un análisis de causas por segmento y periodo para presentarlo a quien decide.",
                     "coordinar": "Reunir al equipo, asignar responsables por frente y fijar un control semanal mientras se escala el diagnóstico.",
                     "decidir": "Definir un plan de contingencia con prioridades, presupuesto máximo, responsables y criterio de reversión, y aprobarlo.",
                     "riesgosa": "Recortar el gasto de todas las áreas de inmediato, en la misma proporción, sin analizar su efecto.",
                     "inaccion": "Esperar al próximo cierre para ver si la caída se corrige sola."}})
    if c["lider"] is not None:
        pct = f"{P(c['lider_pct'])} de {m}" if c["lider_pct"] is not None else f"el mayor valor de {m}"
        S.append({"id": "concentracion", "comp": "Priorización de recursos", "enun": f"En {c['dim']}, «{c['lider']}» concentra {pct}. En plena crisis, ¿cómo abordas esa dependencia?",
                  "op": {"escalar": f"Señalar el riesgo de dependencia con la cifra a mi jefe y pedir una definición sobre cómo proteger a «{c['lider']}».",
                         "analizar": f"Calcular cuánto se perdería si «{c['lider']}» baja y preparar escenarios para quien decide.",
                         "coordinar": f"Asignar un responsable que proteja a «{c['lider']}» y otro que desarrolle las categorías rezagadas, con seguimiento semanal.",
                         "decidir": f"Proteger a «{c['lider']}» con recursos prioritarios y aprobar en paralelo un plan acotado para diversificar, con hitos medibles.",
                         "riesgosa": f"Abandonar a «{c['lider']}» y mover todos los recursos a las categorías pequeñas.",
                         "inaccion": "No hacer nada: si siempre ha funcionado, seguirá funcionando."}})
    S.append({"id": "calidad", "comp": "Diagnóstico con datos", "enun": f"El puntaje de calidad de los datos es {c['calidad']}/100 y hay que informar a la dirección esta semana. ¿Qué haces?",
              "op": {"escalar": "Informar a mi jefe qué columnas tienen vacíos y qué conclusiones no son confiables, con evidencia.",
                     "analizar": "Documentar los vacíos y repetir los cálculos reportando N/A en lo que no se pueda sustentar.",
                     "coordinar": "Pedir a cada responsable de captura que corrija su fuente y fijar una fecha de reentrega antes de la reunión.",
                     "decidir": "Condicionar las decisiones irreversibles a un umbral mínimo de calidad y autorizar la corrección de captura en origen.",
                     "riesgosa": "Rellenar los vacíos con promedios para que los reportes se vean completos.",
                     "inaccion": "Presentar las cifras tal cual, sin advertir nada."}})
    if c["pct_neg"] is not None:
        S.append({"id": "reclamos", "comp": "Comunicación y escalamiento", "enun": f"El {P(c['pct_neg'])} de los mensajes de los usuarios es negativo" + (f" y el tema más frecuente es «{c['tema']}»" if c["tema"] else "") + ". ¿Cómo respondes?",
                  "op": {"escalar": "Compartir ejemplos representativos y el porcentaje con mi jefe para que se priorice el tema dominante.",
                         "analizar": "Clasificar los mensajes por tema y área y preparar un resumen con frecuencias.",
                         "coordinar": "Asignar un responsable por tema, definir tiempos de respuesta comprometidos y revisar avances cada semana.",
                         "decidir": "Aprobar un plan de recuperación del servicio con metas de tiempo, responsables y comunicación pública de compromisos.",
                         "riesgosa": "Responder a todos con mensajes automáticos sin resolver las causas.",
                         "inaccion": "Considerar que son casos aislados y no actuar."}})
    elif c["anom"]:
        a = c["anom"]
        S.append({"id": "anomalia", "comp": "Diagnóstico con datos", "enun": f"Aparece un valor atípico en {h(a['columna'])} ({N(a['valor'])}) asociado a «{a['id']}». ¿Qué haces?",
                  "op": {"escalar": "Reportar el registro y su identificador a mi jefe para que se verifique con la fuente.",
                         "analizar": "Compararlo con registros similares y documentar si parece un error de captura o un evento real.",
                         "coordinar": "Pedir al área dueña del dato que valide el registro y fijar fecha de respuesta.",
                         "decidir": "Definir una regla de validación para que los valores extremos se revisen antes de entrar a los reportes de dirección.",
                         "riesgosa": "Eliminar el registro sin consultarlo.",
                         "inaccion": "Ignorarlo: un solo dato no importa."}})
    S.append({"id": "comunicacion", "comp": "Comunicación y escalamiento", "enun": "El equipo percibe la crisis y empiezan a circular rumores. ¿Cómo manejas la comunicación?",
              "op": {"escalar": "Contar a mi jefe qué rumores circulan y pedir lineamientos oficiales antes de hablar.",
                     "analizar": "Recopilar los hechos verificados (cifras reales) para que quien comunique tenga información precisa.",
                     "coordinar": "Reunir a mi equipo, explicar lo que sé con datos, lo que no sé y los próximos pasos, y recoger inquietudes.",
                     "decidir": "Definir el mensaje oficial (situación, medidas, lo que sigue y cuándo se informará de nuevo) y comunicarlo a todos los niveles.",
                     "riesgosa": "Negar que exista una crisis para evitar el pánico.",
                     "inaccion": "No decir nada hasta que la situación se resuelva."}})
    S.append({"id": "prioridad", "comp": "Priorización de recursos", "enun": "Los recursos alcanzan solo para sostener una de las iniciativas en curso. ¿Cómo decides cuál se mantiene?",
              "op": {"escalar": "Listar las iniciativas con su impacto y pedir a mi jefe el criterio de priorización.",
                     "analizar": f"Construir una matriz de impacto sobre {m}, costo y urgencia para cada iniciativa.",
                     "coordinar": "Reunir a los responsables, aplicar la matriz de impacto y acordar cuál se sostiene y cuál se pausa.",
                     "decidir": f"Elegir según impacto en {m}, costo y reversibilidad, pausar las demás con fecha de revisión y comunicarlo.",
                     "riesgosa": "Sostener todas a medias.",
                     "inaccion": "Dejar que cada área decida por su cuenta."}})
    if c["escenario"] == "operativa":
        S.append({"id": "parada", "comp": "Coordinación y ejecución", "enun": "Un proceso crítico se detiene y hay clientes esperando. ¿Qué haces?",
                  "op": {"escalar": "Reportar de inmediato la parada, su hora de inicio y los clientes afectados a mi jefe.",
                         "analizar": "Identificar el punto exacto de falla y estimar el tiempo de recuperación para informar a quien decide.",
                         "coordinar": "Organizar turnos de respuesta, asignar quién repara, quién informa a clientes y fijar un punto de control cada hora.",
                         "decidir": "Autorizar recursos de emergencia (personal o proveedor externo) con un tope de costo y un plan de comunicación a clientes.",
                         "riesgosa": "Reiniciar todo el proceso sin diagnosticar la causa.",
                         "inaccion": "Esperar a que el sistema se recupere por sí solo."}})
    else:
        S.append({"id": "liquidez", "comp": "Gestión del riesgo", "enun": "La caja alcanza para pocas semanas y hay pagos pendientes. ¿Qué haces?",
                  "op": {"escalar": "Reportar a mi jefe el calendario de pagos vencidos y su monto de inmediato.",
                         "analizar": "Elaborar un flujo de caja semanal con pagos obligatorios, aplazables y de mayor riesgo.",
                         "coordinar": "Coordinar con compras y cartera el orden de pagos y la gestión de cobros, con revisión semanal.",
                         "decidir": "Priorizar pagos críticos, negociar plazos con proveedores y aprobar un tope de gasto discrecional hasta recuperar la caja.",
                         "riesgosa": "Pagar primero a quien más presione y aplazar el resto sin avisar.",
                         "inaccion": "Esperar a que entren ingresos para decidir."}})
    return S


def _mc(c: dict, sit: dict, rol: str, rng: random.Random) -> dict:
    sc = ALCANCE_SCORE[rol]
    # 4 opciones graduadas por rol: la ideal, una parcial, una que excede o sub-aprovecha el alcance, y una impulsiva/de inacción
    base = {"Auxiliar": ["escalar", "analizar", "decidir"], "Asistente": ["analizar", "escalar", "decidir"],
            "Supervisor": ["coordinar", "analizar", "decidir"], "Gerente": ["decidir", "coordinar", "analizar"]}[rol]
    chosen = base + [rng.choice(["riesgosa", "inaccion"])]
    rng.shuffle(chosen)
    ids = "ABCD"
    opciones = [{"id": ids[i], "texto": sit["op"][a]} for i, a in enumerate(chosen)]
    puntajes = {ids[i]: sc[a] for i, a in enumerate(chosen)}
    best = max(puntajes, key=puntajes.get)
    expl = {}
    for i, a in enumerate(chosen):
        s = sc[a]
        pref = ("Es la respuesta más adecuada para un " + rol if s == 1.0 else "Es parcialmente adecuada para un " + rol if s > 0 else "Es poco adecuada para un " + rol)
        extra = "" if s > 0 or a in ("riesgosa", "inaccion") else " Excede tu alcance: corresponde a un nivel superior."
        expl[ids[i]] = f"{pref}: {_RAZON[a]}.{extra}"
    return {"formato": "opcion_multiple", "competencia": sit["comp"], "tipo_eval": "decision", "enunciado": sit["enun"], "contenido": {"opciones": opciones},
            "clave": {"mejor": best, "puntajes": puntajes, "explicaciones": expl}, "explicacion": f"Para un {rol}, lo ideal es: {sit['op'][max(chosen, key=lambda a: sc[a])]}"}


def _vf_bank(c: dict, rol: str, rng: random.Random) -> list[dict]:
    B = []

    def add(afirm, verdad, comp, expl, roles=None, tipo="conocimiento"):
        if roles is None or rol in roles:
            B.append({"formato": "verdadero_falso", "competencia": comp, "tipo_eval": tipo, "enunciado": "Indica si la afirmación es verdadera o falsa.", "contenido": {"afirmacion": afirm}, "clave": {"respuesta": verdad}, "explicacion": expl})
    if c["lider"] is not None and c["peor"] is not None and c["lider"] != c["peor"]:
        what = "mayor aporte a" if c["agg"] == "suma" else "mayor promedio de"
        if rng.random() < 0.5:
            add(f"«{c['lider']}» es la categoría de {c['dim']} con {what} {c['m']}.", True, "Diagnóstico con datos", f"Verdadero: en los datos, «{c['lider']}» lidera {c['m']} por {c['dim']}.")
        else:
            add(f"«{c['peor']}» es la categoría de {c['dim']} con {what} {c['m']}.", False, "Diagnóstico con datos", f"Falso: quien lidera es «{c['lider']}»; «{c['peor']}» es el extremo opuesto.")
    add("La calidad de los datos cargados es alta (puntaje de 85/100 o más).", c["calidad"] >= 85, "Diagnóstico con datos", f"El puntaje real es {c['calidad']}/100 ({c['veredicto']}).")
    if c["var"] is not None:
        sube = c["var"] > 0
        add(f"En el último periodo completo, {c['m']} {'bajó' if sube else 'subió'} frente al periodo previo.", False, "Diagnóstico con datos", f"Falso: la variación real fue {P(c['var'])}.") if rng.random() < 0.5 else \
            add(f"En el último periodo completo, {c['m']} {'subió' if sube else 'bajó'} frente al periodo previo.", True, "Diagnóstico con datos", f"Verdadero: la variación real fue {P(c['var'])}.")
    if c["pct_neg"] is not None:
        add("Más de la mitad de los mensajes de texto de los usuarios es negativa.", c["pct_neg"] > 50, "Diagnóstico con datos", f"El porcentaje real de mensajes negativos es {P(c['pct_neg'])}.")
    add("En una crisis conviene decidir lo más rápido posible, aunque no se verifiquen los datos.", False, "Gestión del riesgo", "Falso: la urgencia degrada la calidad de la decisión; verifica lo mínimo necesario y decide con un criterio de reversión.")
    add("Una correlación entre dos indicadores demuestra que uno causa al otro.", False, "Diagnóstico con datos", "Falso: una asociación no prueba causalidad; puede haber un tercer factor.")
    add("Comunicar con transparencia lo que se sabe y lo que no se sabe reduce los rumores.", True, "Comunicación y escalamiento", "Verdadero: la transparencia con límites claros genera confianza.")
    add("Los valores faltantes deben rellenarse con promedios para que los reportes sean completos.", False, "Diagnóstico con datos", "Falso: los faltantes se reportan como N/A; imputar sin evidencia inventa información.")
    add("Un piloto acotado con una métrica de éxito definida reduce el riesgo de una decisión difícil de revertir.", True, "Gestión del riesgo", "Verdadero: permite aprender barato antes de escalar.", tipo="decision")
    add("Lo ya invertido en un proyecto debe pesar más que los beneficios futuros al decidir si se continúa.", False, "Visión estratégica", "Falso: es el sesgo del costo hundido; solo importan costos y beneficios futuros.")
    add("Fijar de antemano un criterio de reversión (cuándo dar marcha atrás) es parte de una buena decisión.", True, "Gestión del riesgo", "Verdadero: evita persistir en una decisión que ya no funciona.", tipo="decision")
    add("Ante una caída de ingresos, recortar todas las áreas en la misma proporción es siempre la mejor medida.", False, "Priorización de recursos", "Falso: conviene proteger lo que sostiene el ingreso y priorizar con criterios.", tipo="decision")
    add("Si detecto una anomalía que excede mi autoridad, lo correcto es corregirla en silencio para no preocupar a nadie.", False, "Comunicación y escalamiento", "Falso: se escala con evidencia a quien tiene autoridad.", roles=("Auxiliar", "Asistente"), tipo="decision")
    add("Delegar significa asignar responsable, plazo y criterio de éxito, y hacer seguimiento.", True, "Coordinación y ejecución", "Verdadero: sin esos tres elementos no hay delegación, hay esperanza.", roles=("Supervisor", "Gerente"))
    add("Un gerente debe delegar por completo la comunicación de la crisis para concentrarse solo en los números.", False, "Visión estratégica", "Falso: la dirección de la crisis y su comunicación son indelegables.", roles=("Gerente",), tipo="decision")
    add("Un supervisor responde por convertir las decisiones de la dirección en acciones coordinadas del equipo.", True, "Coordinación y ejecución", "Verdadero: ese es su alcance principal.", roles=("Supervisor",))
    add("Un asistente debe aprobar por sí mismo el recorte de presupuesto de otra área si el análisis lo justifica.", False, "Priorización de recursos", "Falso: el asistente prepara el análisis; la aprobación corresponde a quien tiene la autoridad.", roles=("Asistente",), tipo="decision")
    rng.shuffle(B)
    return B


def _match_bank(c: dict, rng: random.Random) -> list[dict]:
    items = []
    if c["lider"] is not None:
        pct = f" ({P(c['lider_pct'])} de {c['m']})" if c["lider_pct"] is not None else ""
        items.append((f"Dependencia de «{c['lider']}»{pct}", "Proteger al segmento líder y desarrollar en paralelo los rezagados con hitos medibles"))
    if c["calidad"] < 85:
        items.append((f"Datos con vacíos (calidad {c['calidad']}/100)", "Corregir la captura en origen y reportar N/A en lugar de imputar"))
    else:
        items.append(("Decisiones tomadas sin métrica de seguimiento", "Definir una métrica de éxito, un plazo de revisión y un criterio de reversión"))
    items.append((f"Caída sostenida de {c['m']}", "Diagnosticar la causa raíz por segmento y probar un piloto de recuperación"))
    if c["pct_neg"] is not None:
        items.append((f"Insatisfacción en los mensajes" + (f" (tema «{c['tema']}»)" if c["tema"] else ""), "Asignar un responsable al tema dominante y comprometer tiempos de respuesta"))
    if c["anom"]:
        items.append(("Valores atípicos sin explicación", "Auditar los registros extremos con la fuente antes de usarlos en decisiones"))
    items.append(("Falta de liquidez", "Priorizar pagos críticos y negociar plazos con proveedores"))
    items.append(("Rumores y desconfianza del equipo", "Comunicar hechos verificados y los próximos pasos con regularidad"))
    out = []
    for k in range(4):
        sub = items[k:] + items[:k]
        sub = sub[:4] if len(items) >= 4 else sub
        if len(sub) < 3:
            break
        sub = sub[: rng.choice([3, 4]) if len(sub) >= 4 else 3]
        causas = [{"id": f"c{i + 1}", "texto": s[0]} for i, s in enumerate(sub)]
        sols = [{"id": f"s{i + 1}", "texto": s[1]} for i, s in enumerate(sub)]
        rng.shuffle(sols)
        txt2id = {s["texto"]: s["id"] for s in sols}
        out.append({"formato": "emparejamiento", "competencia": "Gestión del riesgo", "tipo_eval": "decision", "enunciado": "Empareja cada causa de la crisis con la solución más adecuada (usa el desplegable de cada causa).",
                    "contenido": {"causas": causas, "soluciones": sols}, "clave": {"correcto": {causas[i]["id"]: txt2id[sub[i][1]] for i in range(len(sub))}},
                    "explicacion": "Cada solución ataca la causa raíz de su problema: " + "; ".join(f"{s[0]} → {s[1]}" for s in sub) + "."})
    rng.shuffle(out)
    return out


def _comp_bank(c: dict, rol: str, rng: random.Random) -> list[dict]:
    def q(comp, tipo, enun, huecos, expl):
        return {"formato": "completar", "competencia": comp, "tipo_eval": tipo, "enunciado": enun, "contenido": {"huecos": [{"id": hh["id"], "antes": hh["antes"], "despues": hh["despues"], "opciones": hh["opciones"]} for hh in huecos]},
                "clave": {"huecos": {hh["id"]: hh["correcta"] for hh in huecos}}, "explicacion": expl}

    def hueco(hid, antes, despues, correcta, malas):
        malas = list(dict.fromkeys(m for m in malas if m != correcta))  # sin duplicados ni ecos de la correcta
        malas += [x for x in ("N/A", "No se puede determinar") if x not in malas and len(malas) < 2]
        ops = [correcta] + malas
        rng.shuffle(ops)
        return {"id": hid, "antes": antes, "despues": despues, "opciones": [{"id": f"{hid}{i + 1}", "texto": t} for i, t in enumerate(ops)], "correcta": f"{hid}{ops.index(correcta) + 1}"}
    B = []
    B.append(q("Gestión del riesgo", "decision", "Completa la frase seleccionando la opción correcta.",
               [hueco("h1", "Antes de recortar costos en una crisis de ingresos, lo primero es", ".", "diagnosticar la causa con datos", ["recortar a todas las áreas por igual", "esperar a que la situación mejore sola", "ocultar la situación al equipo"])],
               "Primero se diagnostica la causa con datos; recortar a ciegas puede destruir lo que sostiene el ingreso."))
    if c["lider"] is not None and c["lider_pct"] is not None:
        val, fm = c["lider_pct"], P
        B.append(q("Diagnóstico con datos", "conocimiento", "Completa la frase con la cifra correcta (según tus datos).",
                   [hueco("h1", f"En {c['dim']}, «{c['lider']}» aporta", f"de {c['m']}.", fm(val), [fm(round(val * 0.55, 1)), fm(round(min(val * 1.5, 99.0), 1)), fm(round(val * 0.3, 1))])], f"La cifra real es {P(val)}."))
    elif c["media"] is not None:
        val = c["media"]
        B.append(q("Diagnóstico con datos", "conocimiento", "Completa la frase con la cifra correcta (según tus datos).",
                   [hueco("h1", f"En promedio, {c['m']} es", ".", N(val), [N(round(val * 0.6, 2)), N(round(val * 1.4, 2)), N(round(val * 2.1, 2))])], f"El promedio real de {c['m']} es {N(val)}."))
    r = NIVELES[rol]
    otras = [NIVELES[x]["responsabilidad"] for x in ROLES if x != rol]
    comp_by_role = {"Auxiliar": "Comunicación y escalamiento", "Asistente": "Diagnóstico con datos", "Supervisor": "Coordinación y ejecución", "Gerente": "Visión estratégica"}
    B.append(q(comp_by_role[rol], "decision", "Completa la frase pensando en tu rol en esta crisis.",
               [hueco("h1", f"Como {rol}, mi responsabilidad principal en esta crisis es", ".", r["responsabilidad"], otras)],
               f"El alcance de un {rol} es: {r['alcance']}."))
    B.append(q("Gestión del riesgo", "decision", "Completa la frase con las opciones desplegables.",
               [hueco("h1", "Una buena decisión de crisis define una métrica de éxito, un", "", "plazo de revisión", ["culpable", "premio"]),
                hueco("h2", "y un criterio de", "antes de ejecutar.", "reversión", ["castigo", "olvido"])],
               "La decisión se acompaña de una métrica de éxito, un plazo de revisión y un criterio de reversión."))
    rng.shuffle(B)
    return B


def generate_offline(ctx: dict, rol: str, dinamica: str, n: int, rng: random.Random) -> list[dict]:
    sits = _situaciones(ctx)
    rng.shuffle(sits)
    pools = {"opcion_multiple": [_mc(ctx, s, rol, rng) for s in sits], "verdadero_falso": _vf_bank(ctx, rol, rng), "emparejamiento": _match_bank(ctx, rng), "completar": _comp_bank(ctx, rol, rng)}
    if dinamica in FORMATOS:
        order = [dinamica] * n
        n = min(n, len(pools[dinamica]))
        order = order[:n]
    else:
        pattern = ["opcion_multiple", "verdadero_falso", "emparejamiento", "completar", "opcion_multiple", "verdadero_falso", "completar", "opcion_multiple", "verdadero_falso", "emparejamiento"]
        order = pattern[:n]
    out, used = [], {k: 0 for k in pools}
    for fmt in order:
        pool = pools[fmt]
        if used[fmt] >= len(pool):  # banco agotado: se completa con otro formato disponible
            fmt = next((k for k in ("opcion_multiple", "verdadero_falso", "completar", "emparejamiento") if used[k] < len(pools[k])), None)
            if fmt is None:
                break
        q = pools[fmt][used[fmt]]
        used[fmt] += 1
        out.append(q)
    for i, q in enumerate(out, 1):
        q["id"] = f"q{i}"
    return out


# ============================================================================================== validación (salida del LLM)
def valid_question(q: dict) -> bool:
    try:
        if q["formato"] not in FORMATOS or q["competencia"] not in COMPETENCIAS or q["tipo_eval"] not in ("decision", "conocimiento"):
            return False
        c, k = q["contenido"], q["clave"]
        if q["formato"] == "opcion_multiple":
            ids = [o["id"] for o in c["opciones"]]
            return ids == ["A", "B", "C", "D"] and k["mejor"] in ids and set(k["puntajes"]) == set(ids) and all(0 <= float(v) <= 1 for v in k["puntajes"].values()) and float(k["puntajes"][k["mejor"]]) == max(float(v) for v in k["puntajes"].values())
        if q["formato"] == "verdadero_falso":
            return isinstance(k["respuesta"], bool) and bool(str(c["afirmacion"]).strip())
        if q["formato"] == "emparejamiento":
            cs, ss = [x["id"] for x in c["causas"]], [x["id"] for x in c["soluciones"]]
            return 3 <= len(cs) <= 4 and len(cs) == len(ss) and set(k["correcto"]) == set(cs) and set(k["correcto"].values()) == set(ss)
        if q["formato"] == "completar":
            hs = c["huecos"]
            return 1 <= len(hs) <= 2 and all(hh["id"] in k["huecos"] and k["huecos"][hh["id"]] in [o["id"] for o in hh["opciones"]] and 2 <= len(hh["opciones"]) <= 5 for hh in hs)
    except Exception:  # noqa: BLE001
        return False
    return False


def post_simulador(out: dict, payload: dict, meta: dict, fallback) -> dict:
    keep = []
    for q in out.get("preguntas", []):
        if valid_question(q) and (payload["dinamica"] == "mixta" or q["formato"] == payload["dinamica"]):
            keep.append(q)
        else:
            meta["correcciones_guardrail"].append(f"Pregunta '{q.get('id')}' descartada: estructura, clave o formato inválidos.")
    want = payload["n_preguntas"]
    if len(keep) < want:
        extra = [q for q in fallback() if q["formato"] in ([payload["dinamica"]] if payload["dinamica"] in FORMATOS else list(FORMATOS))]
        have = {q["enunciado"] for q in keep}
        for q in extra:
            if len(keep) >= want:
                break
            if q["enunciado"] not in have:
                keep.append(q)
                meta["correcciones_guardrail"].append("Pregunta de respaldo añadida para completar la simulación.")
    keep = keep[:want]
    for i, q in enumerate(keep, 1):
        q["id"] = f"q{i}"
    out["preguntas"] = keep
    wl = build_whitelist(payload["datos"], payload["parametros"])
    found: list[str] = []
    out["contexto"] = scrub_numbers(out["contexto"], wl, found)
    meta["cifras_no_verificadas"] += found
    return out


# ============================================================================================== API
def generate(llm: LLM, run, run_id: str, rol: str, escenario: str = "auto", dinamica: str = "mixta", n: int = 8, seed: int | None = None) -> tuple[Simulation, dict]:
    if rol not in NIVELES:
        raise ValueError(f"Rol no válido: {rol}. Opciones: {', '.join(ROLES)}.")
    if escenario not in ESCENARIOS:
        raise ValueError(f"Escenario no válido: {escenario}.")
    if dinamica != "mixta" and dinamica not in FORMATOS:
        raise ValueError(f"Dinámica no válida: {dinamica}.")
    n = max(3, min(int(n), 12))
    esc_key, razon = pick_scenario(run.facts, escenario)
    ctx = build_ctx(run, esc_key, rol)
    rng = random.Random(seed if seed is not None else secrets.randbits(32))
    contexto = build_context_block(ctx, razon, esc_key)

    def offline_fn(p):
        return {"contexto": contexto, "preguntas": generate_offline(ctx, rol, dinamica, n, random.Random(rng.random()))}

    def fallback():
        return generate_offline(ctx, rol, dinamica, 12, random.Random(rng.random()))

    payload = {"rol": rol, "nivel": NIVELES[rol], "escenario": {"clave": esc_key, **{k: v for k, v in ESCENARIOS[esc_key].items() if k in ("nombre", "descripcion", "choque", "horizonte")}, "razon": razon},
               "dinamica": dinamica, "n_preguntas": n, "competencias": COMPETENCIAS, "datos": {k: v for k, v in ctx.items() if k not in ("rol",)},
               "parametros": {"choque_pct": ctx["choque"], "horizonte_meses": ctx["horizonte"]}, "contexto_base": contexto}
    agent = Agent("simulador", offline_fn, lambda o, p, m: post_simulador(o, p, m, fallback))
    out, meta = agent.run(llm, payload)
    for q in out["preguntas"]:
        q.setdefault("explicacion", "")
    sim = Simulation(sim_id=secrets.token_hex(5), run_id=run_id, rol=rol, escenario=esc_key, dinamica=dinamica, contexto=out["contexto"], preguntas=out["preguntas"], motor=meta["motor"])
    return sim, meta


def public_view(sim: Simulation) -> dict:
    """Lo que ve el cliente: enunciados y opciones, SIN clave ni explicaciones."""
    return {"sim_id": sim.sim_id, "rol": sim.rol, "escenario": sim.escenario, "dinamica": sim.dinamica, "motor": sim.motor, "contexto": sim.contexto,
            "preguntas": [{k: q[k] for k in ("id", "formato", "competencia", "tipo_eval", "enunciado", "contenido")} for q in sim.preguntas]}


def _answer_text(q: dict, ans) -> str:
    c = q["contenido"]
    if ans in (None, "", {}):
        return "(sin responder)"
    f = q["formato"]
    if f == "opcion_multiple":
        o = next((x for x in c["opciones"] if x["id"] == ans), None)
        return f"{ans}) {o['texto']}" if o else "(respuesta inválida)"
    if f == "verdadero_falso":
        return "Verdadero" if ans is True else "Falso" if ans is False else "(sin responder)"
    if f == "emparejamiento":
        sols = {s["id"]: s["texto"] for s in c["soluciones"]}
        return "; ".join(f"{x['texto']} → {sols.get(ans.get(x['id']), '(vacío)')}" for x in c["causas"])
    if f == "completar":
        return "; ".join(f"{hh['antes']} [{next((o['texto'] for o in hh['opciones'] if o['id'] == ans.get(hh['id'])), '(vacío)')}] {hh['despues']}".strip() for hh in c["huecos"])
    return str(ans)


def _correct_text(q: dict) -> str:
    c, k, f = q["contenido"], q["clave"], q["formato"]
    if f == "opcion_multiple":
        return _answer_text(q, k["mejor"])
    if f == "verdadero_falso":
        return "Verdadero" if k["respuesta"] else "Falso"
    if f == "emparejamiento":
        return _answer_text(q, k["correcto"])
    return _answer_text(q, k["huecos"])


def score_question(q: dict, ans) -> float:
    k, f = q["clave"], q["formato"]
    try:
        if f == "opcion_multiple":
            return float(k["puntajes"].get(ans, 0.0)) if isinstance(ans, str) else 0.0
        if f == "verdadero_falso":
            if isinstance(ans, str):
                ans = {"true": True, "verdadero": True, "v": True, "false": False, "falso": False, "f": False}.get(ans.lower())
            return 1.0 if isinstance(ans, bool) and ans == k["respuesta"] else 0.0
        if f == "emparejamiento":
            if not isinstance(ans, dict):
                return 0.0
            return sum(1 for cid, sid in k["correcto"].items() if ans.get(cid) == sid) / len(k["correcto"])
        if f == "completar":
            if not isinstance(ans, dict):
                return 0.0
            return sum(1 for hid, oid in k["huecos"].items() if ans.get(hid) == oid) / len(k["huecos"])
    except Exception:  # noqa: BLE001
        return 0.0
    return 0.0


def _nivel(p: float) -> str:
    return "Sobresaliente" if p >= 85 else "Satisfactorio" if p >= 70 else "En desarrollo" if p >= 50 else "Requiere refuerzo"


def grade(sim: Simulation, respuestas: dict) -> dict:
    """Reporte de Desempeño Final: puntaje, % de éxito de decisiones, diagnóstico por rol, competencias y recomendaciones."""
    respuestas = respuestas or {}
    rol, lvl = sim.rol, NIVELES[sim.rol]
    rev, tot, dec, dec_opt, dec_n, sin = [], 0.0, 0.0, 0, 0, 0
    comp: dict[str, list[float]] = {}
    for q in sim.preguntas:
        ans = respuestas.get(q["id"])
        s = score_question(q, ans)
        answered = ans not in (None, "", {}) and (not isinstance(ans, dict) or any(v for v in ans.values()))
        sin += 0 if answered else 1
        tot += s
        comp.setdefault(q["competencia"], []).append(s)
        if q["tipo_eval"] == "decision":
            dec += s
            dec_n += 1
            dec_opt += 1 if s >= 0.999 else 0
        rev.append({"id": q["id"], "formato": q["formato"], "competencia": q["competencia"], "enunciado": q["enunciado"], "tu_respuesta": _answer_text(q, ans), "respuesta_correcta": _correct_text(q),
                    "puntaje_pct": round(100 * s), "estado": "correcta" if s >= 0.999 else "parcial" if s > 0 else "incorrecta", "explicacion": _feedback(q, ans)})
    n = max(len(sim.preguntas), 1)
    puntaje = round(100 * tot / n, 1)
    exito = round(100 * dec / dec_n, 1) if dec_n else None
    comps = []
    for nombre in COMPETENCIAS:
        if nombre in comp:
            p = round(100 * sum(comp[nombre]) / len(comp[nombre]), 1)
            comps.append({"nombre": nombre, "pct": p, "nivel": "Alto" if p >= 75 else "Medio" if p >= 50 else "Bajo", "importancia_rol": lvl["importancia"][nombre], "preguntas": len(comp[nombre])})
    ev = sorted(comps, key=lambda x: (-x["pct"], x["nombre"]))
    imp = {"alta": 0, "media": 1, "baja": 2}
    fort = [c for c in ev if c["pct"] >= 75][:3]
    debil = sorted([c for c in comps if c["pct"] < 75], key=lambda x: (imp[x["importancia_rol"]], x["pct"]))
    nivel = _nivel(puntaje)
    diag = f"Como {rol} ({lvl['alcance']}), tu desempeño global fue {nivel.lower()} ({puntaje}%)."
    if fort:
        diag += " Tus fortalezas: " + ", ".join(f"{c['nombre']} ({c['pct']}%)" for c in fort) + "."
    if debil:
        diag += " Prioridad de mejora para tu rol: " + ", ".join(f"{c['nombre']} ({c['pct']}%, importancia {c['importancia_rol']} para un {rol})" for c in debil[:2]) + "."
    if puntaje >= 85:
        listo = f"Listo/a para asumir responsabilidades de {lvl['siguiente']}." if lvl["siguiente"] else "Nivel sólido para dirigir una crisis; puedes mentorizar a otros niveles."
    elif puntaje >= 70:
        listo = f"Cumples lo esperado para el rol de {rol}; refuerza las competencias señaladas antes de pasar a un nivel superior."
    elif puntaje >= 50:
        listo = f"Estás en desarrollo para el rol de {rol}: practica los criterios de alcance y evidencia."
    else:
        listo = f"Se requiere refuerzo para el rol de {rol}: repasa el alcance del rol y repite la simulación."
    recs = [f"{c['nombre']}: {RECOMENDACIONES[c['nombre']][rol]}" for c in debil[:3]]
    if dec_n and dec_opt < dec_n / 2:
        recs.append(f"Solo {dec_opt} de {dec_n} decisiones fueron óptimas: antes de elegir, pregúntate qué corresponde a tu alcance como {rol} y qué evidencia sustenta cada opción.")
    if sin:
        recs.append(f"Dejaste {sin} pregunta(s) sin responder; en una crisis real no decidir también es una decisión.")
    if not recs:
        recs.append(f"Mantén el nivel y practica un escenario más exigente, asumiendo el rol de {lvl['siguiente'] or 'Gerente'}.")
    rep = {"sim_id": sim.sim_id, "rol": rol, "escenario": sim.escenario, "puntaje_pct": puntaje, "exito_decisiones_pct": exito, "decisiones_optimas": f"{dec_opt} de {dec_n}" if dec_n else "N/A",
           "nivel_desempeno": nivel, "diagnostico_rol": diag, "preparacion_para_el_rol": listo, "competencias": comps, "fortalezas": [c["nombre"] for c in fort], "recomendaciones": recs,
           "sin_responder": sin, "total_preguntas": len(sim.preguntas), "revision": rev,
           "nota": "" if dec_n else "No hubo preguntas de decisión en esta dinámica: el % de éxito de decisiones no aplica (N/A); usa la dinámica mixta para medirlo."}
    sim.resultado = rep
    return rep


def _feedback(q: dict, ans) -> str:
    if q["formato"] == "opcion_multiple" and isinstance(ans, str) and ans in q["clave"].get("explicaciones", {}):
        return q["clave"]["explicaciones"][ans] + " " + q.get("explicacion", "")
    return q.get("explicacion", "")
