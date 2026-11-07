# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Servidor web local (stdlib) para la sustentación en vivo: carga un archivo, ejecuta la red de agentes y abre el chat con el consejero."""
from __future__ import annotations

import html
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .branding import FIRMA_TXT, print_footer_html, watermark_html
from .llm import llm_from_env
from .pipeline import MultiAgentSystem, Run
from .prompts import PROMPTS, catalog_hash
from .report import CSS, advice_html, md_to_html, render_html, render_md
from .simulator import ESCENARIOS, FORMATOS, public_view
from .strategist import COMPETENCIAS, NIVELES

ROOT = Path(__file__).resolve().parents[1]
RUNS: dict[str, Run] = {}
SIMS: dict[str, tuple] = {}
LOCK = threading.Lock()
SYSTEM: MultiAgentSystem | None = None


def _run_summary(run: Run) -> dict:
    f, o = run.facts, run.outputs
    return {"id": None, "archivo": run.filename, "motor": run.llm_name, "huella": run.prompt_hash, "filas": f["resumen"]["filas"], "columnas": f["resumen"]["columnas"],
            "calidad": f["calidad"], "dominio": o["interprete"]["dominio_inferido"], "medida_principal": f["medida_principal"], "tiene_texto": bool(f["texto"]),
            "informe_html": render_html(run, standalone=False),
            "trazabilidad": run.trace, "esquema": [{k: c.get(k) for k in ("original", "normalizado", "tipo", "rol", "pct_nulos")} for c in run.schema]}


class Handler(BaseHTTPRequestHandler):
    server_version = "SMA-Univalle/1.0"

    def log_message(self, fmt, *args):  # silencioso
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8", extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200):
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))

    def _body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            page = (PAGE.replace("/*CSS*/", CSS).replace("<!--WM-->", watermark_html()).replace("<!--FIRMA-->", html.escape(FIRMA_TXT))
                    .replace("<!--FOOT-->", print_footer_html()))
            self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        elif u.path in ("/expediente", "/matriz"):
            p = ROOT / "docs" / ("expediente_tecnico.html" if u.path == "/expediente" else "matriz_auditoria.md")
            if not p.exists():
                return self._json({"error": "Genere el documento con: py tests/run_tests.py && py tests/build_docs.py"}, 404)
            self._send(200, p.read_bytes(), "text/html; charset=utf-8" if p.suffix == ".html" else "text/plain; charset=utf-8")
        elif u.path == "/api/simulador/config":
            self._json({"roles": [{"id": r, "alcance": v["alcance"], "responsabilidad": v["responsabilidad"]} for r, v in NIVELES.items()],
                        "escenarios": [{"id": k, "nombre": v["nombre"], "descripcion": v["descripcion"]} for k, v in ESCENARIOS.items()],
                        "dinamicas": [{"id": "mixta", "nombre": "Mixta (los 4 formatos)"}] + [{"id": k, "nombre": v} for k, v in FORMATOS.items()], "competencias": COMPETENCIAS})
        elif u.path == "/api/estado":
            self._json({"motor": SYSTEM.llm.name, "llm": SYSTEM.llm.available, "huella": catalog_hash(), "agentes": {k: v["nombre"] for k, v in PROMPTS.items()}})
        elif u.path == "/api/demos":
            self._json([p.name for p in sorted((ROOT / "data").glob("[A-I]_*")) if "_etiquetas" not in p.name])
        elif u.path.startswith("/api/descargar/"):
            rid, _, ext = u.path.rsplit("/", 1)[1].partition(".")
            run = RUNS.get(rid)
            if not run:
                return self._json({"error": "sesión no encontrada"}, 404)
            advice = getattr(run, "last_advice", None)
            if ext == "md":
                self._send(200, render_md(run, advice).encode("utf-8"), "text/markdown; charset=utf-8", {"Content-Disposition": f'attachment; filename="{Path(run.filename).stem}_informe.md"'})
            else:
                self._send(200, render_html(run, advice).encode("utf-8"), "text/html; charset=utf-8", {"Content-Disposition": f'attachment; filename="{Path(run.filename).stem}_informe.html"'})
        else:
            self._json({"error": "no encontrado"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/api/analizar":
                name = q.get("nombre", ["archivo.csv"])[0]
                data = self._body()
                if not data:
                    return self._json({"error": "Archivo vacío."}, 400)
                self._analyze(data, name)
            elif u.path == "/api/demo":
                name = Path(q.get("archivo", [""])[0]).name
                p = ROOT / "data" / name
                if not p.exists():
                    return self._json({"error": "Dataset de ejemplo no encontrado."}, 404)
                self._analyze(p.read_bytes(), name)
            elif u.path == "/api/consejero":
                req = json.loads(self._body().decode("utf-8") or "{}")
                run = RUNS.get(req.get("id", ""))
                if not run:
                    return self._json({"error": "Primero carga y analiza un archivo."}, 400)
                memo = SYSTEM.advise(run, (req.get("mensaje") or "").strip(), (req.get("rol") or "").strip())
                run.last_advice = memo
                self._json({"html": advice_html(memo), "meta": memo["_meta"], "postura": memo["recomendacion"]["postura"], "trazabilidad": run.trace[-1]})
            elif u.path == "/api/simulador/iniciar":
                req = json.loads(self._body().decode("utf-8") or "{}")
                run = RUNS.get(req.get("id", ""))
                if not run:
                    return self._json({"error": "Primero carga y analiza un archivo."}, 400)
                try:
                    sim = SYSTEM.simulate_start(run, (req.get("rol") or "").strip(), req.get("escenario") or "auto", req.get("dinamica") or "mixta", req.get("n") or 8, run_id=req["id"])
                except ValueError as e:
                    return self._json({"error": str(e)}, 400)
                with LOCK:
                    SIMS[sim.sim_id] = (run, sim)
                    if len(SIMS) > 60:
                        SIMS.pop(next(iter(SIMS)))
                self._json({**public_view(sim), "trazabilidad": run.trace[-1]})
            elif u.path == "/api/simulador/evaluar":
                req = json.loads(self._body().decode("utf-8") or "{}")
                pair = SIMS.get(req.get("sim_id", ""))
                if not pair:
                    return self._json({"error": "Simulación no encontrada o vencida: inicia una nueva."}, 400)
                run, sim = pair
                rep = SYSTEM.simulate_grade(run, sim, req.get("respuestas") or {})
                self._json({**rep, "trazabilidad": run.trace[-1]})
            else:
                self._json({"error": "no encontrado"}, 404)
        except ValueError as e:
            self._json({"error": f"No pude leer el archivo: {e}"}, 400)
        except Exception as e:  # noqa: BLE001
            self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    def _analyze(self, data: bytes, name: str):
        run = SYSTEM.analyze_bytes(data, name)
        rid = uuid.uuid4().hex[:10]
        with LOCK:
            RUNS[rid] = run
            if len(RUNS) > 25:
                RUNS.pop(next(iter(RUNS)))
        out = _run_summary(run)
        out["id"] = rid
        self._json(out)


def serve(port: int = 8765, open_browser: bool = True):
    global SYSTEM
    SYSTEM = MultiAgentSystem(llm_from_env())
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Sistema multiagente listo en {url}  ·  motor: {SYSTEM.llm.name}")
    if open_browser:
        import webbrowser
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")


PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sistema Multiagente · Analista y Consejero</title><style>/*CSS*/
header.top{background:var(--card);border-bottom:1px solid var(--line);padding:12px 16px;position:sticky;top:0;z-index:5}
header.top .in{max-width:1040px;margin:0 auto;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header.top h1{font-size:17px;margin:0;flex:1}header.top .eng{font-size:12px;color:var(--muted)}
.drop{border:2px dashed var(--line);border-radius:12px;padding:22px;text-align:center;background:var(--card);cursor:pointer;transition:.15s}.drop:hover,.drop.on{border-color:var(--accent);background:var(--accent-soft)}
.btn{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:8px 14px;font:inherit;cursor:pointer}.btn.ghost{background:transparent;color:var(--accent);border:1px solid var(--accent)}.btn:disabled{opacity:.5;cursor:wait}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.chip{border:1px solid var(--line);border-radius:99px;padding:3px 10px;font-size:12.5px;background:var(--card);cursor:pointer;color:var(--ink)}.chip:hover{border-color:var(--accent);color:var(--accent)}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin:18px 0 8px;overflow-x:auto}.tab{padding:8px 14px;border:0;background:none;font:inherit;color:var(--muted);cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap}.tab.on{color:var(--accent);border-color:var(--accent);font-weight:600}
.pane{display:none}.pane.on{display:block}
.pipe{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}.stage{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:12.5px}.stage b{display:block;font-size:13px}.stage.tool{border-style:dashed}.stage.g{border-color:var(--warn)}
textarea,input[type=text]{width:100%;font:inherit;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink)}textarea{min-height:84px;resize:vertical}
.bubble{background:var(--accent-soft);border-radius:10px;padding:8px 12px;margin:14px 0 6px;max-width:92%;margin-left:auto;white-space:pre-wrap}.memo{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:6px 0 18px}
.spin{display:inline-block;width:14px;height:14px;border:2px solid var(--line);border-top-color:var(--accent);border-radius:50%;animation:s .8s linear infinite;vertical-align:-2px;margin-right:6px}@keyframes s{to{transform:rotate(360deg)}}
.err{background:#fde8ec;color:#8a1230;border-radius:8px;padding:10px 12px;margin:10px 0}@media (prefers-color-scheme:dark){.err{background:#3a1520;color:#fda4b5}}
.row{display:grid;grid-template-columns:1fr 2fr;gap:10px}@media(max-width:640px){.row{grid-template-columns:1fr}}
/* ---- Agente 6 · Simulador de crisis ---- */
.howto{background:var(--accent-soft);border:1px solid var(--accent);border-radius:12px;padding:10px 14px;margin:6px 0 14px}.howto summary{cursor:pointer;font-weight:700;color:var(--accent)}
.steps{margin:.6em 0 .4em;padding-left:1.3em}.steps li{margin:.35em 0}.steps strong{color:var(--accent)}
dialog{border:1px solid var(--line);border-radius:14px;background:var(--card);color:var(--ink);max-width:min(560px,92vw);padding:18px 20px}dialog::backdrop{background:rgba(0,0,0,.55)}
.simcard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:10px 0}.simcard h3{margin:.2em 0 .6em;font-size:15px;color:var(--accent)}
.rolegrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}
label.rolecard,label.opt,label.pill{display:block;border:2px solid var(--line);border-radius:12px;padding:10px 12px;background:var(--card);cursor:pointer;transition:.12s}
label.rolecard:hover,label.opt:hover,label.pill:hover{border-color:var(--accent)}label.sel{border-color:var(--accent)!important;background:var(--accent-soft)}
label.rolecard span{display:block;font-size:12.5px;color:var(--muted);margin-top:3px}label.rolecard input,label.opt input,label.pill input{position:absolute;opacity:0;pointer-events:none}
.pills{display:flex;flex-wrap:wrap;gap:8px}label.pill{padding:6px 12px;border-radius:99px;font-size:13px}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:12px}
select.sel-in{width:100%;font:inherit;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink)}select.inline{display:inline-block;width:auto;max-width:100%;margin:0 4px;border-color:var(--accent)}
.bar{height:8px;background:var(--line);border-radius:99px;overflow:hidden;margin:6px 0 10px}.bar>i{display:block;height:100%;background:var(--accent);transition:width .25s}
.qcard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}.qcard .q{font-size:16px;font-weight:600;margin:.5em 0 .8em}
label.opt{margin:7px 0;display:flex;gap:8px}label.opt b{color:var(--accent)}.vf{display:grid;grid-template-columns:1fr 1fr;gap:10px}.vf label.opt{justify-content:center;font-weight:700;font-size:16px;padding:14px}
.pairrow{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-items:center;padding:6px 0;border-bottom:1px dashed var(--line)}@media(max-width:640px){.pairrow{grid-template-columns:1fr}}
.sentence{font-size:16px;line-height:2.2}.dots{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}.dot{width:30px;height:30px;border-radius:50%;border:2px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer;font:inherit;font-size:12.5px}.dot.ok{background:var(--accent-soft);border-color:var(--accent)}.dot.cur{outline:3px solid var(--accent);outline-offset:1px}
.nav{display:flex;justify-content:space-between;gap:8px;margin-top:10px;flex-wrap:wrap}
.ring{--p:0;width:132px;height:132px;border-radius:50%;background:conic-gradient(var(--accent) calc(var(--p)*1%),var(--line) 0);display:grid;place-items:center;flex:none}.ring>div{width:98px;height:98px;border-radius:50%;background:var(--card);display:grid;place-items:center;text-align:center;font-size:26px;font-weight:800}.ring small{display:block;font-size:11px;color:var(--muted);font-weight:500}
.repTop{display:flex;gap:18px;align-items:center;flex-wrap:wrap}.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 14px;min-width:150px}.stat .v{font-size:22px;font-weight:800}.stat .l{font-size:12px;color:var(--muted)}
.crow{display:grid;grid-template-columns:minmax(150px,230px) 1fr 64px;gap:10px;align-items:center;margin:6px 0;font-size:13.5px}.crow .bar{margin:0}.crow .bar>i.bajo{background:var(--bad)}.crow .bar>i.medio{background:var(--warn)}.crow .bar>i.alto{background:var(--ok)}
.rv{border:1px solid var(--line);border-radius:8px;margin:6px 0;background:var(--card)}.rv summary{cursor:pointer;padding:8px 12px;display:flex;gap:8px;align-items:center}.rv .body{padding:4px 14px 12px;font-size:13.5px}.rv .body p{margin:.35em 0}
.tag.correcta{background:var(--ok);color:#fff;border-color:var(--ok)}.tag.parcial{background:var(--warn);color:#fff;border-color:var(--warn)}.tag.incorrecta{background:var(--bad);color:#fff;border-color:var(--bad)}
.hint{font-size:12.5px;color:var(--muted);margin:6px 0}
</style></head><body><!--WM-->
<header class="top"><div class="in"><h1>🧭 Sistema Multiagente · Analista y Consejero estratégico</h1><a class="eng" href="/expediente" target="_blank" style="color:var(--accent)">Expediente técnico</a><span class="eng" id="eng">…</span></div></header>
<div class="wrap" style="padding-bottom:0"><div class="firma"><!--FIRMA--></div></div><!--FOOT-->
<div class="wrap">
 <div class="drop" id="drop"><strong>Arrastra aquí tu base de datos</strong> (CSV, Excel, JSON) o <u>haz clic para elegirla</u><br><span class="muted">Sin configurar nada: el sistema infiere tipos, limpia, analiza e interpreta cualquier estructura.</span>
  <input type="file" id="file" accept=".csv,.tsv,.txt,.xlsx,.xls,.json,.jsonl,.ndjson" hidden></div>
 <div class="chips" id="demos"><span class="muted" style="font-size:12.5px;padding:3px 0">Ejemplos:</span></div>
 <div id="status"></div>
 <div id="app" style="display:none">
  <div class="tabs"><button class="tab on" data-t="informe">📄 Informe</button><button class="tab" data-t="consejero">🧭 Consejero estratégico</button><button class="tab" data-t="sim">🎭 Simulador de crisis</button><button class="tab" data-t="traza">🔗 Trazabilidad de agentes</button></div>
  <div class="pane on" id="p-informe"><div style="display:flex;gap:8px;justify-content:flex-end"><a class="btn ghost" id="dl-html" style="text-decoration:none">Descargar HTML</a><a class="btn ghost" id="dl-md" style="text-decoration:none">Descargar Markdown</a></div><div id="informe"></div></div>
  <div class="pane" id="p-consejero">
   <div class="callout"><strong>Tu consejero no está para darte la razón.</strong> Cuéntale una decisión («Voy a cerrar la sucursal X»), hazle una pregunta («¿Qué área tiene más quejas?») o pídele que explore («Ayúdame a decidir qué priorizar»). Cuestionará tus supuestos, buscará sesgos y contrastará con los datos.</div>
   <div class="row" style="margin-top:10px"><div><label class="sub">Tu rol (opcional; también lo detecto si lo escribes)</label><input type="text" id="rol" placeholder="p. ej. Gerente comercial, Secretario de salud, Rector…"></div>
    <div><label class="sub">Tu decisión, pregunta o inquietud</label><textarea id="msg" placeholder="Escribe aquí. Ej.: Voy a subir los precios 15% porque estoy seguro de que no afectará las ventas."></textarea></div></div>
   <div class="chips" id="ejemplos"></div>
   <div style="display:flex;gap:8px;margin:6px 0"><button class="btn" id="send">Consultar al consejero</button><button class="btn ghost" id="explore">Explorar sin decisión previa</button></div>
   <div id="chat"></div>
  </div>
  <div class="pane" id="p-sim">
   <details class="howto" id="howto" open>
    <summary>📘 Instrucciones de Uso del Simulador</summary>
    <ol class="steps">
     <li><strong>Selecciona tu Rol</strong> (Gerente, Supervisor, Asistente, Auxiliar).</li>
     <li>Haz clic en <strong>«Iniciar Simulación de Crisis»</strong>.</li>
     <li><strong>Responde a los escenarios</strong> generados usando los formatos interactivos (opción múltiple, Falso/Verdadero, emparejamiento y desplegables).</li>
     <li><strong>Recibe tu evaluación directiva final</strong> con tu puntaje y tu % de éxito.</li>
    </ol>
    <p class="hint">Las preguntas se generan con <strong>tus datos reales</strong> (el choque de la crisis es un supuesto del ejercicio). Cada rol se evalúa con criterios distintos: lo ideal para un Auxiliar no es lo ideal para un Gerente.</p>
    <button class="btn ghost" id="howto-modal" type="button">Ver instrucciones en ventana</button>
   </details>
   <dialog id="dlg"><h3 style="margin-top:0">📘 Instrucciones de Uso del Simulador</h3>
    <ol class="steps"><li><strong>Selecciona tu Rol</strong> (Gerente, Supervisor, Asistente, Auxiliar).</li><li>Haz clic en <strong>«Iniciar Simulación de Crisis»</strong>.</li>
     <li><strong>Responde a los escenarios</strong> generados usando los formatos interactivos (opción múltiple, F/V, desplegables).</li><li><strong>Recibe tu evaluación directiva final</strong> con tu % de éxito.</li></ol>
    <div style="text-align:right"><button class="btn" id="dlg-close" type="button">Entendido</button></div></dialog>
   <div id="sim-setup" class="simcard">
    <h3>Paso 1 · Elige tu rol en la empresa</h3>
    <div class="rolegrid" id="roles" role="radiogroup" aria-label="Rol"></div>
    <div class="grid3">
     <div><h3>Paso 2 · Tipo de crisis</h3><select id="sim-esc" class="sel-in"></select><p class="hint" id="esc-desc"></p></div>
     <div><h3>Dinámica de preguntas</h3><div class="pills" id="dins" role="radiogroup" aria-label="Dinámica"></div></div>
     <div><h3>Número de preguntas</h3><select id="sim-n" class="sel-in"><option value="6">6 (rápida)</option><option value="8" selected>8 (recomendada)</option><option value="10">10 (completa)</option></select></div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:14px"><button class="btn" id="sim-start" type="button" disabled>▶ Iniciar Simulación de Crisis</button><span class="hint" id="sim-hint">Selecciona un rol para continuar.</span></div>
   </div>
   <div id="sim-play" style="display:none"></div>
   <div id="sim-report" style="display:none"></div>
  </div>
  <div class="pane" id="p-traza"><h2>Red de agentes: transferencia de payloads</h2><div class="pipe" id="pipe"></div><h2>Detalle</h2><div class="scroll"><table id="ttab"></table></div><h2>Esquema inferido</h2><div class="scroll"><table id="stab"></table></div></div>
 </div>
</div>
<script>
const $=s=>document.querySelector(s);let RID=null,SUM=null;
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
fetch('/api/estado').then(r=>r.json()).then(e=>{$('#eng').textContent='Motor: '+e.motor+' · prompts '+e.huella});
fetch('/api/demos').then(r=>r.json()).then(l=>{l.forEach(n=>{const b=document.createElement('button');b.className='chip';b.textContent=n;b.onclick=()=>run('/api/demo?archivo='+encodeURIComponent(n),null);$('#demos').appendChild(b)})});
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{document.querySelectorAll('.tab,.pane').forEach(x=>x.classList.remove('on'));t.classList.add('on');$('#p-'+t.dataset.t).classList.add('on')});
const drop=$('#drop'),fi=$('#file');drop.onclick=()=>fi.click();fi.onchange=()=>fi.files[0]&&upload(fi.files[0]);
['dragover','dragenter'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add('on')}));['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove('on')}));
drop.addEventListener('drop',ev=>{const f=ev.dataTransfer.files[0];f&&upload(f)});
function upload(f){run('/api/analizar?nombre='+encodeURIComponent(f.name),f)}
async function run(url,body){
 $('#status').innerHTML='<div class="card"><span class="spin"></span><strong>Los agentes están trabajando…</strong> Auditor → Analista → Intérprete → Redactor</div>';$('#app').style.display='none';
 try{const r=await fetch(url,{method:'POST',body});const j=await r.json();if(!r.ok)throw new Error(j.error||r.statusText);SUM=j;RID=j.id;render(j);$('#status').innerHTML=''}
 catch(e){$('#status').innerHTML='<div class="err"><strong>No se pudo procesar:</strong> '+esc(e.message)+'</div>'}}
function render(j){
 simReset();$('#app').style.display='block';$('#informe').innerHTML=j.informe_html;$('#chat').innerHTML='';
 $('#dl-html').href='/api/descargar/'+j.id+'.html';$('#dl-md').href='/api/descargar/'+j.id+'.md';
 $('#pipe').innerHTML=j.trazabilidad.map(t=>`<div class="stage ${t.motor==='herramienta'?'tool':''} ${t.correcciones_guardrail.length||t.cifras_no_verificadas.length?'g':''}"><b>${esc(t.etapa)}</b>${esc(t.entrada)} → ${esc(t.salida)}<br><span class="muted">${esc(t.motor)} · ${t.ms} ms${t.correcciones_guardrail.length?' · 🛡 '+t.correcciones_guardrail.length+' corrección(es)':''}</span></div>`).join('');
 $('#ttab').innerHTML='<tr><th>Etapa</th><th>Motor</th><th>Intentos</th><th>Guardrails</th></tr>'+j.trazabilidad.map(t=>`<tr><td>${esc(t.etapa)}</td><td>${esc(t.motor)}</td><td>${t.intentos}</td><td>${esc(t.correcciones_guardrail.join(' · ')||'—')}${t.cifras_no_verificadas.length?'<br>Cifras no verificadas: '+esc(t.cifras_no_verificadas.join(', ')):''}</td></tr>`).join('');
 $('#stab').innerHTML='<tr><th>Original</th><th>Normalizado</th><th>Tipo</th><th>Rol</th><th>% nulos</th></tr>'+j.esquema.map(c=>`<tr><td>${esc(c.original||'(vacío)')}</td><td>${esc(c.normalizado)}</td><td>${esc(c.tipo)}</td><td>${esc(c.rol)}</td><td>${c.pct_nulos}</td></tr>`).join('');
 const ex=['Voy a subir los precios 15% porque estoy seguro de que nadie lo notará.','¿Cuál es el grupo con mejor desempeño?','Quiero recortar el presupuesto del área con menor resultado.','Como gerente, voy a invertir en el segmento que más crece.'];
 $('#ejemplos').innerHTML='<span class="muted" style="font-size:12.5px;padding:3px 0">Ejemplos:</span>';ex.forEach(t=>{const b=document.createElement('button');b.className='chip';b.textContent=t;b.onclick=()=>{$('#msg').value=t};$('#ejemplos').appendChild(b)});
}
async function ask(explore){
 const msg=explore?'':$('#msg').value.trim();if(!explore&&!msg){$('#msg').focus();return}
 const c=$('#chat');c.insertAdjacentHTML('afterbegin',`<div class="bubble"><strong>${esc($('#rol').value||'Tú')}:</strong> ${esc(msg||'(Explora y dime qué decisiones debería estar evaluando)')}</div><div class="memo" id="pending"><span class="spin"></span>El consejero está analizando tu planteamiento contra los datos…</div>`);
 $('#send').disabled=$('#explore').disabled=true;
 try{const r=await fetch('/api/consejero',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:RID,mensaje:msg,rol:$('#rol').value})});const j=await r.json();if(!r.ok)throw new Error(j.error);
  $('#pending').outerHTML='<div class="memo">'+j.html+'</div>';$('#msg').value='';SUM.trazabilidad.push(j.trazabilidad);render_trace_only()}
 catch(e){$('#pending').outerHTML='<div class="err">'+esc(e.message)+'</div>'}
 $('#send').disabled=$('#explore').disabled=false}
function drawTrace(){
 $('#pipe').innerHTML=SUM.trazabilidad.map(t=>`<div class="stage ${t.motor==='herramienta'?'tool':''} ${t.correcciones_guardrail.length||t.cifras_no_verificadas.length?'g':''}"><b>${esc(t.etapa)}</b>${esc(t.entrada)} → ${esc(t.salida)}<br><span class="muted">${esc(t.motor)} · ${t.ms} ms${t.correcciones_guardrail.length?' · 🛡 '+t.correcciones_guardrail.length+' corrección(es)':''}</span></div>`).join('');
 $('#ttab').innerHTML='<tr><th>Etapa</th><th>Motor</th><th>Intentos</th><th>Guardrails</th></tr>'+SUM.trazabilidad.map(t=>`<tr><td>${esc(t.etapa)}</td><td>${esc(t.motor)}</td><td>${t.intentos}</td><td>${esc(t.correcciones_guardrail.join(' · ')||'—')}${t.cifras_no_verificadas.length?'<br>Cifras no verificadas: '+esc(t.cifras_no_verificadas.join(', ')):''}</td></tr>`).join('')}
function render_trace_only(){drawTrace()}
/* ====================== Agente 6 · Simulador de crisis ====================== */
let SC=null,SIM=null,QI=0,ANS={},ROLE=null,DIN='mixta';
const ICON={Auxiliar:'🛠️',Asistente:'📊',Supervisor:'🧭',Gerente:'🏛️'},FMT={opcion_multiple:'Opción múltiple',verdadero_falso:'Falso / Verdadero',emparejamiento:'Emparejamiento',completar:'Completar la frase'};
fetch('/api/simulador/config').then(r=>r.json()).then(c=>{SC=c;buildSetup()});
$('#howto-modal').onclick=()=>$('#dlg').showModal();$('#dlg-close').onclick=()=>$('#dlg').close();
function buildSetup(){
 $('#roles').innerHTML=SC.roles.map(r=>`<label class="rolecard" data-r="${esc(r.id)}"><input type="radio" name="rol" value="${esc(r.id)}"><strong>${ICON[r.id]||''} ${esc(r.id)}</strong><span>Tú ${esc(r.alcance)}.</span></label>`).join('');
 $('#roles').querySelectorAll('input').forEach(i=>i.onchange=()=>{ROLE=i.value;$('#roles').querySelectorAll('label').forEach(l=>l.classList.toggle('sel',l.dataset.r===ROLE));$('#sim-start').disabled=false;$('#sim-hint').textContent='Rol elegido: '+ROLE+'. ¡Listo para iniciar!'});
 $('#sim-esc').innerHTML=SC.escenarios.map(e=>`<option value="${esc(e.id)}">${esc(e.nombre)}</option>`).join('');
 const ed=()=>{$('#esc-desc').textContent=(SC.escenarios.find(e=>e.id===$('#sim-esc').value)||{}).descripcion||''};$('#sim-esc').onchange=ed;ed();
 $('#dins').innerHTML=SC.dinamicas.map((d,i)=>`<label class="pill ${i===0?'sel':''}" data-d="${esc(d.id)}"><input type="radio" name="din" value="${esc(d.id)}" ${i===0?'checked':''}>${esc(d.nombre)}</label>`).join('');
 $('#dins').querySelectorAll('input').forEach(i=>i.onchange=()=>{DIN=i.value;$('#dins').querySelectorAll('label').forEach(l=>l.classList.toggle('sel',l.dataset.d===DIN))});
 $('#sim-start').onclick=simStart}
function simReset(){SIM=null;QI=0;ANS={};$('#sim-play').style.display='none';$('#sim-report').style.display='none';$('#sim-setup').style.display='block';$('#sim-play').innerHTML='';$('#sim-report').innerHTML=''}
async function simStart(){
 if(!ROLE||!RID)return;const b=$('#sim-start');b.disabled=true;$('#sim-hint').innerHTML='<span class="spin"></span>El Agente 6 está construyendo tu crisis con tus datos…';
 try{const r=await fetch('/api/simulador/iniciar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:RID,rol:ROLE,escenario:$('#sim-esc').value,dinamica:DIN,n:+$('#sim-n').value})});
  const j=await r.json();if(!r.ok)throw new Error(j.error);SIM=j;QI=0;ANS={};SUM.trazabilidad.push(j.trazabilidad);drawTrace();
  $('#sim-setup').style.display='none';$('#sim-report').style.display='none';$('#sim-play').style.display='block';renderPlay();window.scrollTo({top:0,behavior:'smooth'})}
 catch(e){$('#sim-hint').innerHTML='<span style="color:var(--bad)">No se pudo iniciar: '+esc(e.message)+'</span>'}
 b.disabled=false}
function answered(p){const a=ANS[p.id];if(a===undefined||a===null||a==='')return false;if(typeof a==='object')return Object.values(a).some(v=>v);return true}
function renderPlay(){
 const c=SIM.contexto,n=SIM.preguntas.length,q=SIM.preguntas[QI],cur=ANS[q.id];let body='';
 if(q.formato==='opcion_multiple')body=q.contenido.opciones.map(o=>`<label class="opt ${cur===o.id?'sel':''}"><input type="radio" name="q" value="${o.id}" ${cur===o.id?'checked':''}><b>${o.id})</b><span>${esc(o.texto)}</span></label>`).join('');
 else if(q.formato==='verdadero_falso')body=`<p class="sentence" style="line-height:1.5">«${esc(q.contenido.afirmacion)}»</p><div class="vf"><label class="opt ${cur===true?'sel':''}"><input type="radio" name="q" value="true" ${cur===true?'checked':''}>✔ Verdadero</label><label class="opt ${cur===false?'sel':''}"><input type="radio" name="q" value="false" ${cur===false?'checked':''}>✘ Falso</label></div>`;
 else if(q.formato==='emparejamiento'){const a=cur||{};body=q.contenido.causas.map(x=>`<div class="pairrow"><div><strong>${esc(x.texto)}</strong></div><select class="sel-in" data-c="${x.id}"><option value="">— elige la solución —</option>${q.contenido.soluciones.map(s=>`<option value="${s.id}" ${a[x.id]===s.id?'selected':''}>${esc(s.texto)}</option>`).join('')}</select></div>`).join('')}
 else if(q.formato==='completar'){const a=cur||{};body='<p class="sentence">'+q.contenido.huecos.map(h=>`${esc(h.antes)} <select class="sel-in inline" data-h="${h.id}"><option value="">— elige —</option>${h.opciones.map(o=>`<option value="${o.id}" ${a[h.id]===o.id?'selected':''}>${esc(o.texto)}</option>`).join('')}</select> ${esc(h.despues)}`).join(' ')+'</p>'}
 const done=SIM.preguntas.filter(answered).length;
 $('#sim-play').innerHTML=`<div class="simcard"><div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><strong>🎭 ${esc(c.titulo)}</strong><span class="tag">Rol: ${esc(SIM.rol)}</span></div><p>${esc(c.narrativa)}</p>
  <details><summary class="hint" style="cursor:pointer">Datos clave y supuestos del ejercicio</summary><ul>${c.datos_clave.map(d=>`<li>${esc(d)}</li>`).join('')}</ul><ul class="muted">${c.supuestos.map(d=>`<li>${esc(d)}</li>`).join('')}</ul></details></div>
  <div class="bar" aria-label="Progreso"><i style="width:${100*done/n}%"></i></div><div class="hint" id="sim-count">${done} de ${n} respondidas</div>
  <div class="qcard"><div><span class="tag">${FMT[q.formato]}</span> <span class="tag">${esc(q.competencia)}</span> <span class="muted" style="font-size:12.5px">Pregunta ${QI+1} de ${n}</span></div><div class="q">${esc(q.enunciado)}</div><div id="qbody">${body}</div></div>
  <div class="dots">${SIM.preguntas.map((p,i)=>`<button class="dot ${i===QI?'cur':''} ${answered(p)?'ok':''}" data-i="${i}" type="button" aria-label="Ir a la pregunta ${i+1}">${i+1}</button>`).join('')}</div>
  <div class="nav"><button class="btn ghost" id="q-prev" type="button" ${QI===0?'disabled':''}>← Anterior</button><span><button class="btn ghost" id="q-cancel" type="button">Cancelar</button> ${QI<n-1?'<button class="btn" id="q-next" type="button">Siguiente →</button>':'<button class="btn" id="q-fin" type="button">✔ Finalizar y ver mi evaluación</button>'}</span></div>`;
 const P=$('#sim-play');
 P.querySelectorAll('#qbody input[type=radio]').forEach(i=>i.onchange=()=>{ANS[q.id]=q.formato==='verdadero_falso'?(i.value==='true'):i.value;renderPlay()});
 P.querySelectorAll('#qbody select[data-c]').forEach(s=>s.onchange=()=>{ANS[q.id]=Object.assign({},ANS[q.id],{[s.dataset.c]:s.value});refreshDots()});
 P.querySelectorAll('#qbody select[data-h]').forEach(s=>s.onchange=()=>{ANS[q.id]=Object.assign({},ANS[q.id],{[s.dataset.h]:s.value});refreshDots()});
 P.querySelectorAll('.dot').forEach(d=>d.onclick=()=>{QI=+d.dataset.i;renderPlay()});
 const pv=$('#q-prev'),nx=$('#q-next'),fn=$('#q-fin');pv.onclick=()=>{QI--;renderPlay()};if(nx)nx.onclick=()=>{QI++;renderPlay()};if(fn)fn.onclick=simFinish;
 $('#q-cancel').onclick=()=>{if(confirm('¿Cancelar la simulación? Perderás tus respuestas.'))simReset()}}
function refreshDots(){const n=SIM.preguntas.length,done=SIM.preguntas.filter(answered).length;$('#sim-play .bar>i').style.width=(100*done/n)+'%';$('#sim-count').textContent=done+' de '+n+' respondidas';
 $('#sim-play').querySelectorAll('.dot').forEach((d,i)=>d.classList.toggle('ok',answered(SIM.preguntas[i])))}
async function simFinish(){
 const falt=SIM.preguntas.filter(p=>!answered(p)).length;if(falt&&!confirm('Tienes '+falt+' pregunta(s) sin responder (puntúan 0). ¿Finalizar de todos modos?'))return;
 $('#sim-play').insertAdjacentHTML('beforeend','<p><span class="spin"></span>Calculando tu evaluación directiva…</p>');
 try{const r=await fetch('/api/simulador/evaluar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sim_id:SIM.sim_id,respuestas:ANS})});const j=await r.json();if(!r.ok)throw new Error(j.error);
  SUM.trazabilidad.push(j.trazabilidad);drawTrace();renderReport(j)}catch(e){$('#sim-play').insertAdjacentHTML('beforeend','<div class="err">'+esc(e.message)+'</div>')}}
function renderReport(j){
 const lv=n=>n==='Alto'?'alto':n==='Medio'?'medio':'bajo';
 $('#sim-play').style.display='none';const R=$('#sim-report');R.style.display='block';
 R.innerHTML=`<div class="simcard"><h3>📋 Reporte de Desempeño Final · ${esc(j.rol)}</h3>
  <div class="repTop"><div class="ring" style="--p:${j.puntaje_pct}"><div><span>${j.puntaje_pct}%<small>puntaje</small></span></div></div>
   <div style="display:flex;gap:10px;flex-wrap:wrap"><div class="stat"><div class="v">${j.exito_decisiones_pct===null?'N/A':j.exito_decisiones_pct+'%'}</div><div class="l">% de éxito de las decisiones</div></div><div class="stat"><div class="v">${esc(j.decisiones_optimas)}</div><div class="l">decisiones óptimas</div></div><div class="stat"><div class="v">${esc(j.nivel_desempeno)}</div><div class="l">nivel de desempeño</div></div></div></div>
  ${j.nota?`<p class="hint">${esc(j.nota)}</p>`:''}
  <h3 style="margin-top:16px">Diagnóstico de habilidades según tu rol (${esc(j.rol)})</h3><p>${esc(j.diagnostico_rol)}</p><p><strong>Preparación para el rol:</strong> ${esc(j.preparacion_para_el_rol)}</p>
  <h3>Competencias evaluadas</h3>${j.competencias.map(c=>`<div class="crow"><div>${esc(c.nombre)} <span class="tag">${esc(c.importancia_rol)} para tu rol</span></div><div class="bar"><i class="${lv(c.nivel)}" style="width:${c.pct}%"></i></div><div><strong>${c.pct}%</strong></div></div>`).join('')}
  <h3>Recomendaciones de mejora</h3><ul>${j.recomendaciones.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>
  <h3>Revisión pregunta por pregunta</h3>${j.revision.map((x,i)=>`<details class="rv"><summary><span class="tag ${x.estado}">${x.estado} · ${x.puntaje_pct}%</span> <span>${i+1}. ${esc(x.enunciado)}</span></summary><div class="body"><p><strong>Tu respuesta:</strong> ${esc(x.tu_respuesta)}</p><p><strong>Respuesta ideal:</strong> ${esc(x.respuesta_correcta)}</p><p class="muted">${esc(x.explicacion)}</p><p class="hint">${esc(x.competencia)} · ${esc(FMT[x.formato])}</p></div></details>`).join('')}
  <div class="nav" style="justify-content:flex-start"><button class="btn" id="rp-again" type="button">↻ Nueva simulación (mismo rol)</button><button class="btn ghost" id="rp-change" type="button">Cambiar rol o configuración</button><button class="btn ghost" id="rp-print" type="button">🖨 Imprimir / PDF</button></div></div>`;
 $('#rp-again').onclick=()=>{simReset();$('#sim-setup').style.display='none';simStart()};$('#rp-change').onclick=simReset;$('#rp-print').onclick=()=>window.print();window.scrollTo({top:0,behavior:'smooth'})}
$('#send').onclick=()=>ask(false);$('#explore').onclick=()=>ask(true);
$('#msg').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey))ask(false)});
</script></body></html>"""

