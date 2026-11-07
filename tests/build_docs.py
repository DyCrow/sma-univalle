"""Construye el Expediente Técnico (Fase 5): docs/expediente_tecnico.md + .html con diagramas, catálogo de prompts y matriz de testeo.

Todo el contenido técnico (prompts, matriz, ejemplos de payloads) se extrae del código y de la última ejecución de pruebas:
el expediente nunca puede desincronizarse del sistema.
"""
from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DOCS = ROOT / "docs"

import markdown  # noqa: E402

from sma.branding import FIRMA_MD, WATERMARK_CSS, print_footer_html, watermark_html  # noqa: E402
from sma.llm import NullLLM  # noqa: E402
from sma.pipeline import MultiAgentSystem  # noqa: E402
from sma.prompts import PROMPTS, SCHEMAS, catalog_hash, render_system_prompt  # noqa: E402
from sma.report import advice_md  # noqa: E402


# ------------------------------------------------------------------ diagramas SVG
def box(x, y, w, h, title, lines=(), fill="#e8f4f1", stroke="#0f766e", dash=False, tcolor="#0b3d38"):
    d = ' stroke-dasharray="6 4"' if dash else ""
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.6"{d}/>'
    s += f'<text x="{x + w / 2}" y="{y + 20}" text-anchor="middle" font-size="13" font-weight="700" fill="{tcolor}">{title}</text>'
    for i, ln in enumerate(lines):
        s += f'<text x="{x + w / 2}" y="{y + 38 + i * 15}" text-anchor="middle" font-size="11" fill="#33413e">{ln}</text>'
    return s


def arrow(x1, y1, x2, y2, label="", color="#0f766e"):
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2" marker-end="url(#ar)"/>'
    if label:
        s += f'<text x="{(x1 + x2) / 2}" y="{(y1 + y2) / 2 - 6}" text-anchor="middle" font-size="10" fill="#5b6b67">{label}</text>'
    return s


DEFS = '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#0f766e"/></marker></defs>'


def svg_topologia() -> str:
    W, H = 1120, 615
    s = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Segoe UI,Roboto,sans-serif" role="img" aria-label="Topología de la red de agentes">{DEFS}<rect width="{W}" height="{H}" fill="#ffffff"/>'
    s += '<text x="20" y="28" font-size="16" font-weight="700" fill="#0b3d38">Topología de la red de agentes · flujo de payloads</text>'
    T, A = ("#f3f4f6", "#6b7280"), ("#e8f4f1", "#0f766e")
    s += box(20, 60, 150, 70, "Archivo de entrada", ["CSV · Excel · JSON", "cualquier estructura"], "#fff7ed", "#b45309", tcolor="#7c3a06")
    s += box(215, 60, 170, 70, "Ingesta + Percepción", ["encoding · delimitador · encabezado", "tipos · formatos · nulos"], *T, dash=True)
    s += box(430, 60, 190, 70, "AGENTE 1 · Auditor y Limpiador", ["valida/corrige esquema, normaliza", "problemas + veredicto de calidad"], *A)
    s += box(665, 60, 170, 70, "Cómputo estadístico", ["hechos exactos con ref:", "resúmenes · series · correlaciones"], *T, dash=True)
    s += box(880, 60, 220, 70, "AGENTE 2 · Analista Estadístico", ["selecciona variables clave,", "interacciones, tendencias, texto"], *A)
    s += arrow(170, 95, 215, 95) + arrow(385, 95, 430, 95) + arrow(620, 95, 665, 95) + arrow(835, 95, 880, 95)
    s += box(880, 200, 220, 70, "AGENTE 3 · Intérprete Contextual", ["infiere dominio, impacto,", "riesgos, oportunidades, N/A"], *A)
    s += box(430, 200, 380, 70, "AGENTE 4 · Generador de Informes", ["informe ejecutivo estructurado +", "directivas de visualización (gráficos SVG)"], *A)
    s += box(20, 200, 360, 70, "Entregable", ["Informe HTML/MD · gráficos · trazabilidad JSON · CSV limpio"], "#fff7ed", "#b45309", tcolor="#7c3a06")
    s += arrow(990, 130, 990, 200, "payload 2") + arrow(880, 235, 810, 235) + arrow(430, 235, 380, 235)
    # guardrails
    s += '<rect x="420" y="296" width="690" height="46" rx="10" fill="#fff1f2" stroke="#be123c" stroke-width="1.4" stroke-dasharray="5 4"/>'
    s += '<text x="765" y="316" text-anchor="middle" font-size="13" font-weight="700" fill="#9f1239">GUARDRAILS entre cada etapa</text>'
    s += '<text x="765" y="333" text-anchor="middle" font-size="10" fill="#33413e">esquema JSON · reintento con error · valores medidos autoritativos · refs verificables · cifras enmascaradas · respaldo</text>'
    # agente 5
    s += '<text x="20" y="338" font-size="14" font-weight="700" fill="#0b3d38">PLUS · Agente 5</text><text x="20" y="354" font-size="11" fill="#5b6b67">(conversacional, sobre el informe ya generado)</text>'
    s += box(20, 392, 230, 100, "Administrador/a", ["rol · pregunta · decisión", "historial de la conversación"], "#fff7ed", "#b45309", tcolor="#7c3a06")
    s += box(330, 392, 250, 100, "Señales verificables", ["entidades de los datos citadas", "cifras vs variabilidad real", "sesgos · lente por rol/dominio"], *T, dash=True)
    s += box(660, 392, 440, 100, "AGENTE 5 · Consejero Estratégico y Líder-Analista", ["cuestiona supuestos · evidencia a favor/en contra · pre-mortem", "alternativas · postura con condiciones · plan de liderazgo", "preguntas de vuelta · datos que faltan"], "#eef2ff", "#4338ca", tcolor="#312e81")
    s += arrow(250, 442, 330, 442) + arrow(580, 442, 660, 442)
    s += box(660, 508, 440, 90, "AGENTE 6 · Simulador de Crisis y Evaluación Directiva", ["rol (Auxiliar · Asistente · Supervisor · Gerente) + tipo de crisis", "preguntas: opción múltiple · V/F · emparejamiento · completar", "reporte final: puntaje, % de éxito, diagnóstico por rol"], "#fdf4ff", "#a21caf", tcolor="#701a75")
    s += '<path d="M135,492 L135,553 L660,553" fill="none" stroke="#a21caf" stroke-width="1.8" stroke-dasharray="4 3" marker-end="url(#ar)"/><text x="400" y="546" text-anchor="middle" font-size="10" fill="#a21caf">elige rol y dinámica → responde → recibe evaluación</text>'
    s += '<path d="M880,392 C880,352 135,352 135,392" fill="none" stroke="#4338ca" stroke-width="1.8" stroke-dasharray="4 3" marker-end="url(#ar)"/>'
    s += '<text x="700" y="380" text-anchor="middle" font-size="10" fill="#4338ca">memorando de decisión vuelve al administrador (diálogo)</text>'
    return s + "</svg>"


MERMAID_TOPO = """```mermaid
flowchart LR
  F[Archivo CSV/Excel/JSON] --> I[Ingesta + Percepción<br/>herramienta]
  I -->|esquema + muestra| A1[Agente 1<br/>Auditor y Limpiador]
  A1 -->|esquema final| H[Cómputo estadístico<br/>herramienta]
  H -->|hechos con ref| A2[Agente 2<br/>Analista Estadístico]
  A2 -->|análisis| A3[Agente 3<br/>Intérprete Contextual]
  A3 -->|hallazgos| A4[Agente 4<br/>Generador de Informes]
  A4 --> R[Informe HTML/MD + gráficos + trazabilidad]
  R --> A5[Agente 5 PLUS<br/>Consejero Estratégico]
  U[Administrador] <-->|rol, pregunta, decisión| A5
  R --> A6[Agente 6 PLUS<br/>Simulador de Crisis]
  U <-->|rol, respuestas interactivas, evaluación| A6
  G{{Guardrails: esquema, refs, cifras, respaldo}} -.-> A1 & A2 & A3 & A4 & A5 & A6
```"""

MERMAID_SEQ = """```mermaid
sequenceDiagram
  participant U as Administrador
  participant O as Orquestador
  participant T as Herramientas
  participant A as Agente (LLM o respaldo)
  participant G as Guardrails
  U->>O: sube archivo
  O->>T: ingesta, tipos, formatos, nulos
  T-->>O: esquema preliminar + calidad
  O->>A: payload (prompt estructurado + JSON)
  A-->>G: respuesta JSON
  G->>G: validar esquema / refs / cifras
  alt inválido
    G-->>A: errores → reintento (1)
    A-->>G: nueva respuesta
  end
  G-->>O: salida verificada (o respaldo determinista)
  O->>U: informe + trazabilidad
  U->>O: decisión o pregunta
  O->>A: payload del consejero (+ señales)
  A-->>U: memorando: cuestiona, alternativas, plan
```"""


def main():
    sysm = MultiAgentSystem(NullLLM())
    B = sysm.analyze_path(ROOT / "data" / "B_pqr_texto_libre.csv")
    A = sysm.analyze_path(ROOT / "data" / "A_ventas_transaccionales.csv")
    memo = sysm.advise(A, "Voy a cerrar la sucursal Occidente porque vende poco y estoy seguro de que no pasa nada.", "Gerente comercial", history=[])
    memo_pub = sysm.advise(sysm.analyze_path(ROOT / "data" / "E_indicadores_sociales.xlsx"), "Como secretario de planeación voy a priorizar la inversión en Cali porque tiene más población.", "", history=[])

    (DOCS / "diagrama_topologia.svg").write_text(svg_topologia(), encoding="utf-8")
    matriz = (DOCS / "matriz_auditoria.md").read_text(encoding="utf-8") if (DOCS / "matriz_auditoria.md").exists() else "_Ejecute `py run.py pruebas` para generar la matriz._"
    matriz = matriz.replace("# Matriz de Auditoría y Control de Testeo (Fase 4)", "").replace("\n## ", "\n### ")

    def j(o, n=1400):
        t = json.dumps(o, ensure_ascii=False, indent=1)
        return t if len(t) <= n else t[:n] + "\n…"

    cat = []
    for k, p in PROMPTS.items():
        rules = "\n".join(f"| {rid} | {orig} | {txt} |" for rid, orig, txt in p["restricciones"])
        cat.append(f"### {p['nombre']}\n\n**[ROL]** {p['rol']}\n\n**[CONTEXTO]** {p['contexto']}\n\n**[TAREA]** {p['tarea']}\n\n**[RESTRICCIONES]**\n\n| ID | Origen | Regla |\n|---|---|---|\n{rules}\n\n**[FORMATO DE SALIDA]** {p['formato']}\n\n<details><summary>Esquema JSON de validación</summary>\n\n```json\n{json.dumps(SCHEMAS[k], ensure_ascii=False, indent=1)}\n```\n</details>\n")

    import pandas as pd
    from sma.text_utils import sentiment
    raw = pd.read_csv(ROOT / "data" / "B_pqr_texto_libre.csv")
    labels = json.loads((ROOT / "data" / "B_etiquetas_reales.json").read_text())
    acc = sum(("neg" if sentiment(x) == -1 else "pos" if sentiment(x) == 1 else "neu") == y for x, y in zip(raw["descripcion"], labels)) / len(labels) * 100
    acc_txt = f"{acc:.1f}".replace(".", ",")
    a1 = B.outputs["auditor"]; a2 = B.outputs["analista"]; a3 = B.outputs["interprete"]; a4 = B.outputs["informe"]
    res = json.loads((DOCS / "matriz_auditoria.json").read_text(encoding="utf-8")) if (DOCS / "matriz_auditoria.json").exists() else {"resultados": [], "fallas": []}
    n_ok, n_tot = sum(1 for r in res["resultados"] if r["ok"]), len(res["resultados"])

    md = f"""# Expediente Técnico — Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos

**Proyecto Integrador Multidisciplinar · Universidad del Valle (Cali, Colombia)**
{FIRMA_MD[0]}
{FIRMA_MD[1]}
Curso: _[curso/semestre]_ · Docente: _[nombre]_
Huella del catálogo de prompts: `{catalog_hash()}` · Verificaciones automáticas aprobadas: **{n_ok}/{n_tot}**

---

## 1. Resumen y trazabilidad con la rúbrica

El sistema ingiere **cualquier** archivo tabular (CSV, TSV, Excel, JSON anidado o JSON Lines), infiere su estructura sin configuración, la limpia, la analiza, la interpreta y entrega un informe ejecutivo con visualizaciones. Como **plus**, un quinto agente —el **Consejero Estratégico y Líder-Analista**— conversa con quien administra: responde preguntas, **cuestiona las decisiones**, detecta sesgos, propone alternativas y entrega un plan de liderazgo, adaptándose a cualquier rol, sector y pregunta.

| Criterio de la rúbrica (peso) | Evidencia en este proyecto | Dónde verla |
|---|---|---|
| **Generalidad y adaptabilidad (25%)** | 9 datasets de estructuras y dominios distintos (comercial, PQR, producción, social, salud, recursos humanos, ruido, muestra mínima, una sola columna) procesados **sin modificar código ni prompts**: huellas idénticas antes/después (prueba J-01). Dominio inferido distinto por dataset (J-02). Ningún prompt menciona columnas ni dominios (J-04). | §4, §7 prueba J |
| **Arquitectura multiagente (25%)** | 4 roles de la guía + Agente 5; topología con payloads tipados y validados por esquema; guardrails entre etapas; trazabilidad por agente en JSON y en la interfaz. | §3, §5 |
| **Rigor de testeo (25%)** | Matriz de Auditoría con **{len(res['fallas'])} fallas documentadas** (reales e inducidas), su ajuste y **re-verificación automática**; batería de {n_tot} verificaciones con verdad de terreno; sondas de alucinación con un LLM simulado. | §6 |
| **Prueba en vivo y sustentación (25%)** | Interfaz web local (`py run.py servir`) que procesa una base desconocida en segundos, con trazabilidad visible; guion y preguntas frecuentes de defensa. | §8 |

## 2. Fase 1 · Formulación del problema y requerimientos

**Objetivo analítico (sin esquema fijo):** dado un conjunto de datos desconocido, producir de forma autónoma un informe ejecutivo orientado a decisiones y habilitar un diálogo crítico con el decisor.

| ID | Requerimiento (guía) | Cómo se cumple |
|---|---|---|
| RF-1 | Aceptar CSV, Excel, JSON de dominios diversos | `sma/ingest.py`: detecta codificación (UTF-8/cp1252/latin-1), delimitador (coma, punto y coma, tabulación o barra vertical), encabezado ausente, filas de título en Excel, hojas múltiples, JSON anidado/JSONL |
| RF-2 | Mapeo dinámico de variables (numéricas, categóricas, fechas, texto libre) | `sma/profiler.py` + Agente 1: tipo y **rol semántico** (medida, dimensión, fecha, identificador, texto, indicador) por evidencia; formatos de fecha y números mixtos |
| RF-3 | Arquitectura de 4 agentes (Auditor, Analista, Intérprete, Generador) | `sma/agents.py`, `sma/offline.py`, `sma/prompts.py` |
| RF-4 | Prompts estructurados (Rol, Contexto, Tarea, Restricciones, Formato) | `sma/prompts.py` (catálogo en §5) |
| RF-5 | Testeo obligatorio: A (cuantitativa), B (cualitativa), Resiliencia (≤30% nulos, columnas sin nombre, formatos mixtos) + Matriz de Auditoría | `tests/run_tests.py` → `docs/matriz_auditoria.md` (§6) |
| RF-6 | Entrega: diagramas, catálogo de prompts, matriz y prueba en vivo con base desconocida | Este expediente + `py run.py servir` |
| RF-7 (plus) | Agente analista y de liderazgo que ayude a decidir y **cuestione** las decisiones, adaptable a cualquier escenario, rol y pregunta | Agente 5 (§4.2) |
| RF-8 (plus) | Agente 6: simulador de crisis con selector de rol (Auxiliar, Asistente, Supervisor, Gerente), escenarios de crisis a partir del dataset, preguntas en 4 formatos interactivos y reporte final de desempeño | Agente 6 (§4.5) · pestaña «Simulador de crisis» |
| RNF-1 | Cero alucinaciones numéricas | Cálculo exacto por herramientas + verificación de cifras (§3.3) |
| RNF-2 | Operar sin conexión y con cualquier LLM | `sma/llm.py`: Anthropic, OpenAI-compatible (incl. Ollama/LM Studio) o motor determinista |

## 3. Fase 2 · Arquitectura y diseño de la red de agentes

<!--SVG:topologia-->

### 3.1 Topología y payloads

{MERMAID_TOPO}

Cada flecha es un **payload JSON** validado contra un esquema (`sma/prompts.py::SCHEMAS`). La salida de un agente es la entrada del siguiente:

| Etapa | Entrada (payload) | Salida (payload) |
|---|---|---|
| Ingesta (herramienta) | bytes + nombre | DataFrame de texto crudo + notas |
| Agente 1 · Auditor y Limpiador | muestra, esquema preliminar, problemas detectados, calidad | `mapeo_columnas`, `problemas`, `reglas_limpieza`, `calidad_global`, `advertencias` |
| Cómputo (herramienta) | dataset tipado | `hechos` con identificadores `ref` |
| Agente 2 · Analista | esquema + `hechos` | `variables_clave`, `resumen_cuantitativo`, `interacciones`, `tendencias`, `correlaciones`, `analisis_cualitativo`, `anomalias`, `limitaciones` |
| Agente 3 · Intérprete | análisis + `hechos` + calidad | `dominio_inferido`, `hallazgos` (con `evidencia` = refs), `riesgos`, `oportunidades`, `alertas_datos_faltantes`, `preguntas_abiertas` |
| Agente 4 · Generador | A1 + A2 + A3 + columnas válidas | `resumen_ejecutivo`, `secciones`, `recomendaciones`, `visualizaciones` (directivas) |
| Agente 5 · Consejero | informe + `hechos` + mensaje + rol + historial + señales | memorando de decisión (ver §4.2) |

**Ejemplo real de payloads** (dataset B, PQR):

```json
// Agente 1 → mapeo_columnas[0..1]
{j(a1['mapeo_columnas'][:2], 900)}
```
```json
// Agente 2 → resumen_cuantitativo[0]
{j(a2['resumen_cuantitativo'][:1], 600)}
```
```json
// Agente 3 → hallazgos[0]
{j(a3['hallazgos'][:1], 900)}
```
```json
// Agente 4 → visualizaciones[0]
{j(a4['visualizaciones'][:1], 500)}
```

### 3.2 Decisión de diseño: agentes aumentados con herramientas

Los LLM razonan bien pero **calculan mal** y pueden alucinar cifras (glosario [8] de la guía). Por eso cada agente **razona** (decide qué importa, interpreta, redacta) y las **herramientas deterministas calculan** (parseo exacto, estadísticos, series). El agente puede corregir tipos y roles del esquema, pero la herramienta **valida y ejecuta**: p. ej., si el LLM propone que una columna de texto es numérica, se rechaza por evidencia insuficiente (falla F-11). Esto mantiene el espíritu de la guía —no hay algoritmos rígidos por estructura de archivo— y elimina la fuente más común de alucinación.

### 3.3 Guardrails (control de calidad entre agentes)

{MERMAID_SEQ}

1. **Validación de esquema JSON** de cada salida; ante error, **un reintento** con el error como retroalimentación.
2. **Valores medidos son autoritativos:** estadísticos, % de nulos y puntaje de calidad se sobrescriben con los calculados por herramientas (se registra la corrección).
3. **Referencias verificables:** todo hallazgo debe citar `ref` existentes en `hechos`; sin evidencia se descarta.
4. **Verificación de cifras:** cada número de un texto se contrasta con la lista blanca de cifras de los hechos (tolerancia de redondeo, escalas «millones», signo); el no verificado se **enmascara** como `[cifra no verificada]` y se registra.
5. **Regla N/A:** los nulos se reportan, nunca se imputan.
6. **Respaldo determinista** si el LLM falla, devuelve JSON inválido dos veces o no hay modelo: la cadena siempre termina y la trazabilidad indica el motor usado.

## 4. El plus: Agente analista y de liderazgo

### 4.1 Propósito

Que cualquier administrador **decida mejor**, no que se sienta validado. El Consejero actúa como analista (contrasta con los datos), abogado del diablo (cuestiona) y líder (plan, stakeholders, comunicación, criterio de reversión).

### 4.2 Qué entrega (memorando de decisión)

| Bloque | Contenido |
|---|---|
| Modo y reformulación | Distingue **pregunta**, **decisión** o **exploración** y reformula el problema real |
| Lectura del rol | Lente según el rol declarado (o detectado en el texto, o inferido del dominio): finanzas, comercial, operaciones, servicio, talento, sector público, salud, educación, general |
| Respuesta / postura | `proceder` · `proceder con condiciones` · `pilotar primero` · `reconsiderar` · `evidencia insuficiente`, con confianza |
| Evidencia a favor / en contra | Citada con cifras de los datos (la entidad que menciones —«sucursal Sur», «Logística»— se enlaza con el dataset) |
| Cuestionamientos | Supuesto · por qué importa · **prueba que lo refutaría** · severidad (incluye contraste de cifras con la variabilidad real, irreversibilidad, calidad y cobertura de datos, concentración, causalidad) |
| Sesgos | 12 familias (exceso de certeza, anécdota, costo hundido, urgencia, autoridad, causalidad apresurada, confirmación, optimismo, túnel, falsa dicotomía, cortoplacismo, inercia) con su contramedida |
| Pre-mortem y alternativas | «Si fracasa en 6 meses fue porque…»; ≥2 alternativas incluida «medir antes de actuar» |
| Plan de liderazgo | Primeros pasos, KPIs (derivados de los datos), stakeholders, comunicación, **criterio de reversión** numérico |
| Preguntas de vuelta | Máx. 4, las que más cambiarían la decisión; no repite las ya hechas |
| Datos que faltan | Variables típicamente decisivas ausentes (costo/margen, metas, satisfacción, benchmark) |

### 4.3 Adaptabilidad (sin reglas por dominio)

* **Rol:** detectado del campo «rol» o del propio texto («Soy el director de…», «Como secretario…»); cambia el lente, los stakeholders, los KPIs y el estilo de comunicación.
* **Escenario:** las entidades mencionadas se buscan en *cualquier* columna categórica; las preguntas se vinculan a columnas por raíz léxica (`defectos` → `unidades_defectuosas`) y se precalcula la agrupación pedida.
* **Pregunta o decisión:** tres modos distintos de respuesta; el seguimiento recuerda la decisión previa.
* **Con LLM:** el prompt del Agente 5 deja al modelo razonar libremente; las señales verificables y los guardrails se mantienen.

### 4.4 Ejemplos reales

**Gerente comercial · base de ventas · «cerrar la sucursal Occidente»**

{advice_md(memo)}

**Sector público · base social (rol no declarado, detectado desde el texto)**

{advice_md(memo_pub)}

### 4.5 Agente 6 · Simulador de Crisis y Evaluación Directiva

**Qué hace.** A partir de los datos cargados construye un ejercicio de crisis y evalúa la toma de decisiones de la persona según el **rol** que asume.

| Elemento | Detalle |
|---|---|
| Selector de rol | Auxiliar · Asistente · Supervisor · Gerente (cada uno con su alcance, responsabilidad e importancia de competencias) |
| Escenario de crisis | Inopia (liquidez) · Al borde de la quiebra · Crisis operativa crítica · Automático (elige según señales de los datos: caída, mensajes negativos, calidad). El choque (p. ej. «cae 30%») se declara como **supuesto del ejercicio**; las demás cifras provienen de los datos reales |
| Formatos de pregunta | Opción múltiple (A-D, con puntaje parcial) · Falso/Verdadero · Emparejamiento causa↔solución (un desplegable por causa) · Completar la frase con desplegables |
| Calibración por rol | La mejor respuesta a la misma situación cambia con el rol: un Auxiliar escala con evidencia; un Asistente analiza y prepara insumos; un Supervisor coordina y ejecuta; un Gerente decide prioridades y recursos con criterio de reversión. Lo que excede el alcance del rol puntúa 0 |
| Reporte final | Puntaje 0-100%, **% de éxito de las decisiones**, decisiones óptimas, nivel de desempeño, diagnóstico de habilidades según el rol, 6 competencias con su importancia para el rol, preparación para el rol, recomendaciones de mejora y revisión pregunta por pregunta |
| Interfaz | Bloque «Instrucciones de Uso del Simulador» (4 pasos, también en ventana modal) sobre el widget; rol con tarjetas de radio; escenario con desplegable; dinámica con radios; progreso, navegación y resultados |

**Diseño y garantías.** La generación usa el prompt `simulador` (§5) con validación estricta de cada pregunta (formato, 4 opciones A-D, una sola mejor respuesta, claves coherentes, competencia válida) y respaldo determinista; la **calificación es siempre aritmética** (no depende de un LLM); la clave de respuestas permanece en el servidor y el cliente solo recibe la vista pública (prueba L-01/L-08).

## 5. Fase 3 · Catálogo de prompts

Los prompts son **genéricos** (no mencionan dominio ni columnas). La columna *Origen* indica si la regla es de diseño o un **ajuste posterior a una falla** de la Fase 4 (trazable en la matriz).

{chr(10).join(cat)}

## 6. Fase 4 · Testeo, control de calidad y resiliencia

**Protocolo:** (1) Prueba A cuantitativa/comercial; (2) Prueba B cualitativa PQR/texto libre; (3) Prueba de resiliencia con ruido (hasta 30% de nulos, columnas sin nombre, 4 formatos de fecha, importes con `$` y miles, duplicados, marcadores `N/A`/`-`/`?`/`sin dato`); (4) datasets adicionales: JSON anidado, Excel con título y 2 hojas, base **sorpresa** sin encabezado en latin-1; (5) muestra de 12 filas; (6) consejero en 6 sectores y roles; (7) **sondas de alucinación** con un LLM simulado que miente a propósito; (8) generalidad: mismos código y prompts para todo.

Los datasets son **sintéticos con verdad de terreno** (`tests/make_datasets.py`, semilla fija), lo que permite medir exactitud real (p. ej. el 100% de las fechas convertidas coincide con el original, la suma de importes es idéntica, la exactitud del sentimiento se mide contra etiquetas).

{matriz}

## 7. Fase 5 · Entrega y sustentación

### 7.1 Cómo ejecutar

```bash
pip install -r requirements.txt
py run.py servir            # interfaz web: http://127.0.0.1:8765
py run.py pruebas           # Fase 4 completa + Matriz de Auditoría
py run.py analizar mi_base.csv --rol "Gerente" --mensaje "Voy a ..."
```

Para usar un LLM: `set ANTHROPIC_API_KEY=...` (o `OPENAI_API_KEY`; `SMA_OPENAI_BASE_URL` para Ollama/LM Studio). Sin clave, el sistema usa el motor determinista y lo indica en el informe y en la trazabilidad.

### 7.2 Guion sugerido para la prueba en vivo (≈10 min)

1. Abrir la interfaz; mostrar el motor activo y la huella de prompts.
2. Soltar la base desconocida de los docentes. Mostrar la pestaña **Trazabilidad**: cada agente, su motor, los payloads y las correcciones de guardrail.
3. Leer el resumen ejecutivo y mostrar el esquema inferido (tipos y roles) y la calidad de datos.
4. Pasar a **Consejero**: plantear una decisión real sobre esa base y mostrar cómo la cuestiona; luego una pregunta abierta y un seguimiento.
5. Mostrar la Matriz de Auditoría: fallas reales, ajuste y re-verificación.

### 7.3 Preguntas probables de defensa

| Pregunta | Respuesta breve |
|---|---|
| ¿Dónde está la IA si calculan herramientas? | Los agentes deciden el significado (roles, variables clave, interpretación, redacción, cuestionamiento); las herramientas son «calculadoras» que evitan alucinaciones aritméticas. Ver §3.2. |
| ¿Cómo evitan alucinaciones? | Valores medidos autoritativos, refs obligatorias, verificación de cifras con enmascarado, regla N/A y sondas con un LLM que miente (§3.3, §6). |
| ¿Qué pasa si el LLM falla? | Un reintento con retroalimentación y luego respaldo determinista; la trazabilidad lo registra. |
| ¿Es realmente agnóstico? | Huellas de código y prompts idénticas tras procesar 9 datasets; ningún prompt menciona columnas. |
| ¿Cómo cuestiona el Agente 5 sin LLM? | Con señales verificables (entidades, cifras vs variabilidad, sesgos) y plantillas de razonamiento críticas; con LLM razona libremente sobre esas mismas señales. |

## 8. Limitaciones y trabajo futuro (declaradas con transparencia)

* **Motor LLM:** la integración (Anthropic y OpenAI-compatible), el reintento y los guardrails están implementados y **probados con un LLM simulado**; en esta entrega no se ejecutó contra un modelo en vivo por no contar con una clave de API en el entorno de desarrollo. Recomendación: con clave disponible, ejecutar `py run.py pruebas --con-llm`, **registrar en la matriz** las diferencias observadas y ajustar prompts (el procedimiento ya está instrumentado).
* **Sentimiento sin LLM:** el motor de respaldo usa un léxico general en español (82,8% → {acc_txt}% de exactitud en la base sintética tras el ajuste F-09); la ironía y el contexto fino requieren el LLM.
* **Datos de prueba sintéticos:** sirven para medir exactitud con verdad de terreno; conviene complementarlos con datos abiertos reales (p. ej. datos.gov.co) antes de la sustentación.
* **Consejero sin LLM:** sus plantillas son críticas pero finitas; no sustituyen el razonamiento libre de un modelo. No ofrece asesoría legal, médica o financiera vinculante.
* **Rentabilidad y causalidad:** los datos tabulares rara vez incluyen costos ni experimentos; el sistema lo declara en «datos que faltan» y propone pilotos con grupo de comparación.

## 9. Referencias

* Microsoft AutoGen — https://microsoft.github.io/autogen/
* CrewAI — https://docs.crewai.com/
* Prompt Engineering Guide (DAIR.AI) — https://www.promptingguide.ai/es
* Guía Metodológica Institucional · Universidad del Valle — Proyecto Integrador Multidisciplinar (sistemas multiagente de IA).
"""
    (DOCS / "expediente_tecnico.md").write_text(md, encoding="utf-8")

    body = markdown.markdown(md, extensions=["tables", "fenced_code", "toc", "sane_lists"])
    body = body.replace("<!--SVG:topologia-->", f'<div class="diagram">{svg_topologia()}</div>')
    body = re.sub(r'<pre><code class="language-mermaid">.*?</code></pre>', '<p class="muted"><em>(Diagrama Mermaid disponible en la versión Markdown; ver diagrama SVG de topología arriba.)</em></p>', body, flags=re.S)
    html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Expediente técnico · Sistema multiagente</title><style>
body{{margin:0;background:#f7f8f6;color:#16211f;font:15px/1.6 system-ui,Segoe UI,Roboto,sans-serif}}main{{max-width:1040px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:26px}}h2{{margin-top:2em;border-bottom:2px solid #0f766e;padding-bottom:.25em}}h3{{margin-top:1.4em;color:#0f766e}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin:.6em 0 1.2em;display:block;overflow-x:auto}}th,td{{border:1px solid #dfe5e2;padding:6px 8px;text-align:left;vertical-align:top}}th{{background:#e3f2ef}}
pre{{background:#0f1513;color:#e6eeeb;padding:12px;border-radius:8px;overflow-x:auto;font-size:12.5px}}code{{background:#e3f2ef;padding:1px 5px;border-radius:4px}}pre code{{background:none;padding:0}}
.diagram{{background:#fff;border:1px solid #dfe5e2;border-radius:10px;padding:8px;overflow-x:auto}}.diagram svg{{width:100%;min-width:760px;height:auto}}details{{margin:.4em 0}}summary{{cursor:pointer;color:#0f766e}}
hr{{border:0;border-top:1px solid #dfe5e2;margin:1.6em 0}}.muted{{color:#5b6b67}}
@media (prefers-color-scheme:dark){{body{{background:#0f1513;color:#e6eeeb}}th{{background:#143a35}}td,th{{border-color:#2a3733}}code{{background:#143a35}}h3{{color:#3cc4b4}}}}
:root{{--muted:#5b6b67;--accent:#0f766e}}{WATERMARK_CSS}
@media print{{pre{{white-space:pre-wrap}}table{{display:table}}}}
</style></head><body>{watermark_html()}{print_footer_html()}<main>{body}</main></body></html>"""
    (DOCS / "expediente_tecnico.html").write_text(html, encoding="utf-8")
    print("Expediente generado:", DOCS / "expediente_tecnico.html")


if __name__ == "__main__":
    main()

