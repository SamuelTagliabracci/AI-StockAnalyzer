// Theme engine: each theme is a flat map of CSS variables applied to <html>.
// Swapping a theme = swapping this token set + a data-theme attribute (for
// theme-specific visual flourishes like scanlines / starfields defined in CSS).

export type ThemeId = 'nasdaq' | 'fallout' | 'empire'

export interface ThemeMeta {
  id: ThemeId
  label: string
  blurb: string
  vars: Record<string, string>
}

export const THEMES: Record<ThemeId, ThemeMeta> = {
  // ---- Flagship: polished pro trading desk -------------------------------
  nasdaq: {
    id: 'nasdaq',
    label: 'NASDAQ Terminal',
    blurb: 'Pro trading desk',
    vars: {
      '--bg': '#04070b',
      '--bg-grid': 'rgba(34, 197, 180, 0.05)',
      '--panel': '#0a1018',
      '--panel-2': '#0d141d',
      '--border': '#16212e',
      '--border-bright': '#1f3344',
      '--text': '#d7e2ee',
      '--text-dim': '#67788c',
      '--text-bright': '#ffffff',
      '--up': '#00e08a',
      '--down': '#ff4d5e',
      '--accent': '#19d4ff',
      '--accent-glow': 'rgba(25, 212, 255, 0.45)',
      '--warn': '#ffcb47',
      '--font-mono': "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace",
      '--font-ui': "'Inter', system-ui, -apple-system, sans-serif",
      '--radius': '6px',
      '--scan-opacity': '0',
    },
  },
  // ---- Showcase skins (engine-ready; tuned later) ------------------------
  fallout: {
    id: 'fallout',
    label: 'Vault-Tec / Pip-Boy',
    blurb: 'Fallout 3 CRT',
    vars: {
      '--bg': '#05140a',
      '--bg-grid': 'rgba(74, 255, 142, 0.06)',
      '--panel': '#06180c',
      '--panel-2': '#082110',
      '--border': '#0f3d22',
      '--border-bright': '#2bff88',
      '--text': '#42ff90',
      '--text-dim': '#1f8f4e',
      '--text-bright': '#b9ffd0',
      '--up': '#7dffa8',
      '--down': '#ffd23f',
      '--accent': '#42ff90',
      '--accent-glow': 'rgba(66, 255, 144, 0.5)',
      '--warn': '#ffd23f',
      '--font-mono': "'JetBrains Mono', ui-monospace, monospace",
      '--font-ui': "'JetBrains Mono', ui-monospace, monospace",
      '--radius': '2px',
      '--scan-opacity': '0.5',
    },
  },
  empire: {
    id: 'empire',
    label: 'Galactic Empire',
    blurb: 'Imperial holo-console',
    vars: {
      '--bg': '#02060d',
      '--bg-grid': 'rgba(80, 180, 255, 0.05)',
      '--panel': '#050d18',
      '--panel-2': '#07121f',
      '--border': '#10293f',
      '--border-bright': '#2e8fd6',
      '--text': '#afe0ff',
      '--text-dim': '#4f7493',
      '--text-bright': '#eaf6ff',
      '--up': '#54d6ff',
      '--down': '#ff5470',
      '--accent': '#37b6ff',
      '--accent-glow': 'rgba(55, 182, 255, 0.5)',
      '--warn': '#ff9f1c',
      '--font-mono': "'JetBrains Mono', ui-monospace, monospace",
      '--font-ui': "'Inter', system-ui, sans-serif",
      '--radius': '0px',
      '--scan-opacity': '0.15',
    },
  },
}

export function applyTheme(id: ThemeId) {
  const root = document.documentElement
  const theme = THEMES[id]
  for (const [k, v] of Object.entries(theme.vars)) root.style.setProperty(k, v)
  root.setAttribute('data-theme', id)
}
