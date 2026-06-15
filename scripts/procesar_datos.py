"""
Script de procesamiento — corre automáticamente en GitHub Actions.
Versión optimizada con pandas (< 5 segundos de procesamiento).
"""
import json, sys, math
from pathlib import Path
from datetime import datetime

EXCLUIR = ['PRODUCCION']
CLASIF  = ['ALTA ROTACIÓN', 'MEDIA ROTACIÓN', 'LENTA ROTACIÓN', 'SAGRADOS']
ROOT    = Path(__file__).parent.parent
SEMANAS = 7   # fechas más recientes a incluir


def get_semaforo(e, bo, mi, te, ob):
    if e == 'FALTANTE' and bo == 0:           return 'ROJO'
    if e == 'FALTANTE' and bo > 0:            return 'AMARILLO'
    if e == 'RIESGO' and bo == 0 and mi < te: return 'ROJO'
    if mi < te and bo > 0:                    return 'NARANJA'
    if mi < ob and mi >= te:                  return 'MORADO'
    if e == 'SOBRE INVENTARIO' or mi > (ob + te): return 'AZUL'
    return 'VERDE'


def clean_nan(o):
    if isinstance(o, float):
        return 0 if (math.isnan(o) or math.isinf(o)) else round(o, 4)
    if isinstance(o, dict):  return {k: clean_nan(v) for k, v in o.items()}
    if isinstance(o, list):  return [clean_nan(i) for i in o]
    return o


def main():
    try:
        import pandas as pd
    except ImportError:
        print("❌ pandas no instalado"); sys.exit(1)

    excels = list((ROOT / 'data').glob('*.xlsx')) + list((ROOT / 'data').glob('*.xls'))
    if not excels:
        print("❌ No se encontró ningún Excel en data/"); sys.exit(1)

    excel_path = excels[0]
    engine = 'openpyxl' if excel_path.suffix.lower() in ('.xlsx','.xlsm') else 'xlrd'
    print(f"📂 Procesando: {excel_path.name}")

    df1 = pd.read_excel(excel_path, sheet_name=0, engine=engine)
    try:
        df2 = pd.read_excel(excel_path, sheet_name='Detalle', engine=engine)
        print(f"  ✓ Hoja principal: {len(df1):,} filas")
        print(f"  ✓ Hoja Detalle:   {len(df2):,} filas")
    except Exception:
        df2 = None
        print(f"  ✓ Hoja principal: {len(df1):,} filas  ⚠ Sin hoja Detalle")

    # ── Preparar hoja principal ───────────────────────────────────────────────
    df1['fecha']         = pd.to_datetime(df1['Fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
    df1['comprador']     = df1['COMPRADOR'].fillna('').str.strip().str.upper()
    df1['clasificacion'] = df1['Clasificacion'].fillna('').str.strip().str.upper()
    df1['mov']           = df1['Clasificacion de mov'].fillna('').str.strip().str.upper()
    df1['claves']        = pd.to_numeric(df1['Claves'], errors='coerce').fillna(0)
    df1 = df1[df1['fecha'].notna() & (df1['fecha'] != 'NaT')]
    df1 = df1[~df1['comprador'].isin(EXCLUIR)]
    df1 = df1[df1['clasificacion'].notna() & (df1['clasificacion'] != '') & (df1['clasificacion'] != '(EN BLANCO)')]

    all_fechas  = sorted(df1['fecha'].unique())
    fechas      = sorted(df1['fecha'].unique().tolist())
    compradores = sorted(df1['comprador'].unique().tolist())
    print(f"  📅 Fechas: {fechas[0]} → {fechas[-1]} ({len(fechas)} días)")

    if not fechas:
        print("❌ Sin datos después de filtrar"); sys.exit(1)

    uf  = fechas[-1]; pf = fechas[0]
    meses = sorted(set(f[:7] for f in fechas))
    mA  = meses[-1]
    mAn = meses[-2] if len(meses) > 1 else None
    fU  = [f for f in fechas if f.startswith(mA)]
    fAnt = [f for f in fechas if mAn and f.startswith(mAn)]
    lastAnt = fAnt[-1] if fAnt else pf

    falt = df1[df1['mov'] == 'FALTANTE']

    totalByDay  = falt.groupby('fecha')['claves'].sum().to_dict()
    clavesTotal = df1.groupby('fecha')['claves'].sum().to_dict()

    clasByDay = {cl: falt[falt['clasificacion']==cl].groupby('fecha')['claves'].sum().to_dict()
                 for cl in CLASIF}

    cbd = falt.groupby(['comprador','fecha'])['claves'].sum().reset_index()
    compByDay = {c: {} for c in compradores}
    for _, r in cbd.iterrows():
        compByDay[r['comprador']][r['fecha']] = r['claves']

    ccbd = falt.groupby(['comprador','clasificacion','fecha'])['claves'].sum().reset_index()
    compClByDay = {c: {cl: {} for cl in CLASIF} for c in compradores}
    for _, r in ccbd.iterrows():
        c,cl,f,v = r['comprador'],r['clasificacion'],r['fecha'],r['claves']
        if c in compClByDay and cl in compClByDay[c]:
            compClByDay[c][cl][f] = v

    uni_uf  = df1[df1['fecha']==uf ].groupby(['comprador','clasificacion'])['claves'].sum()
    uni_ant = df1[df1['fecha']==lastAnt].groupby(['comprador','clasificacion'])['claves'].sum() if lastAnt else None

    def get_uni(comp=None, cl=None, ant=False):
        src = uni_ant if ant else uni_uf
        if src is None: return 0
        try:
            if comp and cl and cl!='TOTAL': return float(src.get((comp,cl), 0))
            if comp:
                m = src.index.get_level_values(0)==comp; return float(src[m].sum())
            if cl and cl!='TOTAL':
                m = src.index.get_level_values(1)==cl;   return float(src[m].sum())
            return float(src.sum())
        except: return 0

    def st(sk, skA, bd):
        f1 = bd.get(lastAnt, 0); f2 = bd.get(uf, 0)
        pk = max((bd.get(f,0) for f in fU), default=0)
        return {"skus":sk,"f1":f1,"f2":f2,"pico":pk,
                "pct_f1":  round(f1/skA*100,2) if skA>0 else 0,
                "pct_f2":  round(f2/sk *100,2) if sk >0 else 0,
                "pct_pico":round(pk/sk *100,2) if sk >0 else 0}

    CDATA = {}
    for c in compradores:
        CDATA[c] = {}
        for cl in CLASIF+['TOTAL']:
            bd = compByDay[c] if cl=='TOTAL' else compClByDay[c][cl]
            CDATA[c][cl] = st(get_uni(c,cl), get_uni(c,cl,ant=True), bd)

    AREA_DATA = {}
    for cl in CLASIF+['TOTAL']:
        fl = falt if cl=='TOTAL' else falt[falt['clasificacion']==cl]
        bd = fl.groupby('fecha')['claves'].sum().to_dict()
        AREA_DATA[cl] = st(get_uni(cl=cl), get_uni(cl=cl,ant=True), bd)

    # ── Hoja Detalle ──────────────────────────────────────────────────────────
    detRows = []; faltDetalle = {}

    if df2 is not None:
        df2['fecha'] = pd.to_datetime(df2['Fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
        df2 = df2[~df2['COMPRADOR'].fillna('').str.strip().str.upper().isin(EXCLUIR)]
        # Guardar últimas 7 fechas disponibles en Detalle
        fechas_det = sorted(df2['fecha'].dropna().unique())
        ultimas_7_det = set(fechas_det[-7:])
        last_det = fechas_det[-1] if fechas_det else None
        df2 = df2[df2['fecha'].isin(ultimas_7_det)]
        print(f"  📅 Detalle: {len(ultimas_7_det)} fechas ({min(ultimas_7_det) if ultimas_7_det else ''} → {last_det})")

        for _, r in df2.iterrows():
            comp = str(r.get('COMPRADOR','') or '').strip().upper()
            if not comp or comp in EXCLUIR: continue
            e  = str(r.get('Clasificacion_estatus de inventario','') or '').strip().upper()
            bo = float(r.get('Back Order',0) or 0)
            mi = float(r.get('Meses de inventario',0) or 0)
            te = float(r.get('Tiempo de entrega',0) or 0)
            ob = float(r.get('Objetivo_Meses de inventario',0) or 0)
            row = {
                "fecha":        str(r.get('fecha','')),
                "clave":        str(r.get('Clave','') or ''),
                "nombre":       str(r.get('Nombre','') or '')[:60],
                "marca":        str(r.get('Marca','') or ''),
                "unidad":       str(r.get('Unidad','') or ''),
                "clasificacion":str(r.get('Clasificación','') or '').strip(),
                "existencias":  round(float(r.get('Existencias',0) or 0),2),
                "grupo":        str(r.get('GRUPO','') or '').strip(),
                "comprador":    comp,
                "clmov":        str(r.get('Clasificación por movimiento','') or '').strip().upper(),
                "t_entrega":    round(te,2), "obj_meses": round(ob,2), "meses_inv": round(mi,2),
                "estatus":      e,
                "reorden":      str(r.get('Clasificacion_Punto de reorden','') or '').strip(),
                "bo":           round(bo,2),
                "semaforo":     get_semaforo(e,bo,mi,te,ob),
            }
            detRows.append(row)
            # faltDetalle solo con el último día (para expandibles en Tabla Resumen)
            if e == 'FALTANTE' and row.get('fecha') == last_det:
                faltDetalle.setdefault(comp,{}).setdefault(row['clmov'],[]).append(row)

    def uq(f): return sorted(set(r[f] for r in detRows if r.get(f)))

    snap = {
        "fechas":fechas, "compradores":compradores,
        "totalByDay":totalByDay, "clavesTotal":clavesTotal,
        "clasByDay":clasByDay, "compByDay":compByDay, "compClByDay":compClByDay,
        "CDATA":CDATA, "AREA_DATA":AREA_DATA,
        "ultimaFecha":uf, "primeraFecha":pf,
        "mesActual":mA, "mesAnterior":mAn, "fechasUltimoMes":fU,
        "totalHoy":float(totalByDay.get(uf,0)),
        "clavesHoy":float(clavesTotal.get(uf,0)),
        "filename":excel_path.name,
        "ultimaActualizacion":datetime.now().strftime('%d/%m/%Y %H:%M'),
        "detalleRows":detRows,
        "detFechas":uq('fecha'), "detMarcas":uq('marca'), "detClMovs":uq('clmov'),
        "detGrupos":uq('grupo'), "detComps":uq('comprador'),
        "detEstatus":uq('estatus'), "detReorden":uq('reorden'),
        "faltDetalle":faltDetalle,
    }

    snap = clean_nan(snap)
    js   = json.dumps(snap, ensure_ascii=False, separators=(',',':'))
    out  = ROOT / 'data.json'
    out.write_text(js, encoding='utf-8')

    kb = len(js.encode())/1024
    print(f"\n✅ data.json: {kb:,.0f} KB ({kb/1024:.1f} MB)")
    print(f"   Fechas: {len(fechas)} · Compradores: {len(compradores)} · Detalle: {len(detRows):,} claves")


if __name__ == '__main__':
    main()
