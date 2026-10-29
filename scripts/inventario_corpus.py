import sys, pathlib, warnings, datetime as dt, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

def anios(df):
    # 1. Intentar columnas datetime o string con formato fecha
    for c in df:
        s = df[c]
        d = s if pd.api.types.is_datetime64_any_dtype(s) else pd.to_datetime(
            s.where(s.map(lambda v: isinstance(v, (dt.date, str)))),
            errors='coerce',
            dayfirst=True
        )
        valid_years = d.dt.year.dropna()
        valid_years = valid_years[(valid_years >= 2022) & (valid_years <= 2027)]
        if len(valid_years) > max(len(df) * 0.4, 3):
            return valid_years.value_counts().sort_index().to_dict()
    # 2. Intentar columnas numéricas de Año / Gestión (ej. AÑO INCIO en ARCA o GESTIÓN en Egresos)
    for c in df:
        s = pd.to_numeric(df[c], errors='coerce').dropna()
        valid_years = s[(s >= 2022) & (s <= 2027) & (s % 1 == 0)]
        if len(valid_years) > max(len(df) * 0.4, 3):
            return valid_years.astype(int).value_counts().sort_index().to_dict()
    return {}

def leer(f):
    if f.suffix.lower() == '.xlsx':
        return pd.read_excel(f, sheet_name=None, header=None)
    for e in ('utf-8-sig', 'latin-1'):
        try:
            return {'-': pd.read_csv(f, header=None, sep=None, engine='python', encoding=e, on_bad_lines='skip')}
        except UnicodeDecodeError:
            pass
    return {}

R = pathlib.Path(sys.argv[1])
print('|Archivo|Hoja|Filas|Cols|KB|Filas por gestión|\n|-|-|-|-|-|-|')
total_filas = 0
totales_anios = {}
for f in sorted(p for p in R.rglob('*') if p.suffix.lower() in ('.xlsx', '.csv')):
    for h, df in leer(f).items():
        df = df.dropna(how='all').dropna(axis=1, how='all')
        if df.empty:
            continue
        n = max(int((df.notna().sum(1) >= 2).sum()) - 1, 0)
        total_filas += n
        dist_anios = anios(df.iloc[1:])
        for k, v in dist_anios.items():
            totales_anios[int(k)] = totales_anios.get(int(k), 0) + int(v)
        a = ', '.join(f'{int(k)}: {int(v)}' for k, v in dist_anios.items()) or 's/f'
        fname_anon = (
            f.name.replace(' y Unifranz', ' Posgrado')
                  .replace(' - EXP. UNIFRANZ POSTGRADO', ' - Posgrado Histórico')
        )
        h_anon = h.replace('UNIFRANZ', 'POSGRADO')
        print(f'|{fname_anon}|{h_anon}|{n:,}|{df.shape[1]}|{f.stat().st_size/1024:,.1f}|{a}|')

res_anios = ', '.join(f'{k}: {v:,}' for k, v in sorted(totales_anios.items()))
print(f'\nTOTAL FILAS PROCESABLES: {total_filas:,} | DESGLOSE POR GESTIÓN: {res_anios}')
