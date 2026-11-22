import React, { useEffect, useState } from 'react';
import Button from '../../../components/shared/Button';
import EntityHighlightText from './EntityHighlightText';

/**
 * Renderizador genérico de `acciones[]` (DF-L3 b / DF-L8 c).
 * No conoce motivos ni límites fijos: todo llega en el descriptor del backend.
 */
export default function ReviewActionRenderer({
  item,
  readOnly = false,
  busy = false,
  onExecute,
  onReopen = null,
  activeActionIdx = 0,
  onSelectActionIdx = null,
}) {
  const acciones = Array.isArray(item?.acciones) && item.acciones.length > 0
    ? item.acciones
    : (Array.isArray(item?.campos_correccion) && item.campos_correccion.length > 0
      ? [{ codigo: 'APROBAR', etiqueta: 'Aprobar con corrección', widget: 'ValueCorrector', campos: item.campos_correccion, precarga: {} }]
      : []);
  const [selectedIdx, setSelectedIdx] = useState(activeActionIdx);
  const idx = onSelectActionIdx ? activeActionIdx : selectedIdx;
  const setIdx = onSelectActionIdx || setSelectedIdx;
  const accion = acciones[idx] || acciones[0] || null;
  const [form, setForm] = useState({});

  useEffect(() => {
    if (!accion) return;
    const next = {};
    for (const c of accion.campos || []) {
      const pre = accion.precarga?.[c.name];
      next[c.name] = pre !== undefined && pre !== null ? pre : (c.default ?? '');
    }
    setForm(next);
  }, [item?.id, accion?.codigo]);

  if (!acciones.length) {
    return (
      <div style={{ marginTop: 12 }}>
        <p style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>Sin acciones disponibles para este estado.</p>
        {onReopen && !readOnly && (
          <Button variant="ghost" style={{ marginTop: 8 }} disabled={busy} onClick={() => onReopen(item)}>
            Reabrir caso
          </Button>
        )}
      </div>
    );
  }

  const candidatos = Array.isArray(item?.candidatos) && item.candidatos.length > 0
    ? item.candidatos
    : (Array.isArray(accion?.precarga?.candidatos) ? accion.precarga.candidatos : []);

  const submitAction = () => {
    if (!accion || busy || readOnly) return;
    const faltantes = (accion.campos || []).filter((c) => {
      if (!c.required) return false;
      const v = form[c.name];
      return v === undefined || v === null || String(v).trim() === '';
    });
    if (faltantes.length > 0) return;
    onExecute(item, accion, form);
  };

  return (
    <div style={{ marginTop: 12 }}>
      {accion?.widget === 'EntityTagEditor' && (
        <div style={{ padding: 12, borderRadius: 10, background: 'var(--color-mist-gray)', marginBottom: 12 }}>
          <p style={{ fontSize: 11.5, fontWeight: 600, marginBottom: 6, color: 'var(--color-slate-gray)' }}>Entidades detectadas (IOB2)</p>
          <EntityHighlightText
            text={item?.que_vio || ''}
            betoEnts={accion.precarga?.beto_ents || []}
            entidades={item?.entidades || accion.precarga?.entidades || []}
          />
        </div>
      )}

      {accion?.widget === 'IdentityCompare' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10, padding: 12, borderRadius: 10, background: 'var(--color-mist-gray)', marginBottom: 12 }}>
          <div><span style={{ fontSize: 11, color: 'var(--color-slate-gray)' }}>Nombre en fuente</span><p style={{ fontWeight: 600 }}>{item?.estudiante || 'Sin dato'}</p></div>
          <div><span style={{ fontSize: 11, color: 'var(--color-slate-gray)' }}>Padrón (CI {item?.ci_enmascarado || 'Sin CI'})</span><p style={{ fontWeight: 600 }}>{item?.sugerencia || '••••'}</p></div>
          {item?.similitud_nombre_completo != null && (
            <div><span style={{ fontSize: 11, color: 'var(--color-slate-gray)' }}>Similitud</span><p style={{ fontWeight: 700 }}>{Math.round(Number(item.similitud_nombre_completo) * 100)} %</p></div>
          )}
        </div>
      )}

      {accion?.widget === 'CandidateSelector' && candidatos.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Candidatos sugeridos (haz clic para elegir):</p>
          <div style={{ display: 'grid', gap: 6 }}>
            {candidatos.map((cand, i) => {
              const cid = cand.id_estudiante ?? cand.id ?? i;
              const selected = String(form.id_estudiante_candidato ?? '') === String(cid);
              return (
                <button
                  key={cid}
                  type="button"
                  disabled={busy || readOnly}
                  onClick={() => setForm((prev) => ({ ...prev, id_estudiante_candidato: cid }))}
                  style={{
                    textAlign: 'left',
                    padding: '8px 12px',
                    borderRadius: 10,
                    border: `1px solid ${selected ? 'var(--color-gira-gold)' : 'var(--color-border)'}`,
                    background: selected ? 'var(--dataops-info-bg)' : 'var(--color-pure-white)',
                    color: 'var(--color-ink-black)',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: 8,
                    fontSize: 12,
                  }}
                >
                  <span><strong>{cand.nombre || '••••'}</strong> · CI {cand.ci_enmascarada || 'Sin CI'} · {cand.programa || 'Sin programa'}</span>
                  <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--color-slate-gray)' }}>
                    Similitud {cand.similitud ?? '—'} %{cand.probabilidad_beto != null ? ` · BETO ${Math.round(Number(cand.probabilidad_beto) * 100)} %` : ''}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {!readOnly && (
        <>
          <div role="tablist" aria-label="Acciones disponibles" style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
            {acciones.map((a, i) => (
              <Button
                key={a.codigo}
                type="button"
                variant="ghost"
                role="tab"
                aria-selected={i === idx}
                disabled={busy}
                onClick={() => setIdx(i)}
                style={{
                  fontSize: 12,
                  borderColor: i === idx ? 'var(--color-gira-gold)' : 'var(--color-border)',
                  background: i === idx ? 'var(--dataops-info-bg)' : undefined,
                  color: i === idx ? 'var(--dataops-info-text)' : undefined,
                }}
              >
                {a.etiqueta}
              </Button>
            ))}
          </div>

          {accion && (
            <div style={{ display: 'grid', gap: 10, padding: 14, borderRadius: 12, border: '1px solid var(--color-border)' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
                {(accion.campos || []).map((c) => {
                  const val = form[c.name] ?? '';
                  if (c.type === 'checkbox') {
                    return (
                      <label key={c.name} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, paddingTop: 16 }}>
                        <input
                          type="checkbox"
                          checked={Boolean(val)}
                          disabled={busy}
                          onChange={(e) => setForm((prev) => ({ ...prev, [c.name]: e.target.checked }))}
                        />
                        {c.label}
                      </label>
                    );
                  }
                  if (c.type === 'select' && Array.isArray(c.options)) {
                    return (
                      <label key={c.name} style={{ fontSize: 12 }}>
                        {c.label}{c.required ? ' *' : ''}
                        <select
                          name={c.name}
                          aria-label={c.label}
                          className="dataops-select"
                          value={val}
                          disabled={busy}
                          onChange={(e) => setForm((prev) => ({ ...prev, [c.name]: e.target.value }))}
                        >
                          <option value="">Selecciona…</option>
                          {c.options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                        </select>
                      </label>
                    );
                  }
                  return (
                    <label key={c.name} style={{ fontSize: 12 }}>
                      {c.label}{c.required ? ' *' : ''}
                      <input
                        name={c.name}
                        aria-label={c.label}
                        className="dataops-input"
                        type={c.type === 'number' ? 'number' : c.type === 'date' ? 'date' : 'text'}
                        value={val}
                        disabled={busy}
                        maxLength={c.max_length || undefined}
                        min={c.min !== undefined ? c.min : undefined}
                        max={c.max !== undefined ? c.max : undefined}
                        onChange={(e) => setForm((prev) => ({ ...prev, [c.name]: e.target.value }))}
                      />
                    </label>
                  );
                })}
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                <Button
                  type="button"
                  variant="ghost"
                  className={accion.codigo === 'DESCARTAR' || accion.codigo === 'DESCARTAR_VACIA' ? '' : 'btn-pill-gold'}
                  disabled={busy}
                  onClick={submitAction}
                >
                  {accion.etiqueta}
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {onReopen && !readOnly && (
        <Button variant="ghost" style={{ marginTop: 10 }} disabled={busy} onClick={() => onReopen(item)}>
          Reabrir caso
        </Button>
      )}
    </div>
  );
}
