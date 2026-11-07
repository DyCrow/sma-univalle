# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos

Proyecto Integrador Multidisciplinar · Universidad del Valle. Cumple las fases 1–5 de la guía y agrega un **quinto agente: Consejero Estratégico y Líder-Analista** que cuestiona las decisiones de quien administra.

## Inicio rápido (Windows / macOS / Linux)

```bash
pip install -r requirements.txt
py run.py servir
```

Se abre `http://127.0.0.1:8765`: arrastra cualquier CSV / Excel / JSON y obtén el informe, la trazabilidad de agentes y el chat con el consejero.

| Comando | Qué hace |
|---|---|
| `py run.py servir` | Interfaz web (sustentación en vivo) |
| `py run.py analizar base.csv --rol "Gerente" --mensaje "Voy a ..."` | Informe + memorando del consejero; guarda HTML, MD, CSV limpio, hechos y trazabilidad en `salidas/` |
| `py run.py consejero base.csv` | Chat interactivo en consola |
| `py run.py pruebas` | Fase 4: batería (91 verificaciones) y regeneración de `docs/matriz_auditoria.md` |
| `py tests/build_docs.py` | Regenera `docs/expediente_tecnico.html/.md` |
| `py run.py demo` | Procesa todos los datasets de ejemplo |

## Motor de IA

* Sin configuración: **motor determinista** (sin conexión ni costo). Los agentes devuelven el mismo JSON que con LLM.
* Con LLM: `set ANTHROPIC_API_KEY=...` (modelo por defecto `claude-sonnet-5-5`, cambiar con `SMA_MODEL`) u `OPENAI_API_KEY` / `SMA_OPENAI_BASE_URL` (OpenAI, Ollama, LM Studio…). El informe y la trazabilidad indican siempre el motor usado por agente.
* Pruebas con LLM real: `py run.py pruebas --con-llm` (registre las diferencias en la matriz).

## Estructura

```
run.py                 CLI
sma/ingest.py          ingesta agnóstica (CSV/Excel/JSON, encoding, delimitador, encabezado)
sma/profiler.py        tipos, formatos de fecha/número, nulos, roles semánticos
sma/cleaner.py         esquema, validación de propuestas del agente, limpieza, calidad
sma/analytics.py       hechos exactos con `ref` (estadísticos, series, correlaciones, texto)
sma/prompts.py         catálogo de prompts (Rol·Contexto·Tarea·Restricciones·Formato) + esquemas
sma/agents.py          clase Agent (reintento, validación, guardrails, respaldo)
sma/offline.py         motores deterministas de los Agentes 1-4
sma/strategist.py      Agente 5 (consejero): señales, sesgos, entidades, lentes por rol, motor de respaldo
sma/report.py          informe HTML/MD y gráficos SVG
sma/web.py             servidor local
tests/                 generador de datasets con verdad de terreno, batería de pruebas, generador del expediente
data/                  datasets de prueba A–G
docs/                  expediente técnico, matriz de auditoría, bitácora de fallas, diagramas
```

## Agente 6 · Simulador de crisis

Pestaña **Simulador de crisis**: 1) elige tu rol (Auxiliar, Asistente, Supervisor, Gerente); 2) elige tipo de crisis y dinámica; 3) responde (opción múltiple, F/V, emparejamiento, desplegables); 4) recibe tu reporte de desempeño con puntaje y % de éxito. API: `/api/simulador/config`, `/iniciar`, `/evaluar`.

## Cómo usar al Consejero (Agente 5)

* **Decisión:** «Voy a cerrar la sucursal Sur porque vende poco» → postura, evidencia a favor/en contra, supuestos cuestionados, sesgos, pre-mortem, alternativas, plan de liderazgo.
* **Pregunta:** «¿Qué máquina tiene más defectos?» → respuesta con cifras de tus datos + premisas a verificar.
* **Exploración:** botón «Explorar sin decisión previa» → decisiones que los datos sugieren y lo que cuestionaría de cada una.
* Indica tu rol (o escríbelo: «Soy la secretaria de salud…»): cambia el lente, los stakeholders y los KPIs.


