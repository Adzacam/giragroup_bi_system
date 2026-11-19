import { isAcademicSourceType } from '../../../utils/fileTypeDetector';
import { MAX_ARCHIVOS_POR_LOTE } from '../../../constants/dataopsConfig';

export const toggleUidSelection = (selectedUids, uid) => {
  const next = new Set(selectedUids);
  if (next.has(uid)) next.delete(uid);
  else next.add(uid);
  return Array.from(next);
};

export const isAllQueueSelected = (queuedFiles, selectedUids) => {
  if (!Array.isArray(queuedFiles) || queuedFiles.length === 0) return false;
  const set = new Set(selectedUids);
  return queuedFiles.every((item) => set.has(item.uid));
};

export const toggleSelectAllQueue = (queuedFiles, selectedUids) => {
  if (!Array.isArray(queuedFiles) || queuedFiles.length === 0) return [];
  if (isAllQueueSelected(queuedFiles, selectedUids)) return [];
  return queuedFiles.map((item) => item.uid);
};

export const getSelectedQueueFiles = (queuedFiles, selectedUids) => {
  if (!Array.isArray(queuedFiles) || queuedFiles.length === 0) return [];
  const set = new Set(selectedUids);
  return queuedFiles.filter((item) => set.has(item.uid));
};

export const validateQueueSelection = (
  selectedFiles,
  maxFiles = MAX_ARCHIVOS_POR_LOTE,
  institucion = 'GiraGroup Posgrado'
) => {
  const list = Array.isArray(selectedFiles) ? selectedFiles : [];
  const missingSourceTypeCount = list.filter((it) => !it?.sourceType).length;
  const missingScaleCount = list.filter(
    (it) => isAcademicSourceType(it?.sourceType) && !it?.tipoEscala
  ).length;
  const valid =
    list.length > 0 &&
    list.length <= maxFiles &&
    Boolean(institucion) &&
    missingSourceTypeCount === 0 &&
    missingScaleCount === 0;

  return {
    valid,
    selectedCount: list.length,
    missingSourceTypeCount,
    missingScaleCount,
  };
};

export const puedeEliminarLote = (src) =>
  src?.status === 'ERROR' && Boolean(src?.puede_eliminar);

export const puedeReintentarLote = (src) =>
  src?.status === 'ERROR' && Boolean(src?.puede_reintentar_lectura);

export const getAccionesBloqueHabilitadas = (selectedBatches) => {
  const list = Array.isArray(selectedBatches) ? selectedBatches : [];
  if (list.length === 0) {
    return { count: 0, canDelete: false, canRetry: false };
  }
  return {
    count: list.length,
    canDelete: list.every(puedeEliminarLote),
    canRetry: list.every(puedeReintentarLote),
  };
};

export const toggleBatchSelection = (selectedIds, idLote) => {
  const next = new Set(selectedIds);
  if (next.has(idLote)) next.delete(idLote);
  else next.add(idLote);
  return Array.from(next);
};

export const isAllBatchesSelected = (rows, selectedIds) => {
  if (!Array.isArray(rows) || rows.length === 0) return false;
  const set = new Set(selectedIds);
  return rows.every((r) => set.has(r.id_lote));
};

export const toggleSelectAllBatches = (rows, selectedIds) => {
  if (!Array.isArray(rows) || rows.length === 0) return [];
  if (isAllBatchesSelected(rows, selectedIds)) return [];
  return rows.map((r) => r.id_lote);
};
