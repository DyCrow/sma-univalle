"""Generador reproducible de los datasets de prueba de la Fase 4 (con 'verdad de terreno' para auditar).

A  Ventas transaccionales (cuantitativa / comercial)
B  PQR con texto libre (cualitativa)
C  Dataset con RUIDO (hasta 30% de nulos, columnas sin nombre, formatos mixtos, duplicados, nulos ocultos)
D  Producción en JSON anidado
E  Indicadores sociales en Excel (con filas de título y varias hojas)
F  'Base sorpresa' sin encabezado, latin-1, punto y coma, coma decimal (simula la prueba en vivo)
G  Muestra diminuta (12 filas) para probar cautela por tamaño de muestra
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
TRUTH: dict = {}


def gen_ventas(n=6000, seed=42, noisy=False):
    rng = np.random.default_rng(seed)
    start, end = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-06-30")
    days = (end - start).days + 1
    # estacionalidad: nov-dic altos, ene bajo; tendencia creciente
    day_idx = np.arange(days)
    dts = start + pd.to_timedelta(day_idx, unit="D")
    w = (1 + 0.0012 * day_idx) * np.where(dts.month.isin([11, 12]), 1.6, np.where(dts.month == 1, 0.7, 1.0)) * np.where(dts.dayofweek >= 5, 1.25, 1.0)
    w = w / w.sum()
    fecha = dts[rng.choice(days, size=n, p=w)]
    suc = rng.choice(["Norte", "Sur", "Centro", "Oriente", "Occidente"], size=n, p=[0.30, 0.18, 0.27, 0.13, 0.12])
    cats = {"Electrónica": (["Televisor 55", "Portátil 14", "Celular X", "Audífonos BT"], 1_200_000), "Hogar": (["Licuadora", "Nevera mini", "Juego de sábanas", "Lámpara LED"], 220_000),
            "Moda": (["Chaqueta", "Jeans", "Zapatillas", "Camiseta"], 130_000), "Alimentos": (["Café 500g", "Aceite 3L", "Arroz 5kg", "Chocolate"], 28_000), "Deportes": (["Bicicleta", "Balón", "Pesas 10kg", "Tenis running"], 310_000)}
    cat = rng.choice(list(cats), size=n, p=[0.30, 0.18, 0.2, 0.2, 0.12])
    prod = np.array([rng.choice(cats[c][0]) for c in cat])
    base = np.array([cats[c][1] for c in cat])
    price = np.round(base * rng.lognormal(0, 0.18, n), -2)
    qty = rng.integers(1, 6, size=n)
    qty = np.where(cat == "Alimentos", rng.integers(2, 9, size=n), qty)
    disc = rng.choice([0, 5, 10, 15], size=n, p=[0.55, 0.2, 0.15, 0.10])
    disc = np.where(suc == "Oriente", np.minimum(disc + 10, 25), disc)
    total = np.round(qty * price * (1 - disc / 100), 0)
    df = pd.DataFrame({
        "id_transaccion": [f"T{i + 1:06d}" for i in range(n)], "fecha": fecha, "sucursal": suc, "categoria": cat, "producto": prod,
        "cantidad": qty, "precio_unitario": price, "descuento_pct": disc, "total": total,
        "medio_pago": rng.choice(["Tarjeta", "Efectivo", "Transferencia", "PSE"], size=n, p=[0.5, 0.2, 0.15, 0.15]),
        "vendedor": rng.choice([f"Vendedor {i:02d}" for i in range(1, 16)], size=n),
    })
    out_idx = rng.choice(n, 3, replace=False)  # 3 transacciones atípicas x40
    df.loc[out_idx, "total"] = df.loc[out_idx, "total"] * 40
    df = df.sort_values("fecha").reset_index(drop=True)
    df["id_transaccion"] = [f"T{i + 1:06d}" for i in range(n)]
    truth = {"total_ventas": float(df["total"].sum()), "n": n, "top_sucursal": df.groupby("sucursal")["total"].sum().idxmax(),
             "top_categoria": df.groupby("categoria")["total"].sum().idxmax(), "outliers_plantados": 3,
             "mes_pico": str(df.assign(m=df["fecha"].dt.to_period("M")).groupby("m")["total"].sum().idxmax()),
             "ids_top3_totales": df.nlargest(3, "total")["id_transaccion"].tolist(), "fecha_min": str(df["fecha"].min().date()), "fecha_max": str(df["fecha"].max().date())}
    return df, truth


def make_A():
    df, truth = gen_ventas()
    out = df.copy()
    # ~18% de las fechas en formato dd/mm/aaaa (prueba clásica de la guía: conversión de fechas)
    rng = np.random.default_rng(7)
    f = out["fecha"].dt.strftime("%Y-%m-%d").astype(object)
    sel = rng.random(len(out)) < 0.18
    f[sel] = out.loc[sel, "fecha"].dt.strftime("%d/%m/%Y")
    out["fecha"] = f
    out["total"] = out["total"].astype(int)
    out.to_csv(OUT / "A_ventas_transaccionales.csv", index=False)
    truth["fechas_formato_dmy"] = int(sel.sum())
    TRUTH["A"] = truth


FRAG = {
    "neg_tiempo": ["Llevo {n} días esperando respuesta a mi solicitud y nadie me informa nada, es una demora inaceptable.", "El trámite está vencido hace semanas y siguen sin respuesta, un servicio muy lento.", "Radiqué hace {n} días y todavía permanece pendiente; pésima atención al cliente."],
    "neg_cobro": ["Me cobraron dos veces la factura del mes y no me han devuelto el dinero, exijo el reembolso.", "Hay un cobro indebido en mi cuenta y la tarifa no corresponde a lo contratado, estoy muy molesto.", "La factura llegó con un cargo que no reconozco, quiero reclamar la devolución."],
    "neg_calidad": ["El producto llegó dañado y defectuoso, la calidad es pésima y no funciona.", "Compré un artículo que falló a los {n} días, es mala calidad y piden pagar la garantía.", "El servicio técnico dejó el equipo peor de como estaba, resultado deficiente."],
    "neg_trato": ["El funcionario fue grosero e irrespetuoso, un trato inaceptable para un usuario.", "Me atendieron mal en la sede, el asesor no sabía nada y fue muy descortés.", "Pésima atención del personal, nadie quiso ayudarme."],
    "neg_entrega": ["El pedido nunca llegó y la guía de envío no aparece, el transporte perdió mi paquete.", "La entrega se retrasó {n} días y el domicilio llegó incompleto."],
    "neg_digital": ["La plataforma web no funciona, siempre sale un error y no puedo cambiar la clave.", "La aplicación se cae constantemente y el portal es muy lento."],
    "pos": ["Quiero felicitar al asesor que me atendió, excelente servicio y muy amable, muchas gracias.", "Agradezco la rápida solución de mi caso, todo quedó resuelto en un día.", "Excelente atención en la sede, el personal fue cordial y eficiente, lo recomiendo."],
    "neu": ["Solicito información sobre los requisitos para el trámite de un certificado.", "Necesito conocer el horario de atención y los documentos necesarios para la cita.", "Quisiera saber cómo actualizar mis datos en el sistema, por favor."],
    "sug": ["Sugiero habilitar más puntos de atención y publicar mejor la información de los trámites.", "Recomiendo mejorar la señalización de la sede y ampliar el horario."],
}


def make_B(n=2000, seed=11):
    rng = np.random.default_rng(seed)
    areas = ["Facturación", "Atención al usuario", "Soporte técnico", "Logística", "Jurídica"]
    area = rng.choice(areas, size=n, p=[0.28, 0.25, 0.2, 0.17, 0.10])
    rows, labels = [], []
    for a in area:
        if a == "Facturación":
            p = {"neg_cobro": .55, "neg_tiempo": .15, "pos": .05, "neu": .15, "sug": .10}
        elif a == "Logística":
            p = {"neg_entrega": .5, "neg_tiempo": .2, "pos": .08, "neu": .12, "sug": .10}
        elif a == "Soporte técnico":
            p = {"neg_calidad": .35, "neg_digital": .25, "neg_tiempo": .1, "pos": .12, "neu": .18}
        elif a == "Jurídica":
            p = {"neg_tiempo": .35, "neu": .4, "neg_trato": .1, "pos": .05, "sug": .10}
        else:
            p = {"neg_trato": .3, "neg_tiempo": .15, "pos": .2, "neu": .25, "sug": .10}
        k = rng.choice(list(p), p=np.array(list(p.values())) / sum(p.values()))
        txt = rng.choice(FRAG[k]).format(n=int(rng.integers(5, 40)))
        rows.append(txt)
        labels.append("neg" if k.startswith("neg") else "pos" if k == "pos" else "neu")
    tipo_map = {"neg_cobro": "Reclamo", "neg_tiempo": "Queja", "neg_calidad": "Reclamo", "neg_trato": "Queja", "neg_entrega": "Reclamo", "neg_digital": "Queja", "pos": "Felicitación", "neu": "Petición", "sug": "Sugerencia"}
    # tipo registrado por el usuario (con variantes de escritura)
    tipos = []
    for lab, txt in zip(labels, rows):
        base = "Queja" if lab == "neg" else "Felicitación" if lab == "pos" else "Petición"
        if "Sugiero" in txt or "Recomiendo" in txt:
            base = "Sugerencia"
        tipos.append(base)
    variants = {"Queja": ["Queja", "queja", "QUEJA", "Queja ", "Quejá"], "Petición": ["Petición", "Peticion", "PETICIÓN", "petición"], "Felicitación": ["Felicitación", "felicitacion"], "Sugerencia": ["Sugerencia", "sugerencia "]}
    tipos_v = [rng.choice(variants[t]) if rng.random() < 0.3 else t for t in tipos]
    fecha = pd.to_datetime("2025-01-01") + pd.to_timedelta(rng.integers(0, 330, n), unit="D")
    estado = rng.choice(["Resuelto", "En trámite", "Pendiente", "Cerrado"], size=n, p=[0.45, 0.2, 0.15, 0.2])
    dias = np.where(area == "Logística", rng.gamma(4, 3.5, n), rng.gamma(3, 2.4, n)).round(0)
    dias = np.where(estado == "Pendiente", np.nan, dias)
    df = pd.DataFrame({"radicado": [f"PQR-2025-{i + 1:06d}" for i in range(n)], "fecha_radicacion": fecha.strftime("%Y-%m-%d"),
                       "canal": rng.choice(["Web", "Telefónico", "Presencial", "Correo", "Redes sociales"], size=n, p=[0.3, 0.25, 0.2, 0.15, 0.1]),
                       "tipo_solicitud": tipos_v, "area_responsable": area, "descripcion": rows, "estado": estado, "dias_respuesta": dias})
    df.to_csv(OUT / "B_pqr_texto_libre.csv", index=False, encoding="utf-8")
    truth_pct_neg = float(np.mean(np.array(labels) == "neg") * 100)
    area_neg = pd.Series(np.array(labels) == "neg").groupby(area).mean().sort_values(ascending=False)
    TRUTH["B"] = {"n": n, "pct_negativo_real": truth_pct_neg, "area_mas_negativa": area_neg.index[0], "labels": labels, "tipos_canonicos": 4,
                  "area_mas_lenta": pd.Series(dias).groupby(area).mean().idxmax()}


def make_C(seed=5):
    """Dataset con RUIDO: nulos hasta 30%, columnas sin nombre, formatos mixtos, duplicados, nulos ocultos."""
    rng = np.random.default_rng(seed)
    base, _ = gen_ventas(n=3000, seed=99)
    n = len(base)
    df = base.copy()
    truth_nulls = {}
    # nulos aleatorios (hasta 30%) en distintas columnas
    for col, p in {"sucursal": 0.30, "categoria": 0.12, "cantidad": 0.22, "precio_unitario": 0.25, "descuento_pct": 0.30, "medio_pago": 0.18, "vendedor": 0.08, "total": 0.05}.items():
        mask = rng.random(n) < p
        truth_nulls[col] = float(mask.mean() * 100)
        df[col] = df[col].astype(object)
        df.loc[mask, col] = None
    # nulos con distintos marcadores (ocultos)
    for col in ("sucursal", "medio_pago", "vendedor", "categoria"):
        idx = df.index[df[col].isna()]
        marks = rng.choice(["N/A", "-", "?", "", "sin dato", "NULL"], size=len(idx))
        df.loc[idx, col] = marks
    # fechas mezcladas (4 formatos)
    f = df["fecha"]
    r = rng.random(n)
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    fm = []
    for ts, x in zip(f, r):
        if x < 0.35:
            fm.append(ts.strftime("%Y-%m-%d"))
        elif x < 0.65:
            fm.append(ts.strftime("%d/%m/%Y"))
        elif x < 0.85:
            fm.append(f"{ts.day} de {meses[ts.month - 1]} de {ts.year}")
        else:
            fm.append(ts.strftime("%d-%m-%Y"))
    df["fecha"] = fm
    mask = rng.random(n) < 0.06
    truth_nulls["fecha"] = float(mask.mean() * 100)
    df.loc[mask, "fecha"] = np.where(rng.random(mask.sum()) < 0.5, "", "N/A")
    truth_total_sum = float(pd.to_numeric(df["total"], errors="coerce").sum())
    # moneda con símbolos y formatos mixtos
    def fmt_money(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return v
        x = rng.random()
        if x < 0.4:
            return f"$ {int(v):,}".replace(",", ".")
        if x < 0.7:
            return str(int(v))
        return f"{int(v)},00"
    df["total"] = [fmt_money(v) for v in df["total"]]
    df["precio_unitario"] = [fmt_money(v) for v in df["precio_unitario"]]
    # variantes de categorías (mayúsculas / espacios)
    def messy(v):
        if not isinstance(v, str) or v in ("N/A", "-", "?", "", "sin dato", "NULL"):
            return v
        x = rng.random()
        return v.upper() if x < 0.12 else v.lower() + " " if x < 0.2 else v
    df["sucursal"] = [messy(v) for v in df["sucursal"]]
    # outliers/negativos
    neg = rng.choice(n, 8, replace=False)
    df["cantidad"] = df["cantidad"].astype(object)
    df.loc[neg, "cantidad"] = -1
    # columnas sin nombre / basura
    df["Unnamed: 12"] = rng.choice(["x", "y", None], size=n)
    df[""] = rng.integers(0, 3, size=n).astype(object)
    df["  Notas "] = np.where(rng.random(n) < 0.8, None, "revisar")
    # duplicados
    dup_idx = rng.choice(n, 60, replace=False)
    df = pd.concat([df, df.iloc[dup_idx]], ignore_index=True)
    df = df.sample(frac=1, random_state=3).reset_index(drop=True)
    df.to_csv(OUT / "C_ruido_nulos_formatos_mixtos.csv", index=False, encoding="utf-8")
    TRUTH["C"] = {"total_suma_original": truth_total_sum, "nulos_inyectados_pct": truth_nulls, "duplicados_inyectados": 60, "columnas_sin_nombre": 2, "n_filas_con_duplicados": len(df), "max_nulos_pct": max(truth_nulls.values())}


def make_D(n=1500, seed=3):
    rng = np.random.default_rng(seed)
    regs = []
    base = pd.Timestamp("2025-02-01")
    for i in range(n):
        planta = rng.choice(["Cali", "Yumbo", "Palmira"], p=[0.5, 0.3, 0.2])
        maq = f"M-{int(rng.integers(1, 9)):02d}"
        prod = int(rng.normal(800, 120) * (0.8 if maq in ("M-03", "M-07") else 1.0))
        defect_rate = 0.02 + (0.05 if maq == "M-03" else 0) + rng.normal(0, 0.005)
        regs.append({"orden": {"id": f"OP-{i + 1:05d}", "planta": str(planta)}, "maquina": maq, "turno": str(rng.choice(["Mañana", "Tarde", "Noche"])),
                     "fecha": (base + pd.Timedelta(days=int(rng.integers(0, 240)))).strftime("%Y-%m-%d"), "unidades_producidas": prod,
                     "unidades_defectuosas": int(max(0, prod * defect_rate)), "tiempo_paro_min": float(round(abs(rng.normal(25, 18)), 1)),
                     "operario": {"nombre": f"Op {int(rng.integers(1, 20))}", "antiguedad_anios": int(rng.integers(0, 15))}})
    (OUT / "D_produccion_anidado.json").write_text(json.dumps({"meta": {"fuente": "MES planta", "version": 2}, "registros": regs}, ensure_ascii=False, indent=1), encoding="utf-8")
    TRUTH["D"] = {"n": n, "maquina_mas_defectos": "M-03"}


def make_E(seed=17):
    rng = np.random.default_rng(seed)
    munis = [("Cali", "Valle del Cauca", 2280000), ("Palmira", "Valle del Cauca", 360000), ("Tuluá", "Valle del Cauca", 220000), ("Buenaventura", "Valle del Cauca", 310000),
             ("Popayán", "Cauca", 320000), ("Santander de Quilichao", "Cauca", 100000), ("Pasto", "Nariño", 350000), ("Tumaco", "Nariño", 220000),
             ("Neiva", "Huila", 360000), ("Pitalito", "Huila", 140000), ("Quibdó", "Chocó", 130000), ("Ibagué", "Tolima", 540000)]
    rows = []
    for (m, d, pop) in munis:
        poor = 12 + (30 if m in ("Buenaventura", "Tumaco", "Quibdó") else 8 if d in ("Cauca",) else 0)
        for year in (2021, 2022, 2023, 2024):
            rows.append([m, d, year, int(pop * (1 + 0.01 * (year - 2021))), f"{(poor - 0.8 * (year - 2021) + rng.normal(0, 1)):.1f}%".replace(".", ","),
                         f"{(92 - 0.4 * poor + rng.normal(0, 2)):.1f}".replace(".", ","), f"{(9 + 0.3 * poor + rng.normal(0, 1)):.1f}".replace(".", ","), round(abs(rng.normal(14 + 0.4 * poor, 6)), 1)])
    hdr = ["Municipio", "Departamento", "Año", "Población", "Pobreza multidimensional (%)", "Cobertura educativa neta (%)", "Desempleo (%)", "Homicidios por 100 mil hab."]
    with pd.ExcelWriter(OUT / "E_indicadores_sociales.xlsx") as xw:
        title = pd.DataFrame([["Observatorio Social Regional - Indicadores municipales 2021-2024"] + [None] * 7])
        title.to_excel(xw, sheet_name="Indicadores", index=False, header=False, startrow=0)
        pd.DataFrame([hdr] + rows).to_excel(xw, sheet_name="Indicadores", index=False, header=False, startrow=1)
        pd.DataFrame({"Nota": ["Fuente: elaboración propia con datos simulados.", "Los porcentajes usan coma decimal."]}).to_excel(xw, sheet_name="Notas", index=False)
    TRUTH["E"] = {"n": len(rows), "municipio_mas_pobre": "Buenaventura|Tumaco|Quibdó"}


def make_F(n=900, seed=23):
    """Base 'sorpresa': hospitalaria, sin encabezado, latin-1, ';' y coma decimal."""
    rng = np.random.default_rng(seed)
    dx = ["Neumonía", "Fractura", "Apendicitis", "Dengue", "Hipertensión", "Diabetes", "Parto", "Gastroenteritis"]
    serv = ["Urgencias", "Medicina interna", "Cirugía", "Pediatría", "Ginecología"]
    lines = []
    for i in range(n):
        d = pd.Timestamp("2025-03-01") + pd.Timedelta(days=int(rng.integers(0, 200)))
        est = int(rng.choice([2, 5, 9, 14], p=[.3, .4, .2, .1])) if rng.random() > .1 else int(rng.integers(1, 3))
        costo = int(est * rng.normal(900000, 150000))
        edad = int(np.clip(rng.normal(48, 20), 0, 95))
        lines.append(";".join([str(100000 + i), d.strftime("%d/%m/%Y"), str(rng.choice(serv)), str(rng.choice(["Masculino", "Femenino"])), str(edad), str(rng.choice(dx)), str(est),
                               f"{costo:,}".replace(",", ".") + ",00", str(rng.choice(["Alta", "Alta", "Alta", "Remisión", "Fallecido"], p=[.8, .1, .05, .04, .01]))]))
    (OUT / "F_base_sorpresa_hospital.csv").write_bytes("\n".join(lines).encode("latin-1"))
    TRUTH["F"] = {"n": n}


def make_G():
    df = pd.DataFrame({"producto": ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C"], "unidades": [5, 7, 3, 6, 9, 2, 4, 8, 3, 5, 10, 1],
                       "region": ["N", "S"] * 6})
    df.to_csv(OUT / "G_muestra_diminuta.csv", index=False)
    TRUTH["G"] = {"n": 12}


def make_H(n=800, seed=1):
    """Recursos humanos: latin-1, ';', importes con '$', encabezados con tildes/signos, indicador Sí/No."""
    rng = np.random.default_rng(seed)
    cargos = ["Soporte", "Ventas", "Contabilidad", "Logística", "Dirección"]
    df = pd.DataFrame({"Empleado": [f"E{i:04d}" for i in range(n)], "Cargo": rng.choice(cargos, n, p=[.35, .3, .12, .18, .05]),
                       "Salario mensual": [f"$ {int(x):,}".replace(",", ".") for x in rng.normal(3_200_000, 900_000, n).clip(1_300_000)],
                       "Fecha de ingreso": pd.to_datetime("2018-01-01") + pd.to_timedelta(rng.integers(0, 2600, n), unit="D"),
                       "Ciudad": rng.choice(["Cali", "Bogotá", "Medellín"], n), "Evaluación (1-5)": rng.integers(1, 6, n), "Días de ausentismo": rng.poisson(3, n),
                       "¿Renunció?": rng.choice(["Sí", "No"], n, p=[.18, .82])})
    sop = df["Cargo"] == "Soporte"
    df.loc[sop, "¿Renunció?"] = rng.choice(["Sí", "No"], int(sop.sum()), p=[.35, .65])
    df["Fecha de ingreso"] = df["Fecha de ingreso"].dt.strftime("%d/%m/%Y")
    (OUT / "H_recursos_humanos.csv").write_bytes(df.to_csv(index=False, sep=";").encode("latin-1"))
    TRUTH["H"] = {"n": n, "tasa_renuncia_soporte_pct": float((df.loc[sop, "¿Renunció?"] == "Sí").mean() * 100), "tasa_renuncia_general_pct": float((df["¿Renunció?"] == "Sí").mean() * 100)}


def make_I(n=80, seed=4):
    """Archivo de UNA sola columna de texto con comas internas (el delimitador no debe inventarse)."""
    rng = np.random.default_rng(seed)
    keys = [k for k in FRAG if k != "sug"]
    rows, labels = [], []
    for _ in range(n):
        k = str(rng.choice(keys))
        rows.append(str(rng.choice(FRAG[k])).format(n=int(rng.integers(5, 40))))
        labels.append("neg" if k.startswith("neg") else "pos" if k == "pos" else "neu")
    pd.DataFrame({"comentario": rows}).to_csv(OUT / "I_encuesta_una_columna.csv", index=False, encoding="utf-8")
    TRUTH["I"] = {"n": n, "labels": labels}


def main():
    OUT.mkdir(exist_ok=True)
    make_A(); make_B(); make_C(); make_D(); make_E(); make_F(); make_G(); make_H(); make_I()
    TRUTH["B"].pop("labels", None) if False else None
    t = {k: {kk: vv for kk, vv in v.items() if kk != "labels"} for k, v in TRUTH.items()}
    (OUT / "verdad_de_terreno.json").write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    # etiquetas del dataset B para medir exactitud del sentimiento
    (OUT / "B_etiquetas_reales.json").write_text(json.dumps(TRUTH["B"]["labels"]), encoding="utf-8")
    (OUT / "I_etiquetas_reales.json").write_text(json.dumps(TRUTH["I"]["labels"]), encoding="utf-8")
    print("Datasets generados en", OUT)
    for p in sorted(OUT.iterdir()):
        print(" -", p.name, f"{p.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
