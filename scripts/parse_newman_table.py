import json

with open('docs/evidencias/newman_report.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

executions = data['run']['executions']
print(f'| Endpoint / Caso | Método | Esperado | Obtenido | Tiempo (ms) | Resultado |')
print(f'| :--- | :---: | :---: | :---: | :---: | :---: |')
for ex in executions:
    name = ex['item']['name']
    method = ex['request']['method']
    url_obj = ex['request']['url']
    path = '/' + '/'.join(url_obj.get('path', []))
    if url_obj.get('query'):
        q_str = '&'.join([f"{q.get('key')}={q.get('value')}" for q in url_obj.get('query')])
        path += f'?{q_str}'
    code = ex['response']['code']
    time_ms = ex['response']['responseTime']
    all_passed = True
    expected_code = 200
    for a in ex.get('assertions', []):
        if a.get('error'):
            all_passed = False
    if '401' in name:
        expected_code = 401
    elif '422' in name:
        expected_code = 422
    elif '403' in name:
        expected_code = 403
    elif '400' in name:
        expected_code = 400
    res_str = 'PASÓ' if all_passed and code == expected_code else 'FALLÓ'
    print(f'| {name} (`{path}`) | {method} | {expected_code} | {code} | {time_ms} ms | {res_str} |')
