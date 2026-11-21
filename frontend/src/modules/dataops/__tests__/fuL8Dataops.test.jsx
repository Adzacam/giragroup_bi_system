import React from 'react';
import fs from 'node:fs';
import path from 'node:path';
import { describe, it, expect, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import {
  MOTIVOS_BANDEJA,
  MOTIVOS_INFORMATIVOS,
  maskCi,
  maskNombre,
  maskTexto,
  textoMotivo,
} from '../../../constants/motivosBandeja';
import GruposBandeja from '../components/GruposBandeja';
import BetoReadingFlowView from '../BetoReadingFlowView';
import { LoteFlowProvider } from '../context/LoteFlowContext';
import { NotificationProvider } from '../../../context/NotificationContext';

vi.mock('../../../context/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'auditor', role: 'AUDITOR_CALIDAD' } }),
}));

vi.mock('../components/BatchFlowLayout', () => ({
  default: ({ children }) => <div data-testid="batch-flow-layout">{children}</div>,
}));

vi.mock('../../../api/dataopsApi', () => ({
  dataopsApi: {
    getLoteContext: vi.fn(),
    getBetoReading: vi.fn(),
    getResumen: vi.fn(),
  },
}));

vi.mock('../context/LoteFlowContext', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useLoteFlow: () => ({
      context: { id_lote: 1, estado_flujo: 'LEIDO_BETO', archivos: [] },
      isLoading: false,
      readOnly: false,
      batchId: '1',
      steps: [],
    }),
  };
});

vi.mock('../hooks/useLecturaBeto', () => ({
  default: () => ({
    ready: true,
    processing: false,
    readOnly: false,
    contexto: { id_lote: 1, estado_flujo: 'LEIDO_BETO', archivos: [] },
    summary: {
      total_procesados: 100,
      aceptados_automaticamente: 80,
      por_revisar: 15,
      con_incidencias: 5,
    },
    pagination: { page: 1, total_pages: 1, total_items: 0 },
    data: {
      status: 'success',
      id_lote: 1,
      resumen_ejecutivo: {
        total_procesados: 100,
        aceptados_automaticamente: 80,
        por_revisar: 15,
        con_incidencias: 5,
      },
      resumen_cascada: {
        CI_EXACTA: 50,
        ENCABEZADO: 30,
        FUZZY: 10,
        REGEX: 5,
        BETO: 5,
        total_entidades: 100,
        etapas: [
          { etapa: 'CI_EXACTA', cantidad: 50, porcentaje: 50.0 },
          { etapa: 'ENCABEZADO', cantidad: 30, porcentaje: 30.0 },
          { etapa: 'FUZZY', cantidad: 10, porcentaje: 10.0 },
          { etapa: 'REGEX', cantidad: 5, porcentaje: 5.0 },
          { etapa: 'BETO', cantidad: 5, porcentaje: 5.0 },
        ],
      },
      registros: [],
      pagination: { page: 1, total_pages: 1, total_items: 0 },
    },
    isFetching: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

describe('FU-B3 — DataOps FU-L8 (motivosBandeja, GruposBandeja, BetoReadingFlowView, cero hex y cero PII)', () => {
  it('motivosBandeja incluye los 8 motivos nuevos, MOTIVOS_INFORMATIVOS y enmascara PII', () => {
    const nuevos = [
      'HOJA_IGNORADA',
      'NOTA_FUERA_DE_RANGO',
      'RESPUESTA_EN_COLUMNA_EQUIVOCADA',
      'CUOTAS_NEGATIVAS',
      'CONFLICTO_META',
      'VALOR_FUERA_DE_CATALOGO',
      'PUNTUACION_FUERA_DE_ESCALA',
      'ESCALA_NO_INFERIBLE',
    ];
    for (const m of nuevos) {
      expect(MOTIVOS_BANDEJA[m]).toBeTruthy();
      expect(textoMotivo(m)).toBe(MOTIVOS_BANDEJA[m]);
    }
    expect(MOTIVOS_INFORMATIVOS.has('HOJA_IGNORADA')).toBe(true);
    const masked = maskTexto('CI: 12345678 | Nombre: Juan Carlos Perez | valor: 999');
    expect(masked).not.toContain('12345678');
    expect(masked).not.toContain('Juan Carlos Perez');
    expect(maskCi('12345678')).toBe('12***78');
    expect(maskNombre('Juan Perez')).toContain('(Anonimizado)');
  });

  it('GruposBandeja renderiza patrones, bloque "Por qué está aquí" y cero PII', () => {
    const html = renderToStaticMarkup(
      <GruposBandeja
        data={{
          patrones: [
            { motivo: 'CI_NOMBRE_DISCORDANTE', patron: 'Nombre muy distinto (similitud < 30)', n: 12, grupos: 4 },
          ],
          grupos: [
            {
              clave: 'grupo-abc',
              motivo: 'NOTA_FUERA_DE_RANGO',
              titulo: 'Nota fuera de rango',
              n: 3,
              accion_grupo: 'MANUAL',
              patron: 'Nombre muy distinto (similitud < 30)',
              ejemplo: 'CI: 88776655 | Nota: 13622300',
              explicacion: {
                regla: 'Rango válido de nota académica',
                umbral: '0 ≤ nota ≤ 100',
                valor_enmascarado: 'CI: 88***55 | Nota: 13***00',
              },
            },
          ],
        }}
        readOnly={false}
        busy={false}
        onVerIndividual={() => {}}
        onResolver={() => {}}
      />
    );
    expect(html).toContain('Nombre muy distinto');
    expect(html).toContain('Por qué está aquí');
    expect(html).toContain('Rango válido de nota académica');
    expect(html).toContain('0 ≤ nota ≤ 100');
    expect(html).not.toContain('88776655');
  });

  it('BetoReadingFlowView renderiza resumen_cascada con bloque "Qué significa:"', () => {
    const qc = new QueryClient();
    const html = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <NotificationProvider>
          <MemoryRouter initialEntries={['/dataops/lote/1/lectura']}>
            <LoteFlowProvider>
              <Routes>
                <Route path="/dataops/lote/:id/lectura" element={<BetoReadingFlowView />} />
              </Routes>
            </LoteFlowProvider>
          </MemoryRouter>
        </NotificationProvider>
      </QueryClientProvider>
    );
    expect(html).toContain('Cascada de resolución por etapa');
    expect(html).toContain('Cédula exacta');
    expect(html).toContain('Encabezado del archivo');
    expect(html).toContain('Coincidencia aproximada');
    expect(html).toContain('Leído por BETO');
    expect(html).toContain('Qué significa:');
  });

  it('guardia cero hex sueltos en los archivos DataOps modificados', () => {
    const archivos = [
      'src/modules/dataops/IngestView.jsx',
      'src/modules/dataops/BetoReadingFlowView.jsx',
      'src/modules/dataops/HumanReviewFlowView.jsx',
      'src/modules/dataops/components/GruposBandeja.jsx',
    ];
    for (const rel of archivos) {
      const full = path.resolve(process.cwd(), rel);
      const contenido = fs.readFileSync(full, 'utf-8');
      const matches = contenido.match(/#[0-9a-fA-F]{3,8}\b/g) || [];
      expect(matches, `Hex sueltos encontrados en ${rel}: ${matches.join(', ')}`).toEqual([]);
    }
  });
});
