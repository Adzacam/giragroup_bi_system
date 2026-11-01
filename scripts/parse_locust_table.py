import pandas as pd

df = pd.read_csv('docs/evidencias/locust_summary_stats.csv')
print('| Método | Endpoint | Peticiones | Fallos | p50 (Mediana) | p95 | p99 | RPS |')
print('| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |')
for _, row in df.iterrows():
    name = row['Name']
    m = row['Type'] if pd.notna(row['Type']) else '-'
    reqs = int(row['Request Count'])
    fails = int(row['Failure Count'])
    p50 = f"{row['50%']:.0f} ms"
    p95 = f"{row['95%']:.0f} ms"
    p99 = f"{row['99%']:.0f} ms"
    rps = f"{row['Requests/s']:.2f}"
    print(f'| {m} | `{name}` | {reqs} | {fails} | {p50} | {p95} | {p99} | {rps} |')
