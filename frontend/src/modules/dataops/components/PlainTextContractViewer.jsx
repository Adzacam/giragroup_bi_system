import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileCode, Sparkles, CheckCircle2, Copy, Check, Zap, AlertCircle, FileText } from 'lucide-react';
import { sileoToast } from '../../../services/sileoToast';
import { dataopsApi } from '../../../api/dataopsApi';

export default function PlainTextContractViewer({ activeDocId = null, incomingFiles = [], sources = [], onSelectDoc = null }) {
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);
  const [records, setRecords] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState(activeDocId);

  // Sincronizar selección de documento cuando activeDocId cambia desde el padre
  useEffect(() => {
    if (activeDocId) {
      setSelectedDocId(activeDocId);
    } else if (sources.length > 0) {
      setSelectedDocId(sources[0].id);
    }
  }, [activeDocId, sources]);

  // Cargar registros de texto plano reales desde Registros de Ingesta
  useEffect(() => {
    let isMounted = true;
    const loadPlainText = async () => {
      setIsLoading(true);
      try {
        const res = await dataopsApi.getPlainTextRecords(selectedDocId ? String(selectedDocId) : null);
        if (isMounted) {
          if (res?.data && Array.isArray(res.data)) {
            setRecords(res.data);
          } else {
            setRecords([]);
          }
        }
      } catch (err) {
        if (isMounted) {
          console.warn('No se pudieron obtener registros de texto plano:', err);
          setRecords([]);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadPlainText();
    return () => { isMounted = false; };
  }, [selectedDocId]);

  // Obtener metadatos del documento seleccionado
  const currentDocMeta = sources.find(s => s.id === selectedDocId) || 
                         incomingFiles.find(f => f.id === selectedDocId) || 
                         (records[0] ? { name: records[0].nombre_archivo, type: records[0].tipo_fuente, id: records[0].id_documento } : null);

  const activeRecord = records[0] || null;

  // Generar el contrato de salida serializado a partir de las tuplas reales
  const contractOutput = activeRecord ? [
    '=== GIRAGROUP DATAOPS INGESTION CONTRACT v2.0 ===',
    `METADATA: DOC_ID=${activeRecord.id_documento || selectedDocId || 'N/A'} | ARCHIVO=${activeRecord.nombre_archivo || currentDocMeta?.name || 'Documento'} | TIPO=${activeRecord.tipo_fuente || currentDocMeta?.type || 'Tabular'}`,
    `TARGET_CONTRACT: Registros de Ingesta (Texto Plano) | SCORE_CONFIANZA=${activeRecord.score_confianza ?? '0.90'}`,
    `ESTADO_INTEGRIDAD: ${activeRecord.requiere_revision ? 'REQUIERE_REVISION (Dudoso / Incompleto)' : 'VALIDADO_CANONICO'}`,
    '--------------------------------------------------------------------------------',
    activeRecord.texto_plano || 'Sin contenido de texto plano'
  ].join('\n') : '';

  // Extraer muestra cruda
  const rawSnippet = activeRecord?.texto_plano 
    ? activeRecord.texto_plano.split('\n').slice(0, 4).join('\n') 
    : 'Sin filas crudas disponibles.';

  const handleCopy = () => {
    if (!contractOutput) return;
    navigator.clipboard.writeText(contractOutput);
    setCopied(true);
    sileoToast.success({
      title: 'Contrato Copiado',
      description: 'El texto plano estandarizado de staging se copió al portapapeles.'
    });
    setTimeout(() => setCopied(false), 2000);
  };

  // Lista de documentos disponibles para seleccionar
  const availableDocs = sources.length > 0 ? sources : incomingFiles;

  return (
    <div
      className="floating-artifact"
      style={{
        borderRadius: 'var(--radius-cards)',
        border: '1px solid var(--color-border)',
        padding: '24px 28px',
        backgroundColor: 'var(--color-paper-white)',
        marginBottom: '24px',
        boxShadow: 'var(--shadow-subtle)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
            <span
              style={{
                backgroundColor: 'rgba(217, 155, 38, 0.15)',
                color: 'var(--color-gira-gold, #D99B26)',
                fontSize: '10.5px',
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: '6px',
                letterSpacing: '0.4px',
                border: '1px solid rgba(217, 155, 38, 0.3)',
              }}
            >
              Contrato Canónico
            </span>
            <span
              style={{
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                color: 'var(--color-gira-gold, #D99B26)',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <FileCode size={13} /> Contrato de Salida Único · Serialización a Texto Plano
            </span>
          </div>
          <h3 className="serif-heading" style={{ fontSize: '20px', margin: '4px 0 0 0', color: 'var(--color-ink-black)' }}>
            Conversión Estandarizada bajo Contrato Canónico
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
            Transformación homogénea de filas heterogéneas a texto plano inmutable en el repositorio de <strong>Registros de Ingesta</strong>.
          </p>
        </div>

        {/* Selector de Documento Activo */}
        {availableDocs.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {availableDocs.map((doc) => {
              const docId = doc.id || doc.name;
              const isSelected = selectedDocId === docId || (selectedDocId === null && availableDocs[0]?.id === docId);
              return (
                <button
                  key={docId}
                  type="button"
                  onClick={() => {
                    setSelectedDocId(doc.id || null);
                    if (onSelectDoc) onSelectDoc(doc.id || null);
                  }}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '9999px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    border: isSelected ? '1px solid var(--color-ink-black)' : '1px solid var(--color-border)',
                    backgroundColor: isSelected ? 'var(--color-ink-black)' : 'var(--color-fog-white)',
                    color: isSelected ? 'var(--color-paper-white)' : 'var(--color-slate-gray)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {doc.name || `Documento ${docId}`}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {isLoading ? (
        <div style={{ padding: '36px', textAlign: 'center', color: 'var(--color-slate-gray)' }}>
          <div style={{ display: 'inline-block', marginBottom: '8px' }}>
            <Zap size={24} className="animate-spin" color="var(--color-gira-gold)" />
          </div>
          <p style={{ margin: 0, fontSize: '13px' }}>Consultando serialización canónica en base de datos...</p>
        </div>
      ) : records.length === 0 ? (
        <div
          style={{
            padding: '36px 20px',
            textAlign: 'center',
            backgroundColor: 'var(--color-fog-white)',
            borderRadius: '16px',
            border: '1px dashed var(--color-border)',
          }}
        >
          <FileText size={32} color="var(--color-slate-gray)" style={{ margin: '0 auto 10px auto', opacity: 0.7 }} />
          <h4 style={{ margin: '0 0 6px 0', fontSize: '15px', color: 'var(--color-ink-black)' }}>
            Sin registros de texto plano en staging
          </h4>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-slate-gray)', maxWidth: '520px', marginLeft: 'auto', marginRight: 'auto' }}>
            Cargue un archivo documental o ejecute la conversión a texto plano en el pipeline para visualizar el contrato canónico generado.
          </p>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '16px',
          }}
        >
          {/* Panel Izquierdo: Entrada Cruda Homologada */}
          <div
            style={{
              backgroundColor: 'var(--color-fog-white)',
              border: '1px solid var(--color-border)',
              borderRadius: '16px',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-alert-amber)', letterSpacing: '0.5px' }}>
                Entrada Tabular Homologada
              </span>
              <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-slate-gray)' }}>
                {currentDocMeta?.name || 'Fuente Activa'}
              </span>
            </div>

            <pre
              style={{
                margin: 0,
                padding: '12px',
                borderRadius: '10px',
                backgroundColor: '#17191c',
                color: '#fed7aa',
                fontSize: '12px',
                fontFamily: 'var(--font-mono)',
                lineHeight: 1.5,
                whiteSpace: 'pre-wrap',
                maxHeight: '230px',
                overflowY: 'auto',
              }}
            >
              {rawSnippet}
            </pre>

            <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--color-slate-gray)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={14} color="#1b8754" />
              <span>Fuente: <strong>{currentDocMeta?.type || 'Archivo Tabular'}</strong> ({records.length} bloque/s en staging)</span>
            </div>
          </div>

          {/* Panel Derecho: Contrato Canónico (Texto Plano Real) */}
          <div
            style={{
              backgroundColor: '#0f1113',
              border: '1px solid #1f2937',
              borderRadius: '16px',
              padding: '16px',
              position: 'relative',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#34d399', letterSpacing: '0.5px' }}>
                Contrato de Salida Estandarizado (Texto Plano)
              </span>
              <button
                type="button"
                onClick={handleCopy}
                style={{
                  background: 'none',
                  border: '1px solid #374151',
                  borderRadius: '6px',
                  color: '#9ca3af',
                  padding: '3px 8px',
                  fontSize: '11px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  cursor: 'pointer',
                }}
                title="Copiar texto plano canónico"
              >
                {copied ? <Check size={12} color="#34d399" /> : <Copy size={12} />}
                <span>{copied ? 'Copiado' : 'Copiar'}</span>
              </button>
            </div>

            <pre
              style={{
                margin: 0,
                padding: '12px',
                borderRadius: '10px',
                backgroundColor: '#0b0c0e',
                color: '#86efac',
                fontSize: '11.5px',
                fontFamily: 'var(--font-mono)',
                lineHeight: 1.45,
                whiteSpace: 'pre-wrap',
                maxHeight: '230px',
                overflowY: 'auto',
              }}
            >
              {contractOutput}
            </pre>

            <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn-pill-dark"
                onClick={() => navigate(selectedDocId ? `/dataops/beto-ner?docIds=${selectedDocId}` : '/dataops/beto-ner')}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <Zap size={14} color="var(--color-gira-gold)" />
                <span>Inspeccionar con BETO NER & Catálogos →</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
