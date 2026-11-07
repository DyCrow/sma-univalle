# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Orquestador de la red de agentes (topología secuencial con verificación entre etapas + Agente 5 conversacional)."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .agents import Agent, post_analista, post_auditor, post_estratega, post_informe, post_interprete
from .analytics import compute_facts
from .cleaner import apply_cleaning, build_schema, validate_schema_override
from .ingest import load_bytes
from .llm import LLM, NullLLM, llm_from_env
from .offline import offline_analista, offline_auditor, offline_informe, offline_interprete
from .prompts import catalog_hash
from .report import advice_md, render_html, render_md
from .strategist import advise_offline, build_signals


def _kb(o) -> str:
    return f"{len(json.dumps(o, ensure_ascii=False, default=str)) / 1024:.1f} KB"


def compact_schema(schema: list[dict]) -> list[dict]:
    return [{k: c.get(k) for k in ("original", "normalizado", "tipo", "rol", "pct_nulos", "detalle")} for c in schema]


@dataclass
class Run:
    filename: str
    llm_name: str
    prompt_hash: str
    raw: pd.DataFrame | None = None
    ingest_notes: list = field(default_factory=list)
    header_log: list = field(default_factory=list)
    schema: list = field(default_factory=list)
    clean: pd.DataFrame | None = None
    clean_log: dict = field(default_factory=dict)
    facts: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    trace: list = field(default_factory=list)
    chat: list = field(default_factory=list)

    def engines(self) -> dict:
        return {t["etapa"]: t["motor"] for t in self.trace}


class MultiAgentSystem:
    def __init__(self, llm: LLM | None = None, verbose: bool = False):
        self.llm = llm if llm is not None else llm_from_env()
        self.verbose = verbose

    def _log(self, *a):
        if self.verbose:
            print(*a, flush=True)

    def _stage(self, run: Run, etapa: str, entrada: str, salida: str, meta: dict, motor: str | None = None):
        run.trace.append({"etapa": etapa, "motor": motor or meta.get("motor", "determinista"), "entrada": entrada, "salida": salida, "ms": meta.get("ms", 0),
                          "intentos": meta.get("intentos", 0), "problemas_validacion": meta.get("problemas_validacion", []),
                          "correcciones_guardrail": meta.get("correcciones_guardrail", []), "cifras_no_verificadas": meta.get("cifras_no_verificadas", [])})
        self._log(f"  · {etapa}: {motor or meta.get('motor')} ({meta.get('ms', 0)} ms)")

    # ------------------------------------------------------------------------------ Agentes 1-4
    def analyze_bytes(self, data: bytes, filename: str) -> Run:
        run = Run(filename=filename, llm_name=self.llm.name, prompt_hash=catalog_hash())
        t0 = time.time()
        run.raw, run.ingest_notes = load_bytes(data, filename)
        self._stage(run, "Ingesta (herramienta)", f"{len(data) / 1024:.0f} KB", f"{run.raw.shape[0]}×{run.raw.shape[1]} texto crudo", {"ms": int((time.time() - t0) * 1000)}, "herramienta")

        # --- Percepción determinista + Agente 1
        t0 = time.time()
        schema, run.header_log = build_schema(run.raw)
        dry_clean, dry_log = apply_cleaning(run.raw, schema)  # corrida en seco: actualiza pct_nulos medidos en 'schema'
        payload1 = {"ingesta": run.ingest_notes, "n_filas_crudas": len(run.raw), "n_columnas": run.raw.shape[1], "muestra": run.raw.head(6).to_dict(orient="records"),
                    "esquema_preliminar": schema, "log_encabezados": run.header_log, "problemas_detectados": dry_log["issues"], "acciones_limpieza": dry_log["acciones"], "calidad": dry_log["score"]}
        a1, m1 = Agent("auditor", offline_auditor, post_auditor).run(self.llm, payload1)
        # El agente propone; las herramientas validan y ejecutan
        by_orig = {c["original"]: c for c in schema}
        final, notes = [], []
        for c in schema:
            prop = next((m for m in a1["mapeo_columnas"] if m["original"] == c["original"]), None)
            if prop:
                c2, n = validate_schema_override(prop, c)
                notes += n
                final.append(c2)
            else:
                final.append(c)
        changed = any(a["tipo"] != b["tipo"] or a["rol"] != b["rol"] for a, b in zip(schema, final))
        run.schema = final
        if changed:
            run.clean, run.clean_log = apply_cleaning(run.raw, run.schema)
            a1["problemas"], a1["calidad_global"] = run.clean_log["issues"], {"puntaje": run.clean_log["score"]["puntaje"], "veredicto": run.clean_log["score"]["veredicto"]}
            m1["correcciones_guardrail"] += notes
        else:
            run.clean, run.clean_log = dry_clean, dry_log
        # los valores medidos son autoritativos
        a1["problemas"], a1["calidad_global"] = run.clean_log["issues"], {"puntaje": run.clean_log["score"]["puntaje"], "veredicto": run.clean_log["score"]["veredicto"]}
        run.outputs["auditor"] = a1
        self._stage(run, "Agente 1 · Auditor y Limpiador", f"{_kb(payload1)} (esquema+muestra)", f"{len(a1['mapeo_columnas'])} cols, {len(a1['problemas'])} problemas", m1)

        # --- Hechos (herramienta) + Agente 2
        t0 = time.time()
        run.facts = compute_facts(run.clean, run.schema, run.clean_log["score"], run.clean_log)
        self._stage(run, "Cómputo estadístico (herramienta)", f"{run.clean.shape[0]}×{run.clean.shape[1]} tipado", f"hechos {_kb(run.facts)}", {"ms": int((time.time() - t0) * 1000)}, "herramienta")
        payload2 = {"esquema": compact_schema(run.schema), "hechos": run.facts, "calidad": a1["calidad_global"]}
        a2, m2 = Agent("analista", offline_analista, post_analista).run(self.llm, payload2)
        run.outputs["analista"] = a2
        self._stage(run, "Agente 2 · Analista Estadístico", _kb(payload2), f"{len(a2['interacciones'])} interacciones, {len(a2['tendencias'])} tendencias", m2)

        # --- Agente 3
        payload3 = {"esquema": run.schema, "hechos": run.facts, "analisis": a2, "problemas": a1["problemas"], "calidad": a1["calidad_global"]}
        a3, m3 = Agent("interprete", offline_interprete, post_interprete).run(self.llm, payload3)
        run.outputs["interprete"] = a3
        self._stage(run, "Agente 3 · Intérprete Contextual", _kb({"analisis": a2, "hechos": "…"}), f"{len(a3['hallazgos'])} hallazgos · dominio {a3['dominio_inferido']['dominio']}", m3)

        # --- Agente 4
        sec_cal = {"titulo": "Calidad de datos y limitaciones", "contenido_md": f"Puntaje de calidad: **{a1['calidad_global']['puntaje']}/100** ({a1['calidad_global']['veredicto']}).\n" + "\n".join(f"- [{x['severidad']}] {x['columna']}: {x['detalle']} → {x['accion']}" for x in a1["problemas"][:10])}
        valid_cols = [c["normalizado"] for c in run.schema]
        payload4 = {"hechos": run.facts, "auditoria": a1, "analisis": a2, "interpretacion": a3, "columnas_validas": valid_cols, "seccion_calidad": sec_cal}
        a4, m4 = Agent("informe", offline_informe, post_informe).run(self.llm, payload4)
        run.outputs["informe"] = a4
        self._stage(run, "Agente 4 · Generador de Informes", _kb({"a1": a1, "a2": a2, "a3": a3}), f"{len(a4['secciones'])} secciones, {len(a4['visualizaciones'])} gráficos", m4)
        return run

    def analyze_path(self, path: str | Path) -> Run:
        p = Path(path)
        return self.analyze_bytes(p.read_bytes(), p.name)

    # ------------------------------------------------------------------------------ Agente 5 (PLUS)
    def advise(self, run: Run, mensaje: str, rol: str = "", history: list | None = None) -> dict:
        history = history if history is not None else run.chat
        signals = build_signals(run, mensaje, rol, history)
        inf = run.outputs["informe"]
        payload = {"informe": {"titulo": inf["titulo"], "resumen_ejecutivo": inf["resumen_ejecutivo"], "recomendaciones": inf["recomendaciones"]},
                   "hallazgos": run.outputs["interprete"]["hallazgos"], "hechos": run.facts, "calidad": run.facts["calidad"],
                   "contexto_usuario": {"rol": rol, "mensaje": mensaje, "historial": history[-8:]}, "senales": signals}
        agent = Agent("estratega", lambda p: advise_offline(run, mensaje, rol, history, signals=p["senales"]), post_estratega)
        out, meta = agent.run(self.llm, payload)
        self._stage(run, "Agente 5 · Consejero Estratégico", f"{len(mensaje.split())} palabras + señales", f"postura: {out['recomendacion']['postura']}", meta)
        run.chat.append({"rol": "usuario", "texto": mensaje})
        run.chat.append({"rol": "asesor", "texto": "\n".join(out.get("preguntas_para_el_administrador", [])) or out["respuesta_directa"]})
        out["_meta"] = {"motor": meta["motor"], "senales": {k: signals[k] for k in ("lente", "rol_etiqueta", "rol_declarado", "dominio", "clasificacion")}, "entidades": [f"{e['columna']}={e['valor']}" for e in signals["entidades"]],
                        "correcciones_guardrail": meta["correcciones_guardrail"], "cifras_no_verificadas": meta["cifras_no_verificadas"]}
        return out

    # ------------------------------------------------------------------------------ Agente 6 (Simulador de crisis)
    def simulate_start(self, run: Run, rol: str, escenario: str = "auto", dinamica: str = "mixta", n: int = 8, seed: int | None = None, run_id: str = ""):
        from .simulator import generate

        sim, meta = generate(self.llm, run, run_id, rol, escenario, dinamica, n, seed)
        self._stage(run, "Agente 6 · Simulador de Crisis (generación)", f"rol {rol} · {sim.escenario} · {dinamica}", f"{len(sim.preguntas)} preguntas", meta)
        return sim

    def simulate_grade(self, run: Run, sim, respuestas: dict) -> dict:
        from .simulator import grade

        t0 = time.time()
        rep = grade(sim, respuestas)
        self._stage(run, "Agente 6 · Evaluación directiva (aritmética determinista)", f"{len(respuestas or {})} respuestas", f"puntaje {rep['puntaje_pct']}%", {"ms": int((time.time() - t0) * 1000)}, "determinista")
        return rep

    # ------------------------------------------------------------------------------ salidas
    def save(self, run: Run, outdir: str | Path, advice: dict | None = None) -> dict:
        out = Path(outdir)
        out.mkdir(parents=True, exist_ok=True)
        stem = Path(run.filename).stem
        files = {
            "html": out / f"{stem}_informe.html", "md": out / f"{stem}_informe.md", "trace": out / f"{stem}_trazabilidad.json", "limpio": out / f"{stem}_limpio.csv", "hechos": out / f"{stem}_hechos.json"}
        files["html"].write_text(render_html(run, advice), encoding="utf-8")
        files["md"].write_text(render_md(run, advice), encoding="utf-8")
        files["trace"].write_text(json.dumps({"archivo": run.filename, "motor": run.llm_name, "huella_prompts": run.prompt_hash, "etapas": run.trace, "salidas_agentes": run.outputs}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        run.clean.to_csv(files["limpio"], index=False, encoding="utf-8-sig")
        files["hechos"].write_text(json.dumps(run.facts, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        return {k: str(v) for k, v in files.items()}
