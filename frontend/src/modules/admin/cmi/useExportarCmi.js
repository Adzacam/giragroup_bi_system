import { useState } from 'react';
import { reportesApi } from '../../../api/reportesApi';
import { sileoToast } from '../../../services/sileoToast';

export default function useExportarCmi() {
  const [isExporting, setIsExporting] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);

  const exportar = async (formato, programa = '') => {
    try {
      setIsExporting(true);
      setShowExportMenu(false);
      sileoToast.info(`Generando exportación oficial en formato ${formato.toUpperCase()}...`);
      await reportesApi.exportarReporte({
        tipo: 'kpis',
        formato,
        gestion: String(new Date().getFullYear()),
        programa,
      });
      sileoToast.success(`Reporte CMI ${formato.toUpperCase()} generado y descargado.`);
    } catch (err) {
      console.error('Error al exportar reporte CMI:', err);
      sileoToast.error('Error al exportar reporte. Verifique sus permisos RBAC.');
    } finally {
      setIsExporting(false);
    }
  };

  return { isExporting, showExportMenu, setShowExportMenu, exportar };
}
