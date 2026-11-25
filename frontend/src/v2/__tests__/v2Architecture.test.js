import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { toV2Path, toV1Path, isV2Pathname, V2_ROLE_REDIRECTS } from '../utils/v2Routes';
import { V2_ROUTE_MANIFEST, normalizeV2RouteKey, prefetchRouteAndData } from '../navigation/routeDataPrefetcherV2';
import { V2_FONT_PRESETS } from '../context/UiVersionContext';

const V2_DIR = path.resolve(__dirname, '..');

const AUTHORIZED_HEX_COLORS = new Set([
  '#0C1E33', '#FAF9F6', '#D99B26', '#F1B844', '#F6C866',
  '#FFFFFF', '#F2F2F3', '#17191C', '#777B86', '#979799', '#A3A6AF', '#ECECEC',
  '#FBE1D1', '#5D2A1A',
  '#0C0E12', '#161920', '#20252E', '#9CA3AF', '#6B7280', '#4B5563', '#29303C',
  '#2C1A14',
  '#1B8754', '#4ADE80',
  '#D9383A', '#F87171', '#FCA5A5',
  '#B45309', '#FBBF24', '#FDE047',
  '#0284C7', '#38BDF8', '#7DD3FC',
]);

function walkFiles(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== '__tests__') results.push(...walkFiles(full));
    } else {
      results.push(full);
    }
  }
  return results;
}

describe('Loop 1: Aislamiento de rutas /v2/* y 5 roles RBAC', () => {
  it('normaliza rutas oficiales y heredadas /v2/*', () => {
    expect(toV2Path('/dashboard')).toBe('/dashboard');
    expect(toV2Path('/v2/dashboard')).toBe('/dashboard');
    expect(toV2Path('/')).toBe('/');
    expect(toV1Path('/v2/dataops/ingesta')).toBe('/dataops/ingesta');
    expect(toV1Path('/v2')).toBe('/');
    expect(isV2Pathname('/v2/dashboard')).toBe(true);
    expect(isV2Pathname('/dashboard')).toBe(false);
  });

  it('define redirección raíz para los 5 roles RBAC', () => {
    const roles = ['ADMIN', 'AUDITOR_CALIDAD', 'DIRECTOR_ACADEMICO', 'ANALISTA_FINANCIERO', 'ANALISTA_MARKETING'];
    for (const r of roles) {
      expect(V2_ROLE_REDIRECTS[r]).toBeTruthy();
      expect(V2_ROLE_REDIRECTS[r].startsWith('/')).toBe(true);
      expect(V2_ROLE_REDIRECTS[r].startsWith('/v2/')).toBe(false);
    }
  });
});

describe('Loop 2: Sincronización Vista + Datos (21+ rutas)', () => {
  it('mapea todas las rutas principales del sistema en V2_ROUTE_MANIFEST', () => {
    const keys = Object.keys(V2_ROUTE_MANIFEST);
    expect(keys.length).toBeGreaterThanOrEqual(21);
    expect(normalizeV2RouteKey('/v2/dataops/lote/42/beto')).toBe('/dataops/beto');
    expect(normalizeV2RouteKey('/v2/dataops/lote/42/texto')).toBe('/dataops/texto');
    expect(normalizeV2RouteKey('/v2/dataops/lote/42/revision')).toBe('/dataops/revision');
  });

  it('espera chunk + datos en paralelo y respeta el tope de seguridad', async () => {
    let chunkLoaded = false;
    let dataLoaded = false;
    const mockManifest = {
      '/dashboard': {
        loadChunk: async () => { chunkLoaded = true; },
        prefetch: () => [Promise.resolve().then(() => { dataLoaded = true; })],
      },
    };
    const res = await prefetchRouteAndData('/v2/dashboard', 'ADMIN', {
      queryClient: { prefetchQuery: () => Promise.resolve() },
      manifest: mockManifest,
      timeoutMs: 500,
    });
    expect(res.status).toBe('ready');
    expect(chunkLoaded).toBe(true);
    expect(dataLoaded).toBe(true);
  });

  it('no bloquea la navegación si el servidor excede el timeout', async () => {
    const mockManifest = {
      '/dashboard': {
        loadChunk: () => new Promise(() => {}),
        prefetch: () => [],
      },
    };
    const res = await prefetchRouteAndData('/v2/dashboard', 'ADMIN', {
      manifest: mockManifest,
      timeoutMs: 30,
    });
    expect(res.status).toBe('timeout');
    expect(res.timedOut).toBe(true);
  });
});

describe('Loop 3: Disciplina estricta de colores y Tipografía Augen Pro', () => {
  it('audita 0 colores hexadecimales fuera de las 3 tablas en frontend/src/v2/', () => {
    const files = walkFiles(V2_DIR);
    const hexRegex = /#[0-9a-fA-F]{3,8}\b/g;
    const violations = [];

    for (const file of files) {
      const content = fs.readFileSync(file, 'utf8');
      const matches = content.match(hexRegex) || [];
      if (path.basename(file) !== 'v2-tokens.css') {
        if (matches.length > 0) {
          violations.push(`${path.basename(file)}: ${matches.join(', ')}`);
        }
      } else {
        for (const hex of matches) {
          if (!AUTHORIZED_HEX_COLORS.has(hex.toUpperCase())) {
            violations.push(`v2-tokens.css unauthorized hex: ${hex}`);
          }
        }
      }
    }

    expect(violations).toEqual([]);
  });

  it('incluye los 4 presets tipográficos en vivo con Augen Pro por defecto', () => {
    const ids = V2_FONT_PRESETS.map((p) => p.id);
    expect(ids).toEqual(['augen', 'jakarta', 'inter-tight', 'gira-original']);
  });
});

describe('Loop 4: Topbar largo en pastilla sin BottomBar ni Aa, Sidebar en pastilla, Botón G 180x180 y Geist 350/400', () => {
  it('NavbarV2 es una pastilla larga sin links de módulos ni FontSwitcherPopoverV2 y con marca GIRA Group', () => {
    const navbarSrc = fs.readFileSync(path.join(V2_DIR, 'layout', 'NavbarV2.jsx'), 'utf8');
    expect(navbarSrc).toContain('v2-topbar-pill');
    expect(navbarSrc).toContain('BI &amp; Intelligence System');
    expect(navbarSrc).not.toContain('FontSwitcherPopoverV2');
    expect(navbarSrc).not.toContain('V2_TOPBAR_ROLE_ITEMS');

    const mainLayoutSrc = fs.readFileSync(path.join(V2_DIR, 'layout', 'MainLayoutV2.jsx'), 'utf8');
    expect(mainLayoutSrc).toContain('MobileBottomNavV2');
  });

  it('incluye Sidebar oculto en pastilla, botón G 180x180 animado, CardFolder Framer, Geist 350/400 y botones fluidos', () => {
    const layoutCss = fs.readFileSync(path.join(V2_DIR, 'styles', 'v2-layout.css'), 'utf8');
    expect(layoutCss).toContain('border-radius: 36px');
    expect(layoutCss).toContain('border-radius: 9999px');
    expect(layoutCss).toContain('v2-gira-full-spin');
    expect(layoutCss).toContain('v2-mobile-pill');
    expect(layoutCss).toContain('stroke-dashoffset: 0');

    const tokensCss = fs.readFileSync(path.join(V2_DIR, 'styles', 'v2-tokens.css'), 'utf8');
    expect(tokensCss).toContain("'Geist'");
    expect(tokensCss).toContain('--v2-weight-heading: 350');
    expect(tokensCss).toContain('--v2-tracking: -0.020em');
    expect(tokensCss).toContain('.kinetic-card');

    const buttonsCss = fs.readFileSync(path.join(V2_DIR, 'styles', 'v2-buttons.css'), 'utf8');
    expect(buttonsCss).toContain('aria-busy="true"');
    expect(buttonsCss).toContain('v2-btn-shimmer');
    expect(buttonsCss).toContain('v2-btn-spin');

    const logoBtn = fs.readFileSync(path.join(V2_DIR, 'components', 'GiraAnimatedLogoButton.jsx'), 'utf8');
    expect(logoBtn).toContain('viewBox="0 0 180 180"');
    expect(logoBtn).toContain('M 83 29 L 123 69 Q 133 79 123 89 L 91 121 Q 81 131 71 121 L 40 90 Q 30 80 40 70 L 53 57 Q 63 47 73 57 L 96 81');

    const folder = fs.readFileSync(path.join(V2_DIR, 'components', 'CardFolderV2.jsx'), 'utf8');
    expect(folder).toContain('v2-folder-back');
    expect(folder).toContain('v2-folder-inner');
    expect(folder).toContain('v2-folder-front');
  });
});

describe('Loop 5 & Ronda 2: CmiScorecard Hooks/CardFolder, queryKeys reales y flushSync Padre->Hijo', () => {
  it('CmiScorecard invoca useParentChildTransitionV2 antes de los early returns y usa CardFolderV2', () => {
    const scorecardSrc = fs.readFileSync(
      path.resolve(V2_DIR, '..', 'modules', 'admin', 'cmi', 'scorecard', 'CmiScorecard.jsx'),
      'utf8'
    );
    const tarjetaSrc = fs.readFileSync(
      path.resolve(V2_DIR, '..', 'modules', 'admin', 'cmi', 'scorecard', 'TarjetaKpi.jsx'),
      'utf8'
    );
    const hookPos = scorecardSrc.indexOf('useParentChildTransitionV2()');
    const loadingPos = scorecardSrc.indexOf('if (isLoading)');
    expect(hookPos).toBeGreaterThan(-1);
    expect(loadingPos).toBeGreaterThan(-1);
    expect(hookPos).toBeLessThan(loadingPos);
    expect(tarjetaSrc).toContain('CardFolderV2');
  });

  it('routeDataPrefetcherV2 usa las queryKeys reales de las vistas', () => {
    const prefetcherSrc = fs.readFileSync(
      path.join(V2_DIR, 'navigation', 'routeDataPrefetcherV2.js'),
      'utf8'
    );
    expect(prefetcherSrc).toContain("['cmi', 'scorecard', null]");
    expect(prefetcherSrc).toContain("['analiticaPredictivaMacro', 6]");
    expect(prefetcherSrc).toContain("['finance', 'metas-gestion']");
    expect(prefetcherSrc).not.toContain("['v2', 'cmi'");
  });

  it('congela las barras, usa flushSync y define parent-child + pastillas animadas + reduced-motion', () => {
    const hookSrc = fs.readFileSync(path.join(V2_DIR, 'transitions', 'useParentChildTransitionV2.js'), 'utf8');
    expect(hookSrc).toContain('flushSync');

    const css = fs.readFileSync(path.join(V2_DIR, 'styles', 'v2-transitions.css'), 'utf8');
    expect(css).toContain('view-transition-name: v2-container-expand');
    expect(css).toContain('view-transition-name: v2-parent-child-card');
    expect(css).toContain('view-transition-name: v2-parent-child-panel');
    expect(css).toContain('view-transition-name: v2-parent-child-subpanel');
    expect(css).toContain('.v2-pill-segment');
    expect(css).toContain('v2-shell-sidebar');
    expect(css).toContain('v2-shell-topbar');
    expect(css).toContain('sibling-forward');
    expect(css).toContain('sibling-backward');
    expect(css).toContain('@supports ((animation-timeline: view()) and (animation-range: entry))');
    expect(css).toContain('@media (prefers-reduced-motion: reduce)');
  });
});
