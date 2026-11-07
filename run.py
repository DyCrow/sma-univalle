#!/usr/bin/env python
# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Interfaz de línea de comandos del Sistema Multiagente (Proyecto Integrador · Universidad del Valle).

  py run.py servir                      # interfaz web local (recomendada para la sustentación)
  py run.py analizar ARCHIVO [--rol "Gerente"] [--mensaje "Voy a ..."] [--salida carpeta]
  py run.py consejero ARCHIVO [--rol "..."]      # chat interactivo con el consejero estratégico
  py run.py pruebas                     # Fase 4: batería completa + Matriz de Auditoría
  py run.py demo                        # procesa todos los datasets de ejemplo

Motor: define ANTHROPIC_API_KEY (o OPENAI_API_KEY / SMA_OPENAI_BASE_URL) para usar un LLM; sin clave opera con el motor determinista.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

from sma.pipeline import MultiAgentSystem  # noqa: E402
from sma.report import advice_md  # noqa: E402


def cmd_analizar(a):
    sysm = MultiAgentSystem(verbose=True)
    print(f"Motor: {sysm.llm.name}\nProcesando {a.archivo} …")
    run = sysm.analyze_path(a.archivo)
    advice = sysm.advise(run, a.mensaje or "", a.rol or "") if (a.mensaje is not None or a.rol) else None
    files = sysm.save(run, a.salida, advice)
    inf = run.outputs["informe"]
    print(f"\n=== {inf['titulo']} ===\n{inf['resumen_ejecutivo']}\n")
    if advice:
        print(advice_md(advice))
    print("\nArchivos generados:")
    for k, v in files.items():
        print(f"  {k:8s} {v}")


def cmd_consejero(a):
    sysm = MultiAgentSystem()
    run = sysm.analyze_path(a.archivo)
    print(f"Motor: {sysm.llm.name}\nBase cargada: {run.filename} ({run.facts['resumen']['filas']} filas). Dominio: {run.outputs['interprete']['dominio_inferido']['dominio']}.")
    print(f"Resumen: {run.outputs['informe']['resumen_ejecutivo']}\n")
    print("Cuéntame una decisión, una pregunta o escribe 'explorar'. Línea vacía o 'salir' para terminar.\n")
    rol = a.rol or ""
    while True:
        try:
            msg = input("Tú > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in ("salir", "exit", "q"):
            break
        if msg.lower().startswith("rol:"):
            rol = msg[4:].strip()
            print(f"  (rol fijado: {rol})")
            continue
        if msg.lower() == "explorar":
            msg = ""
        elif not msg:
            break
        memo = sysm.advise(run, msg, rol)
        print("\n" + advice_md(memo) + "\n")


def cmd_demo(a):
    sysm = MultiAgentSystem(verbose=False)
    out = ROOT / "salidas"
    for p in sorted((ROOT / "data").glob("[A-I]_*")):
        if "_etiquetas" in p.name:
            continue
        run = sysm.analyze_path(p)
        sysm.save(run, out)
        print(f"✔ {p.name:42s} → {run.outputs['interprete']['dominio_inferido']['dominio']:32s} calidad {run.facts['calidad']['puntaje']}/100")
    print(f"\nInformes en {out}")


def main():
    ap = argparse.ArgumentParser(description="Sistema Multiagente de IA · Univalle")
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("servir"); s.add_argument("--puerto", type=int, default=8765); s.add_argument("--sin-navegador", action="store_true")
    s = sp.add_parser("analizar"); s.add_argument("archivo"); s.add_argument("--rol"); s.add_argument("--mensaje"); s.add_argument("--salida", default=str(ROOT / "salidas"))
    s = sp.add_parser("consejero"); s.add_argument("archivo"); s.add_argument("--rol")
    sp.add_parser("pruebas"); sp.add_parser("demo")
    a = ap.parse_args()
    if a.cmd == "servir":
        from sma.web import serve
        serve(a.puerto, not a.sin_navegador)
    elif a.cmd == "analizar":
        cmd_analizar(a)
    elif a.cmd == "consejero":
        cmd_consejero(a)
    elif a.cmd == "pruebas":
        sys.path.insert(0, str(ROOT / "tests"))
        import run_tests
        sys.exit(run_tests.main())
    elif a.cmd == "demo":
        cmd_demo(a)


if __name__ == "__main__":
    main()


