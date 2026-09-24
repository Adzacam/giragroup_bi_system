/**
 * Centralized system constants and design token metadata
 * Eliminates magic strings across views, forms, notifications, and telemetry.
 */

export const NOTIFICATION_SEVERITIES = {
  INFO: 'INFO',
  WARNING: 'WARNING',
  CRITICAL: 'CRITICAL',
};

export const NOTIFICATION_CATEGORIES = {
  RIESGO_ACADEMICO: 'RIESGO_ACADEMICO',
  CALIDAD_DATAOPS: 'CALIDAD_DATAOPS',
  SEGURIDAD: 'SEGURIDAD',
  FINANZAS: 'FINANZAS',
};

export const USER_ROLES = {
  ADMIN: 'ADMIN',
  AUDITOR_CALIDAD: 'AUDITOR_CALIDAD',
  DIRECTOR_ACADEMICO: 'DIRECTOR_ACADEMICO',
  ANALISTA_FINANCIERO: 'ANALISTA_FINANCIERO',
};

export const DEMO_ACCOUNTS = [
  { 
    label: 'Administrador del Sistema', 
    email: 'admin.general@giragroup.bo', 
    role: USER_ROLES.ADMIN 
  },
  { 
    label: 'Auditor de Calidad (DataOps)', 
    email: 'auditor.dataops@giragroup.bo', 
    role: USER_ROLES.AUDITOR_CALIDAD 
  },
  { 
    label: 'Director Académico', 
    email: 'direccion.academica@giragroup.bo', 
    role: USER_ROLES.DIRECTOR_ACADEMICO 
  },
  { 
    label: 'Analista Financiero', 
    email: 'analista.finanzas@giragroup.bo', 
    role: USER_ROLES.ANALISTA_FINANCIERO 
  },
];

export const PIPELINE_STAGES = [
  { id: 1, name: 'Archivo Origen', timing: '45ms', detail: 'Parseo UTF-8', icon: 'FileUp' },
  { id: 2, name: 'Dispatcher', timing: '110ms', detail: 'Acta_POS', icon: 'Split' },
  { id: 3, name: 'Limpieza', timing: '310ms', detail: 'Sanitizado', icon: 'Wand2' },
  { id: 4, name: 'Cabeceras', timing: '140ms', detail: '12 Columnas', icon: 'TableProperties' },
  { id: 5, name: 'Esquema', timing: '195ms', detail: '95.8% Validez', icon: 'ShieldCheck' },
  { id: 6, name: 'A Staging', timing: '85ms', detail: 'INSERT batch', icon: 'Database' },
];
