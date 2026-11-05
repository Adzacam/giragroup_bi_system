import client from './client';

// Informe de Power BI Desktop del CMI (.pbix versionado en el servidor)
const BASE = '/api/v1/powerbi/informe';

const guardarBlob = (response, porDefecto) => {
  const disp = response.headers?.['content-disposition'] || '';
  const m = disp.match(/filename="?([^";]+)"?/);
  const nombre = m ? m[1] : porDefecto;
  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/octet-stream' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
  return nombre;
};

const powerbiApi = {
  getInforme: () => client.get(BASE).then((r) => r.data),
  getVersiones: () => client.get(`${BASE}/versiones`).then((r) => r.data),
  descargar: (version) =>
    client
      .get(`${BASE}/descargar`, { params: version ? { version } : {}, responseType: 'blob' })
      .then((r) => guardarBlob(r, 'giragroup_cmi.pbix')),
  subir: (archivo, nota) => {
    const fd = new FormData();
    fd.append('archivo', archivo);
    if (nota) fd.append('nota', nota);
    return client.post(BASE, fd).then((r) => r.data);
  },
  restaurar: (version) => client.put(`${BASE}/versiones/${version}/vigente`).then((r) => r.data),
};

export default powerbiApi;
