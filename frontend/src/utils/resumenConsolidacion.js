/** Resumen de una consolidación: hechos (académicos + financieros) más estudiantes de admisión, que no generan hechos. */
export function resumenConsolidacion(r = {}) {
  const academicos = r.inserted_academico ?? 0;
  const financieros = r.inserted_financiero ?? 0;
  const admision = r.inserted_admision ?? 0;
  const partes = [`Académicos +${academicos}`, `Financieros +${financieros}`];
  if (admision > 0) partes.push(`Admisión +${admision}`);
  partes.push(`En revisión ${r.inserted_revision ?? 0}`);
  return { total: academicos + financieros + admision, detalle: partes.join(' · ') };
}
