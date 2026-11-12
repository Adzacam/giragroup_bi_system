"""Protección de campos personales en las vistas de DataOps, siempre antes de responder."""
import csv
import re
import unicodedata
from services.dataops_evaluation_service import enmascarar_ci, cis_en_entidades

def _normalizar(valor):
    return ''.join(c for c in unicodedata.normalize('NFD', str(valor).lower()) if unicodedata.category(c) != 'Mn')


def _sensible(clave):
    clave = re.sub(r'[_/\s-]+', ' ', _normalizar(clave).replace('.', '')).strip()
    if re.fullmatch(r'(?:ci|ci numero|ci real|ci enmascarado|ci estudiante|ci docente|doc identidad ci|cedula(?: de identidad)?|documento(?: de identidad)?|nro documento|idnumber)', clave):
        return 'documento'
    if re.fullmatch(r'(?:celular|telefono(?: de contacto| contacto)?|movil|nit)', clave):
        return 'numero'
    if re.fullmatch(r'(?:e ?mail|correo(?: electronico| institucional)?|direccion de correo(?: electronico)?)', clave):
        return 'correo'
    if re.fullmatch(r'(?:direccion(?: de domicilio)?|domicilio|fecha(?: de)? nacimiento|fecha nacimiento|nacimiento|fecha nac)', clave):
        return 'privado'
    if re.fullmatch(r'(?:nombre(?:s)?(?: completo(?:s)?| y apellidos?)?|apellidos?(?: paterno| materno)?|paterno|materno|asesor|razon social|estudiante|docente|participante|alumno|estudiante cliente)', clave):
        return 'privado'
    return None


EMAIL = re.compile(r'[^\s@,|;]+@[^\s@,|;]+\.[A-Za-z]{2,}')
DOCUMENTO = re.compile(r'\b(CI|C[ÉE]DULA(?: DE IDENTIDAD)?|NIT|CELULAR|TEL[ÉE]FONO)\s*[:=#-]?\s*(\+?\d[\d .()-]{4,}\d(?:\s+[A-Z]{2})?)', re.I)


def _numero_publico(valor):
    return enmascarar_ci(re.sub(r'\D', '', str(valor))) if re.search(r'\d', str(valor)) else '••••'


def texto_publico(valor):
    """Censura campos rotulados y documentos explícitos, sin confundir montos o fechas académicas."""
    texto = str(valor)
    partes = re.split(r'(\||;|,(?=\s*[^,:|;]{1,45}:))', texto)
    for i, parte in enumerate(partes):
        rotulo, separador, contenido = parte.partition(':')
        tipo = _sensible(rotulo) if separador else None
        if tipo and contenido.strip():
            numero = contenido.strip()
            protegido = _numero_publico(numero) if tipo in ('documento', 'numero') else '••••'
            partes[i] = f'{rotulo}: {protegido}'
    texto = ''.join(partes)
    texto = DOCUMENTO.sub(lambda m: f'{m[1]} {_numero_publico(m[2])}', texto)
    return EMAIL.sub('••••@••••', texto)


def _publicar(valor, clave=''):
    if valor is None:
        return None
    if _sensible(clave) and str(valor).strip():
        return _numero_publico(valor) if _sensible(clave) in ('documento', 'numero') else '••••'
    if isinstance(valor, dict):
        return {k: _publicar(v, k) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_publicar(v) for v in valor]
    return texto_publico(valor) if isinstance(valor, str) else valor


def _columnas(linea):
    return [v.strip() for v in linea.split('|')] if '|' in linea else next(csv.reader([linea]))


def _fila_publica(linea, tipo_fuente):
    columnas = _columnas(linea)
    # Archivos sin rótulos: el formato anterior identifica nombre y CI en las dos primeras columnas.
    if tipo_fuente in ('ACTA', 'MOODLE', 'ADMISION') and len(columnas) >= 3 and ':' not in linea and re.fullmatch(r'[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+(?:\s+[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+)+', columnas[0]) and re.fullmatch(r'[\d .-]{5,}(?:\s+[A-Z]{2})?', columnas[1].strip(), re.I):
        columnas[0] = '••••'
        columnas[1] = _numero_publico(columnas[1])
        columnas = [texto_publico(c) for c in columnas]
        return columnas, ' | '.join(columnas)
    return [texto_publico(c) for c in columnas], texto_publico(linea)


def _valores_privados(linea, tipo_fuente):
    valores = {}
    for parte in re.split(r'\||;|,(?=\s*[^,:|;]{1,45}:)', linea):
        rotulo, separador, valor = parte.partition(':')
        tipo = _sensible(rotulo) if separador else None
        if tipo and valor.strip():
            valores[valor.strip()] = _numero_publico(valor) if tipo in ('documento', 'numero') else '••••'
    for m in DOCUMENTO.finditer(linea):
        valores[m[2].strip()] = _numero_publico(m[2])
    originales = _columnas(linea)
    publicas, _ = _fila_publica(linea, tipo_fuente)
    if originales and publicas[0] == '••••' and len(originales) >= 3:
        valores[originales[0]] = '••••'
        valores[originales[1]] = publicas[1]
    for valor, protegido in list(valores.items()):
        numero = re.sub(r'\D', '', valor)
        if len(numero) >= 5:
            valores[numero] = _numero_publico(numero)
    return valores


def _proteger_metadatos(valor, privados):
    if isinstance(valor, dict):
        return {k: _proteger_metadatos(v, privados) for k, v in valor.items()}
    if isinstance(valor, str):
        valor = _reemplazar_privados(valor, privados)
    publico = _publicar(valor)
    return publico[:512] if isinstance(publico, str) else publico


def _reemplazar_privados(texto, privados):
    for original in sorted(privados, key=len, reverse=True):
        texto = texto.replace(original, privados[original])
    return texto


def registro_beto_publico(registro):
    """Protege también lecturas antiguas en caché; no modifica la evaluación guardada."""
    lectura = registro.get('lectura') or {}
    texto = registro.get('raw_text') or lectura.get('texto') or ''
    privados = _valores_privados(texto, registro.get('tipo_fuente'))
    entidades = lectura.get('entidades') or []
    sin_dato = ('no provisto', 'no especificado', 'no detectado', 'sin dato', 'none', 'null', '—', '')
    for ci in cis_en_entidades(entidades, registro.get('ci_real')):
        if '•' not in str(ci):
            privados[str(ci)] = _numero_publico(ci)
    for key in ('ci', 'ci_enmascarado'):
        ci = registro.get(key)
        if ci and str(ci).strip().lower() not in sin_dato and '•' not in str(ci):
            privados[str(ci)] = _numero_publico(ci)
    privados_origen = dict(privados)
    nombre = registro.get('estudiante')
    if nombre and nombre not in ('No detectado', 'Sin dato', '••••'):
        privados[str(nombre)] = '••••'
    for entidad in entidades:
        label = _normalizar(entidad.get('label', ''))
        personal = label in ('estudiante', 'docente', 'persona', 'nombre', 'per', 'asesor')
        documento = label in ('documento / ci', 'ci', 'nit', 'celular', 'telefono')
        if personal or documento:
            for key in ('token', 'matchedCanonical', 'ci', 'ci_real', 'ci_numero', 'valor', 'text'):
                valor = entidad.get(key)
                if valor and '•' not in str(valor):
                    privados[str(valor)] = _numero_publico(valor) if documento or key.startswith('ci') else '••••'

    def proteger(valor, clave=''):
        if clave == 'ci_real':
            return None
        if _sensible(clave) and str(valor).strip().lower() in sin_dato:
            return None
        if isinstance(valor, dict):
            return {k: proteger(v, k) for k, v in valor.items() if k != 'ci_real'}
        if isinstance(valor, list):
            return [proteger(v) for v in valor[:50]]
        if isinstance(valor, str):
            # El encabezado del archivo manda para el texto original. Un error del modelo
            # al etiquetar un programa como persona no debe ocultar ese programa en origen.
            valor = _reemplazar_privados(valor, privados_origen if clave in ('raw_text', 'texto') else privados)
            if _sensible(clave) and valor.strip() and '•' not in valor:
                valor = _publicar(valor, clave)
            return texto_publico(valor)[:4000]
        return valor

    campos = ('id', 'stg_id', 'id_documento', 'nombre_archivo', 'tipo_fuente', 'line_number',
              'estado', 'categoria_particion', 'estado_resolucion', 'indice_registro',
              'estudiante', 'ci', 'ci_enmascarado', 'modulo', 'nota_original', 'nota_normalizada',
              'monto', 'area', 'en_calidad', 'es_nuevo_catalogo', 'alerta_abandono', 'decision',
              'raw_text', 'verificacion_reglas')
    publico = proteger({k: registro.get(k) for k in campos})
    publicas = []
    for entidad in entidades[:50]:
        campos_entidad = ('label', 'token', 'matchedCanonical', 'betoConfidence', 'lecturaModelo', 'fuzzScore')
        e = proteger({k: entidad.get(k) for k in campos_entidad})
        if _normalizar(entidad.get('label', '')) in ('estudiante', 'docente', 'persona', 'nombre', 'per', 'asesor'):
            e['token'], e['matchedCanonical'] = '••••', '••••'
        publicas.append(e)
    # Los tokens sueltos de una persona no deben permitir reconstruir su nombre.
    publico['lectura'] = {'texto': proteger(lectura.get('texto', texto), 'texto'), 'entidades': publicas}
    return publico


