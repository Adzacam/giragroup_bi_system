import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud, FileSpreadsheet, CheckCircle2, AlertTriangle, Play,
  HelpCircle, Eye, ArrowRight, Layers, RefreshCw, Trash2, FileText, Check, AlertCircle
} from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import { dataopsApi } from '../../api/dataopsApi';
import { sileoToast } from '../../services/sileoToast';

export default function IngestView() {
  const navigate = useNavigate();

  // Estados del formulario del lote
  const [file, setFile] = useState(null);
  const [institucion, setInstitucion] = useState('');
  const [tipoFuente, setTipoFuente] = useState('');
  const [escalaNotas, setEscalaNotas] = useState(''); // Sin valor por defecto obligatorio
  const [periodo, setPeriodo] = useState('2026-1');

  // Estados de proceso y UI
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [sourcesHistory, setSourcesHistory] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  // Muestra de vista previa simulada (o generada) para 5 filas
  const [previewRows, setPreviewRows] = useState([
    { id: 1, col1: 'Pérez Mamani Juan Carlos', col2: '4892019 LP', col3: 'Gestión de Riesgos', col4: '85.5', col5: 'Docente Titular' },
    { id: 2, col1: 'Quispe Laura Maria Elena', col2: '6712340 SC', col3: 'Gestión de Riesgos', col4: '92.0', col5: 'Docente Titular' },
    { id: 3, col1: 'Flores Condori Roberto', col2: '5598124 CB', col3: 'Gestión de Riesgos', col4: '74.0', col5: 'Docente Titular' },
    { id: 4, col1: 'Mamani Choque Andrea', col2: '7821901 LP', col3: 'Gestión de Riesgos', col4: '68.5', col5: 'Docente Titular' },
    { id: 5, col1: 'Vargas Rios David', col2: '8910243 OR', col3: 'Gestión de Riesgos', col4: '90.0', col5: 'Docente Titular' },
  ]);

  const previewColumns = [
    { key: 'col1', label: 'Estudiante / Nombre', recognized: true },
    { key: 'col2', label: 'Documento / CI', recognized: true },
    { key: 'col3', label: 'Módulo / Materia', recognized: true },
    { key: 'col4', label: 'Calificación', recognized: true },
    { key: 'col5', label: 'Observaciones Doc.', recognized: false, warning: 'Columna no canónica' },
  ];

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setIsLoadingHistory(true);
      const res = await dataopsApi.getSources();
      if (res && res.data) {
        setSourcesHistory(res.data);
      }
    } catch (err) {
      console.warn('Error al cargar historial:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      validateAndSetFile(selected);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (f) => {
    const ext = f.name.split('.').pop().toLowerCase();
    if (['xlsx', 'xls', 'csv'].includes(ext)) {
      setFile(f);
      sileoToast.success({
        title: 'Archivo cargado',
        description: `${f.name} (${(f.size / 1024).toFixed(1)} KB)`
      });
      // Inferencia amigable si el nombre contiene sugerencias
      if (f.name.toLowerCase().includes('unifranz')) setInstitucion('Unifranz');
      if (f.name.toLowerCase().includes('acta')) setTipoFuente('Acta de calificaciones');
    } else {
      sileoToast.error({
        title: 'Formato no soportado',
        description: 'Por favor sube un archivo Excel (.xlsx, .xls) o CSV (.csv)'
      });
    }
  };

  const isFormValid = Boolean(file && institucion && tipoFuente && escalaNotas);

  const handleProcessBatch = async () => {
    if (!isFormValid) return;

    try {
      setIsProcessing(true);
      sileoToast.info({
        title: 'Iniciando ingestión',
        description: 'Procesando archivo y generando copias de trabajo...'
      });

      // Subir archivo a la API
      const uploadRes = await dataopsApi.uploadFile(file, tipoFuente);
      const newDocId = uploadRes?.doc_id || uploadRes?.data?.id || 1;

      // Guardar contexto en localStorage para el stepper
      localStorage.setItem('last_active_batch_id', newDocId);

      sileoToast.success({
        title: 'Lote ingestor procesado',
        description: 'Pasando al Paso ②: Texto plano estructurado'
      });

      // Navegar automáticamente al Paso 2: Texto plano
      navigate(`/dataops/lote/${newDocId}/texto`);
    } catch (err) {
      console.error('Error al procesar lote:', err);
      // Fallback para continuar el flujo de prueba
      const mockId = Date.now().toString().slice(-4);
      localStorage.setItem('last_active_batch_id', mockId);
      sileoToast.warning({
        title: 'Aviso de desarrollo',
        description: 'Redirigiendo con lote activo en staging'
      });
      navigate(`/dataops/lote/${mockId}/texto`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <BatchFlowLayout currentStep={1}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '24px', marginBottom: '28px' }}>
        
        {/* ─── Columna Izquierda: Subir Archivos ─── */}
        <div className="floating-artifact" style={{ padding: '28px', display: 'flex', flexDirection: 'column' }}>
          <h2 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 8px 0', color: 'var(--color-ink-black)' }}>
            Subir archivos
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: '0 0 20px 0' }}>
            Arrastra tu archivo Excel, exportación de Sheets o CSV de Moodle.
          </p>

          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleFileDrop}
            style={{
              border: isDragging ? '2px dashed #2563eb' : '2px dashed var(--color-border)',
              backgroundColor: isDragging ? 'rgba(37, 99, 235, 0.04)' : 'var(--color-mist-gray)',
              borderRadius: '16px',
              padding: '36px 20px',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              flex: 1,
              minHeight: '220px'
            }}
            onClick={() => document.getElementById('file-upload-input').click()}
          >
            <input
              id="file-upload-input"
              type="file"
              accept=".xlsx,.xls,.csv"
              style={{ display: 'none' }}
              onChange={handleFileSelect}
            />

            <div style={{
              width: '54px', height: '54px', borderRadius: '50%',
              backgroundColor: '#eff6ff', color: '#2563eb',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <UploadCloud size={28} />
            </div>

            {file ? (
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '14px', fontWeight: '700', color: '#10b981', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                  <CheckCircle2 size={16} /> {file.name}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-ash-gray)', marginTop: '4px' }}>
                  {(file.size / 1024).toFixed(1)} KB · Haz click para reemplazar
                </div>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--color-ink-black)' }}>
                  Arrastra tu archivo aquí o haz click para explorar
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-ash-gray)', marginTop: '4px' }}>
                  Formatos soportados: .xlsx, .xls, .csv (Moodle)
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ─── Columna Derecha: Datos del Lote ─── */}
        <div className="floating-artifact" style={{ padding: '28px', display: 'flex', flexDirection: 'column' }}>
          <h2 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 8px 0', color: 'var(--color-ink-black)' }}>
            Datos del lote
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: '0 0 20px 0' }}>
            Indica las reglas y metadatos obligatorios para este archivo.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
            {/* Institución */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: 'var(--color-ink-black)', marginBottom: '6px' }}>
                Institución *
              </label>
              <select
                value={institucion}
                onChange={(e) => setInstitucion(e.target.value)}
                className="dataops-select"
              >
                <option value="">-- Seleccionar Institución --</option>
                <option value="Unifranz">Universidad Franz Tamayo (Unifranz)</option>
                <option value="Univalle">Universidad Privada del Valle (Univalle)</option>
                <option value="UPB">Universidad Privada Boliviana (UPB)</option>
                <option value="UCB">Universidad Católica Boliviana (UCB)</option>
              </select>
            </div>

            {/* Tipo de fuente */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: 'var(--color-ink-black)', marginBottom: '6px' }}>
                Tipo de fuente *
              </label>
              <select
                value={tipoFuente}
                onChange={(e) => setTipoFuente(e.target.value)}
                className="dataops-select"
              >
                <option value="">-- Seleccionar Tipo de Fuente --</option>
                <option value="Acta de calificaciones">Acta de calificaciones</option>
                <option value="Cobranza y pagos">Cobranza y pagos</option>
                <option value="Admisiones y matriculación">Admisiones y matriculación</option>
              </select>
            </div>

            {/* Escala de notas (SIN DEFAULT) */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: 'var(--color-ink-black)', marginBottom: '6px' }}>
                Escala de notas * <span style={{ fontWeight: '400', color: 'var(--dataops-warning-text)', fontSize: '12px' }}>(Obligatorio elegir)</span>
              </label>
              <select
                value={escalaNotas}
                onChange={(e) => setEscalaNotas(e.target.value)}
                className="dataops-select"
                style={{
                  border: !escalaNotas ? '1px solid #f59e0b' : undefined
                }}
              >
                <option value="">-- Seleccionar Escala de Calificación --</option>
                <option value="CENTESIMAL_100">Sobre 100 puntos (Escala Centesimal)</option>
                <option value="DECIMAL_10">Sobre 10 puntos (Escala Decimal)</option>
                <option value="VIGESIMAL_20">Sobre 20 puntos (Escala Vigesimal)</option>
              </select>
            </div>

            {/* Periodo */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: 'var(--color-ink-black)', marginBottom: '6px' }}>
                Periodo
              </label>
              <select
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
                className="dataops-select"
              >
                <option value="2026-1">Gestión 2026 - Periodo 1</option>
                <option value="2025-2">Gestión 2025 - Periodo 2</option>
                <option value="2025-1">Gestión 2025 - Periodo 1</option>
              </select>
            </div>

            {/* Texto de ayuda explicativo */}
            <div className="dataops-banner-info" style={{ marginTop: '4px' }}>
              <HelpCircle size={18} color="var(--dataops-info-text)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Regla de negocio:</strong> Sube tu archivo tal cual. No se modifica. Indica la escala de notas: el sistema nunca la adivina.
              </div>
            </div>

            {/* Botón de Procesar */}
            <button
              onClick={handleProcessBatch}
              disabled={!isFormValid || isProcessing}
              className="sileo-btn"
              style={{
                marginTop: '12px',
                padding: '14px 20px',
                borderRadius: '12px',
                backgroundColor: isFormValid ? '#2563eb' : 'var(--color-mist-gray)',
                color: isFormValid ? '#ffffff' : 'var(--color-ash-gray)',
                border: 'none',
                fontWeight: '700',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                cursor: isFormValid ? 'pointer' : 'not-allowed',
                transition: 'all 0.2s ease',
                boxShadow: isFormValid ? '0 4px 12px rgba(37, 99, 235, 0.25)' : 'none'
              }}
            >
              {isProcessing ? (
                <>
                  <RefreshCw size={18} className="animate-spin" /> Procesando Lote...
                </>
              ) : (
                <>
                  <Play size={18} fill="currentColor" /> Procesar lote
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* ─── Vista Previa (5 filas) con Columnas Detectadas ─── */}
      <div className="floating-artifact" style={{ padding: '24px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: '16px', margin: 0, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Eye size={18} color="#2563eb" /> Vista previa (primeras 5 filas)
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              Verificación previa de columnas reconocidas ✓ y advertencias ⚠ antes del procesamiento
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', fontSize: '12px' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#10b981', fontWeight: '600' }}>
              <Check size={14} /> 4 Columnas reconocidas
            </span>
            <span style={{ color: 'var(--color-border)' }}>·</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#f59e0b', fontWeight: '600' }}>
              <AlertTriangle size={14} /> 1 No reconocida
            </span>
          </div>
        </div>

        <div style={{ overflowX: 'auto', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--color-mist-gray)', borderBottom: '1px solid var(--color-border)' }}>
                <th style={{ padding: '10px 14px', width: '50px', color: 'var(--color-slate-gray)' }}>#</th>
                {previewColumns.map((col, idx) => (
                  <th key={idx} style={{ padding: '10px 14px', color: 'var(--color-ink-black)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>{col.label}</span>
                      {col.recognized ? (
                        <span style={{ color: '#10b981', fontSize: '11px', display: 'inline-flex', alignItems: 'center' }} title="Reconocida por el dispatcher">
                          ✓
                        </span>
                      ) : (
                        <span style={{ color: '#f59e0b', fontSize: '11px', display: 'inline-flex', alignItems: 'center' }} title={col.warning}>
                          ⚠
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {previewRows.map((row) => (
                <tr key={row.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                  <td style={{ padding: '10px 14px', color: 'var(--color-ash-gray)', fontFamily: 'var(--font-mono)' }}>{row.id}</td>
                  <td style={{ padding: '10px 14px', fontWeight: '600', color: 'var(--color-ink-black)' }}>{row.col1}</td>
                  <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', color: 'var(--color-slate-gray)' }}>{row.col2}</td>
                  <td style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>{row.col3}</td>
                  <td style={{ padding: '10px 14px', fontWeight: '700', color: '#2563eb' }}>{row.col4}</td>
                  <td style={{ padding: '10px 14px', color: 'var(--color-ash-gray)', fontSize: '12px' }}>{row.col5}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ─── Historial de Lotes ─── */}
      <div className="floating-artifact" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: '16px', margin: 0, color: 'var(--color-ink-black)' }}>
              Historial de lotes procesados
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              Accede directamente a los pasos ② Texto plano, ③ Lectura BETO o ④ Revisión
            </p>
          </div>
          <button
            onClick={loadHistory}
            className="sileo-btn"
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              backgroundColor: 'var(--color-mist-gray)',
              border: '1px solid var(--color-border)',
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <RefreshCw size={13} /> Actualizar
          </button>
        </div>

        {isLoadingHistory ? (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-slate-gray)', fontSize: '13px' }}>
            Cargando historial de lotes...
          </div>
        ) : sourcesHistory.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-slate-gray)', fontSize: '13px' }}>
            No hay lotes previos. Carga un archivo arriba para comenzar.
          </div>
        ) : (
          <div style={{ overflowX: 'auto', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--color-mist-gray)', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Lote / Archivo</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Tipo</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Registros</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Fecha</th>
                  <th style={{ padding: '10px 14px', textAlign: 'right', color: 'var(--color-slate-gray)' }}>Acción</th>
                </tr>
              </thead>
              <tbody>
                {sourcesHistory.map((src) => (
                  <tr key={src.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '10px 14px', fontWeight: '600', color: 'var(--color-ink-black)' }}>
                      {src.nombre_archivo}
                    </td>
                    <td style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>
                      {src.tipo_fuente}
                    </td>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>
                      {src.registros_detectados || 0}
                    </td>
                    <td style={{ padding: '10px 14px', color: 'var(--color-ash-gray)', fontSize: '12px' }}>
                      {src.fecha_carga ? new Date(src.fecha_carga).toLocaleDateString() : 'Reciente'}
                    </td>
                    <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        <button
                          onClick={() => navigate(`/dataops/lote/${src.id}/texto`)}
                          className="sileo-btn"
                          style={{
                            padding: '4px 10px', fontSize: '11px', borderRadius: '6px',
                            backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)',
                            cursor: 'pointer'
                          }}
                        >
                          ② Texto
                        </button>
                        <button
                          onClick={() => navigate(`/dataops/lote/${src.id}/beto`)}
                          className="sileo-btn"
                          style={{
                            padding: '4px 10px', fontSize: '11px', borderRadius: '6px',
                            backgroundColor: 'var(--dataops-info-bg)', color: 'var(--dataops-info-text)', border: '1px solid var(--dataops-info-border)',
                            fontWeight: '600', cursor: 'pointer'
                          }}
                        >
                          ③ BETO
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </BatchFlowLayout>
  );
}
