# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Utilidades de texto: normalización, léxicos de sentimiento, temas y formateo numérico.

Todo el módulo es AGNÓSTICO al dominio: los léxicos son de lenguaje natural general (español),
no dependen de ningún dataset concreto.
"""
from __future__ import annotations

import math
import re
import unicodedata


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c))


def snake(s: str) -> str:
    s = strip_accents(str(s)).lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def norm_key(s: str) -> str:
    """Clave de comparación: minúsculas, sin tildes, sin signos en bordes, espacios colapsados."""
    s = strip_accents(str(s)).lower()
    s = re.sub(r"[\s_\-]+", " ", s).strip(" .,;:!¡?¿\"'()[]")
    return s


def norm_text(s: str) -> str:
    """Normaliza para buscar frases: sin tildes, minúsculas y SIN signos de puntuación (también internos)."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ]+", " ", strip_accents(str(s)).lower())).strip()


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9ñ]+", strip_accents(str(text)).lower())


STOPWORDS = set(
    """a al algo ante con contra cual cuando de del desde donde dos el ella ellos en entre era es esa ese eso esta
    estaba estan este esto estoy fue ha han hasta hay la las le les lo los me mi mis muy ni no nos nuestro o para pero
    por porque que quien se ser si sin sobre su sus te tengo tiene tienen todo todos tu un una uno unos y ya yo he
    hemos fui son sido esta estar como mas menos cada tambien solo pues asi aqui alli ahi entonces ademas the and of
    to in is it for on with was this that are be at or an by from as not have has""".split()
)

# --- Sentimiento (léxico general en español; prefijos de palabra, sin tildes) ---------------------
POS_STEMS = [
    "excelent", "gracias", "agradezc", "agradec", "bueno", "buena", "buen", "rapid", "amable", "felicit", "satisf",
    "solucion", "resuelt", "resolv", "eficien", "recomiend", "atent", "cordial", "perfect", "genial",
    "content", "feliz", "optim", "agil", "fantastic", "increible", "oportun", "puntual",
]  # 'mejor/mejorar' se excluye a propósito: aparece en sugerencias neutras ("publicar mejor la información")
POS_EXACT = {"util", "utiles", "claro", "clara", "cumplieron", "cumplio"}
NEG_STEMS = [
    "pesim", "terribl", "quej", "demor", "tard", "nunca", "error", "falla", "fallo", "problema", "molest",
    "inconform", "lent", "incumpl", "indebid", "danad", "dano", "defectuos", "cancel", "injust", "engan", "fraude",
    "inaceptab", "negligen", "espera", "grosero", "irrespet", "perdid", "abuso", "pesad", "horrible", "peor",
    "deficien", "reclam", "devol", "roto", "sucio", "ruido", "inseguro", "insatisf", "decepc", "frustr", "rechaz",
    "negad", "equivoc", "imposible", "ineficien", "desorden", "colaps",
    "retras", "incomplet", "perdio", "cobraron", "exijo", "reembols", "devuelt", "exig", "denunci", "vencid", "descortes", "faltante",
]
NEG_EXACT = {"mal", "malo", "mala", "malos", "malas", "malisimo", "caro", "cara", "caros", "caras"}
NEGATIONS = {"no", "nunca", "ni", "sin", "jamas", "tampoco"}


def sentiment(text: str) -> int:
    """Devuelve +1, 0 o -1 mediante léxico con manejo simple de negación."""
    toks = tokens(text)
    score = 0
    for i, t in enumerate(toks):
        pol = 0
        if t in POS_EXACT or any(t.startswith(s) for s in POS_STEMS):
            pol = 1
        elif t in NEG_EXACT or any(t.startswith(s) for s in NEG_STEMS):
            pol = -1
        if pol and i > 0 and toks[i - 1] in NEGATIONS and t not in ("nunca",):
            pol = -pol
        score += pol
    return (score > 0) - (score < 0)


THEMES = {
    "Tiempos de respuesta / demoras": ["demor", "tard", "lent", "espera", "plazo", "vencid", "sin respuesta", "pendiente", "retras", "atras", "dias"],
    "Cobros y facturación": ["cobro", "factura", "pago", "cargo", "tarifa", "precio", "reembols", "devoluc", "dinero", "costo", "caro", "descuento"],
    "Calidad del producto/servicio": ["calidad", "defect", "danad", "dano ", "roto", "falla", "fallo", "error", "mal estado", "no funciona", "garantia", "deficien"],
    "Atención y trato": ["atencion", "trato", "grosero", "amable", "asesor", "funcionario", "irrespet", "servicio al cliente", "personal", "cordial", "maltrato"],
    "Canales digitales / plataforma": ["pagina", "plataforma", "app", "aplicacion", "sistema", "web", "portal", "linea", "telefon", "correo", "chat", "internet", "clave"],
    "Entregas y logística": ["entrega", "envio", "pedido", "domicilio", "transporte", "despacho", "paquete", "guia"],
    "Infraestructura y seguridad": ["infraestructura", "via ", "obra", "seguridad", "ruido", "limpieza", "instalacion", "hueco", "alumbrado", "agua", "luz"],
    "Información y trámites": ["informacion", "tramite", "documento", "requisito", "certificado", "solicitud", "formulario", "radicado", "orientacion", "cita"],
}
_THEMES_N = {k: [strip_accents(s) for s in v] for k, v in THEMES.items()}


def themes_of(text: str) -> list[str]:
    t = strip_accents(str(text)).lower()
    return [k for k, stems in _THEMES_N.items() if any(s in t for s in stems)]


INTENT_STEMS = {
    "reclamo": ["reclam", "cobro indebido", "exijo", "reembols", "devoluc", "incumpl", "no me han devuelto"],
    "queja": ["queja", "inconform", "molest", "mal servicio", "grosero", "irrespet", "pesimo", "terrible", "insatisf"],
    "petición": ["solicito", "requiero", "necesito", "quisiera", "por favor", "informacion", "pido", "agradezco me"],
    "sugerencia": ["sugiero", "recomiendo", "propongo", "seria bueno", "deberian", "podrian"],
    "felicitación": ["felicit", "excelente", "muchas gracias", "quedo satisfech", "agradezco el"],
}


def intent_of(text: str) -> str:
    t = strip_accents(str(text)).lower()
    best, best_n = "otro", 0
    for k, stems in INTENT_STEMS.items():
        n = sum(1 for s in stems if strip_accents(s) in t)
        if n > best_n:
            best, best_n = k, n
    return best


# --- Formateo numérico (convención colombiana: 1.234.567,89) -----------------------------------
def fmt_num(x, dec: int | None = None) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "N/A"
    x = float(x)
    if dec is None:
        ax = abs(x)
        dec = 0 if ax >= 1000 or float(x).is_integer() else (1 if ax >= 100 else 2)
    s = f"{x:,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_pct(x, dec: int = 1) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "N/A"
    return fmt_num(x, dec) + "%"


def clip(s: str, n: int = 90) -> str:
    s = str(s).replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"
