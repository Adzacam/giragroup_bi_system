import urllib.request
import json
from core.security import create_access_token

token = create_access_token({'sub': '1', 'role': 'ADMIN', 'email': 'admin@giragroup.bo'})
boundary = '----WebKitFormBoundarySample'
content = 'id,nombre,nota\n1,Juan Perez,85\n2,Maria Lopez,90\n'

parts = [
    f'--{boundary}'.encode('ascii'),
    b'Content-Disposition: form-data; name="files"; filename="test_estudiantes.csv"',
    b'Content-Type: text/csv',
    b'',
    content.encode('utf-8'),
    f'--{boundary}'.encode('ascii'),
    b'Content-Disposition: form-data; name="source_types"',
    b'',
    json.dumps(['Inscripciones (Google Forms)']).encode('utf-8'),
    f'--{boundary}--'.encode('ascii'),
    b''
]

body = b'\r\n'.join(parts)

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/dataops/upload-batch',
    data=body,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': f'multipart/form-data; boundary={boundary}'
    }
)

try:
    with urllib.request.urlopen(req) as resp:
        print('Upload Status:', resp.status)
        print('Upload Response:', resp.read().decode('utf-8'))
except Exception as e:
    print('Upload Error:', e)
