import { useTheme } from '../themes/ThemeContext'
import { THEMES, type ThemeId } from '../themes/themes'

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme()
  return (
    <div className="flex items-center gap-1">
      <span className="tag mr-1">THEME</span>
      {(Object.keys(THEMES) as ThemeId[]).map((id) => (
        <button
          key={id}
          className={theme === id ? 'btn btn-active' : 'btn'}
          aria-pressed={theme === id}
          onClick={() => setTheme(id)}
          title={THEMES[id].blurb}
        >
          {THEMES[id].label.split(' ')[0]}
        </button>
      ))}
    </div>
  )
}
