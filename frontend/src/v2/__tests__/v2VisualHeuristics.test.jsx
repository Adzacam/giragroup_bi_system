import React from 'react';
import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import fs from 'node:fs';
import path from 'node:path';

import IngestBatchFilesTable from '../../modules/dataops/components/IngestBatchFilesTable';
import GruposBandeja from '../../modules/dataops/components/GruposBandeja';
import NotificationPopover from '../../components/notifications/NotificationPopover';

describe('Correcciones visuales y heurísticas V2', () => {
  it('IngestBatchFilesTable muestra el estado como badge limpio sin corchetes literales', () => {
    const html = renderToStaticMarkup(
      <IngestBatchFilesTable
        prepKpis={[['Registros', 10]]}
        inspectedPagination={{
          visibles: [{
            key: 'doc-1',
            nombre: 'notas_2025.xlsx',
            origen: 'ACADEMICO',
            filas: 120,
            fechas: '2025',
            estado: 'Texto listo',
          }],
          pagina: 1,
          totalPaginas: 1,
          total: 1,
          filasPorPagina: 10,
          setPagina: () => {},
        }}
        expandedDetailKey={null}
        onToggleExpand={() => {}}
      />
    );
    expect(html).toContain('Texto listo');
    expect(html).not.toContain('[Texto listo]');
  });

  it('GruposBandeja muestra diferenciador secundario discreto cuando varios grupos comparten motivo', () => {
    const html = renderToStaticMarkup(
      <GruposBandeja
        data={{
          grupos: [
            {
              clave: 'grupo-abc123def456',
              motivo: 'SIN_ESTUDIANTE_O_DOCENTE',
              titulo: 'No se pudo identificar a la persona',
              archivo_origen: 'archivo_a.xlsx',
              n: 5,
              accion_grupo: 'MANUAL',
            },
            {
              clave: 'grupo-987654fedcba',
              motivo: 'SIN_ESTUDIANTE_O_DOCENTE',
              titulo: 'No se pudo identificar a la persona',
              archivo_origen: 'archivo_b.xlsx',
              n: 3,
              accion_grupo: 'MANUAL',
            },
          ],
        }}
        readOnly={false}
        busy={false}
        onVerIndividual={() => {}}
        onResolver={() => {}}
      />
    );
    expect(html).toContain('archivo_a.xlsx');
    expect(html).toContain('#abc123');
    expect(html).toContain('archivo_b.xlsx');
    expect(html).toContain('#987654');
  });

  it('NotificationPopover incluye role="dialog" y NotificationBell cierra con Escape', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <NotificationPopover notifications={[]} onMarkAllRead={() => {}} onClose={() => {}} />
      </MemoryRouter>
    );
    expect(html).toContain('role="dialog"');

    const bellSrc = fs.readFileSync(
      path.resolve(process.cwd(), 'src/components/notifications/NotificationBell.jsx'),
      'utf8'
    );
    expect(bellSrc).toContain("event.key === 'Escape'");
    expect(bellSrc).toContain('keydown');
  });

  it('dataops-flow.css define contraste explícito para .btn-pill-gold:disabled en claro y oscuro', () => {
    const css = fs.readFileSync(
      path.resolve(process.cwd(), 'src/styles/dataops-flow.css'),
      'utf8'
    );
    expect(css).toContain('.btn-pill-gold:disabled');
    expect(css).toContain('[data-theme="dark"] .btn-pill-gold:disabled');
    expect(css).toContain('var(--color-ink-black)');

    const dropzoneSrc = fs.readFileSync(
      path.resolve(process.cwd(), 'src/modules/dataops/components/IngestDropzonePanel.jsx'),
      'utf8'
    );
    expect(dropzoneSrc).not.toContain('sileo-btn');
  });

  it('AvisosTab aplica overflowWrap anywhere y minWidth 0 para códigos largos en móvil', () => {
    const src = fs.readFileSync(
      path.resolve(process.cwd(), 'src/modules/dataops/components/AvisosTab.jsx'),
      'utf8'
    );
    expect(src).toContain("overflowWrap: 'anywhere'");
    expect(src).toContain('minWidth: 0');
  });

  it('VistaGeneralCmi usa color visible en modo oscuro y HumanReviewFlowView consulta lectura BETO', () => {
    const cmiSrc = fs.readFileSync(
      path.resolve(process.cwd(), 'src/modules/admin/cmi/scorecard/VistaGeneralCmi.jsx'),
      'utf8'
    );
    expect(cmiSrc).toContain('isDark ? tokens.gold : tokens.navy');

    const revSrc = fs.readFileSync(
      path.resolve(process.cwd(), 'src/modules/dataops/HumanReviewFlowView.jsx'),
      'utf8'
    );
    expect(revSrc).toContain('getLoteBetoReading');
    expect(revSrc).toContain('aceptados_automaticamente');
  });
});
