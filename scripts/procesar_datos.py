"""
Script de procesamiento — corre automáticamente en GitHub Actions.
No necesitas instalar nada en tu computadora.
"""

import json, sys
from pathlib import Path
from datetime import datetime

EXCLUIR      = ["PRODUCCION"]
CLASIF_ORDER = ["ALTA ROTACIÓN", "MEDIA ROTACIÓN", "LENTA ROTACIÓN", "SAGRADOS"]

ROOT = Path(__file__).parent.parent   # raíz del repositorio

def parse_date(v):
    if v is None: return None
    import pandas as pd
    try: return pd.to_datetime(v).strftime("%Y-%m-%d")
    except: return None

def sum_by(rows, key_fn):
    r = {}
    for row in rows:
        k = key_fn(row)
        r[k] = r.get(k, 0) + row.get("claves", 0)
    return r

def get_semaforo(row):
    est = str(row.get("estatus", "")).upper()
    bo  = float(row.get("bo", 0) or 0)
    mi  = float(row.get("meses_inv", 0) or 0)
    te  = float(row.get("t_entrega", 0) or 0)
    obj = float(row.get("obj_meses", 0) or 0)
    if est == "FALTANTE" and bo == 0:            return "ROJO"
    if est == "FALTANTE" and bo > 0:             return "AMARILLO"
    if est == "RIESGO" and bo == 0 and mi < te:  return "ROJO"
    if mi < te and bo > 0:                       return "NARANJA"
    if mi < obj and mi >= te:                    return "MORADO"
    if est == "SOBRE INVENTARIO" or mi > (obj + te): return "AZUL"
    return "VERDE"

def build_stats(skus, by_day, primera, ultima, fechas_ult):
    f1   = by_day.get(primera, 0)
    f2   = by_day.get(ultima, 0)
    pico = max((by_day.get(f, 0) for f in fechas_ult), default=0)
    return {
        "skus": skus, "f1": f1, "f2": f2, "pico": pico,
        "pct_f2":   round(f2   / skus * 100, 2) if skus > 0 else 0,
        "pct_pico": round(pico / skus * 100, 2) if skus > 0 else 0,
    }

def main():
    import pandas as pd

    # Buscar el Excel en la carpeta data/
    excels = list((ROOT / "data").glob("*.xlsx")) + list((ROOT / "data").glob("*.xls"))
    if not excels:
        print("❌ No se encontró ningún archivo Excel en la carpeta data/")
        sys.exit(1)
    excel_path = excels[0]
    print(f"📂 Procesando: {excel_path.name}")

    df1 = pd.read_excel(excel_path, sheet_name=0)
    try:
        df2 = pd.read_excel(excel_path, sheet_name="Detalle")
        print(f"  ✓ Hoja principal: {len(df1):,} filas")
        print(f"  ✓ Hoja Detalle:   {len(df2):,} filas")
    except Exception:
        df2 = None
        print(f"  ✓ Hoja principal: {len(df1):,} filas")
        print("  ⚠  Hoja Detalle no encontrada")

    # ── Procesar hoja principal ───────────────────────────────────────────────
    rows = []
    for _, r in df1.iterrows():
        comp   = str(r.get("COMPRADOR", "") or "").strip().upper()
        clasif = str(r.get("Clasificacion", "") or "").strip().upper()
        mov    = str(r.get("Clasificacion de mov", "") or "").strip().upper()
        fecha  = parse_date(r.get("Fecha"))
        claves = float(r.get("Claves", 0) or 0)
        if not fecha or not comp or comp in EXCLUIR: continue
        if not clasif or clasif == "(EN BLANCO)": continue
        rows.append({"fecha": fecha, "comprador": comp,
                     "clasificacion": clasif, "mov": mov, "claves": claves})

    fechas      = sorted(set(r["fecha"] for r in rows))
    compradores = sorted(set(r["comprador"] for r in rows))
    faltantes   = [r for r in rows if r["mov"] == "FALTANTE"]
    ultima      = fechas[-1];  primera = fechas[0]
    meses_u     = sorted(set(f[:7] for f in fechas))
    mes_actual  = meses_u[-1]
    mes_ant     = meses_u[-2] if len(meses_u) > 1 else None
    fechas_ult  = [f for f in fechas if f.startswith(mes_actual)]

    total_by_day = sum_by(faltantes, lambda r: r["fecha"])
    claves_total = sum_by(rows,      lambda r: r["fecha"])
    clas_by_day  = {cl: sum_by([r for r in faltantes if r["clasificacion"] == cl],
                                lambda r: r["fecha"]) for cl in CLASIF_ORDER}
    comp_by_day  = {c: sum_by([r for r in faltantes if r["comprador"] == c],
                               lambda r: r["fecha"]) for c in compradores}
    comp_cl_by_day = {c: {cl: sum_by(
        [r for r in faltantes if r["comprador"]==c and r["clasificacion"]==cl],
        lambda r: r["fecha"]) for cl in CLASIF_ORDER} for c in compradores}

    uni_rows = [r for r in rows if r["fecha"] == ultima]
    def uni_sum(comp=None, cl=None):
        f = uni_rows
        if comp: f = [r for r in f if r["comprador"] == comp]
        if cl and cl != "TOTAL": f = [r for r in f if r["clasificacion"] == cl]
        return sum(r["claves"] for r in f)

    CDATA = {}
    for c in compradores:
        CDATA[c] = {}
        for cl in CLASIF_ORDER + ["TOTAL"]:
            bd = comp_by_day[c] if cl == "TOTAL" else comp_cl_by_day[c][cl]
            CDATA[c][cl] = build_stats(uni_sum(comp=c, cl=cl), bd, primera, ultima, fechas_ult)

    AREA_DATA = {}
    for cl in CLASIF_ORDER + ["TOTAL"]:
        fl = [r for r in faltantes if cl == "TOTAL" or r["clasificacion"] == cl]
        bd = sum_by(fl, lambda r: r["fecha"])
        AREA_DATA[cl] = build_stats(uni_sum(cl=cl), bd, primera, ultima, fechas_ult)

    # ── Procesar hoja Detalle ─────────────────────────────────────────────────
    detalle_rows = []
    if df2 is not None:
        for _, r in df2.iterrows():
            comp  = str(r.get("COMPRADOR", "") or "").strip().upper()
            fecha = parse_date(r.get("Fecha"))
            if not comp or comp in EXCLUIR or not fecha: continue
            row = {
                "fecha": fecha, "clave": str(r.get("Clave","") or ""),
                "nombre": str(r.get("Nombre","") or ""),
                "marca": str(r.get("Marca","") or ""),
                "unidad": str(r.get("Unidad","") or ""),
                "clasificacion": str(r.get("Clasificación","") or "").strip(),
                "existencias": float(r.get("Existencias",0) or 0),
                "grupo": str(r.get("GRUPO","") or "").strip(),
                "comprador": comp,
                "clmov": str(r.get("Clasificación por movimiento","") or "").strip().upper(),
                "t_entrega": float(r.get("Tiempo de entrega",0) or 0),
                "obj_meses": float(r.get("Objetivo_Meses de inventario",0) or 0),
                "meses_inv": float(r.get("Meses de inventario",0) or 0),
                "estatus": str(r.get("Clasificacion_estatus de inventario","") or "").strip().upper(),
                "reorden": str(r.get("Clasificacion_Punto de reorden","") or "").strip(),
                "bo": float(r.get("Back Order",0) or 0),
            }
            row["semaforo"] = get_semaforo(row)
            detalle_rows.append(row)

    def uniq(field): return sorted(set(r[field] for r in detalle_rows if r.get(field)))

    ult_det = max((r["fecha"] for r in detalle_rows), default=None)
    falt_detalle = {}
    for r in detalle_rows:
        if r["fecha"] == ult_det and r["estatus"] == "FALTANTE":
            c, cl = r["comprador"], r["clmov"]
            falt_detalle.setdefault(c, {}).setdefault(cl, []).append(r)

    # ── Ensamblar snapshot ────────────────────────────────────────────────────
    meses = ["","Ene","Feb","Mar","Abr","May","Jun",
             "Jul","Ago","Sep","Oct","Nov","Dic"]
    uf = ultima.split("-")
    snap = {
        "fechas": fechas, "compradores": compradores,
        "totalByDay": total_by_day, "clavesTotal": claves_total,
        "clasByDay": clas_by_day, "compByDay": comp_by_day,
        "compClByDay": comp_cl_by_day, "CDATA": CDATA, "AREA_DATA": AREA_DATA,
        "ultimaFecha": ultima, "primeraFecha": primera,
        "mesActual": mes_actual, "mesAnterior": mes_ant,
        "fechasUltimoMes": fechas_ult,
        "totalHoy": total_by_day.get(ultima, 0),
        "totalInicio": total_by_day.get(primera, 0),
        "picoTotal": max((total_by_day.get(f,0) for f in fechas_ult), default=0),
        "clavesHoy": claves_total.get(ultima, 0),
        "filename": excel_path.name,
        "ultimaActualizacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "detalleRows": detalle_rows,
        "detFechas": uniq("fecha"), "detMarcas": uniq("marca"),
        "detClMovs": uniq("clmov"), "detGrupos": uniq("grupo"),
        "detComps": uniq("comprador"), "detEstatus": uniq("estatus"),
        "detReorden": uniq("reorden"), "faltDetalle": falt_detalle,
    }

    # ── Guardar data.json ─────────────────────────────────────────────────────
    # Limpiar NaN y optimizar tamaño antes de serializar
    import math
    def clean_nan(obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj): return 0
            return round(obj, 2)  # máximo 2 decimales
        if isinstance(obj, dict): return {k: clean_nan(v) for k, v in obj.items() if v is not None and v != ""}
        if isinstance(obj, list): return [clean_nan(i) for i in obj]
        return obj

    snap = clean_nan(snap)

    out_path = ROOT / "data.json"
    json_str = json.dumps(snap, ensure_ascii=False, separators=(",", ":"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json_str)

    size_kb = len(json_str.encode()) / 1024
    print(f"   📦 data.json: {size_kb:,.0f} KB")

    size_kb = out_path.stat().st_size / 1024
    print(f"\n✅ data.json generado: {size_kb:,.0f} KB")
    print(f"   Fechas: {len(fechas)} · Compradores: {len(compradores)}"
          f" · Detalle: {len(detalle_rows):,} claves")
    print(f"   Período: {primera} → {ultima}")

if __name__ == "__main__":
    main()
