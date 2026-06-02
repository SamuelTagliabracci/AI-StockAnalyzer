import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { applyTheme, type ThemeId } from './themes'

interface ThemeCtx {
  theme: ThemeId
  setTheme: (id: ThemeId) => void
}

const Ctx = createContext<ThemeCtx>({ theme: 'nasdaq', setTheme: () => {} })

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeId>(() => {
    const urlTheme = new URLSearchParams(window.location.search).get('theme') as ThemeId | null
    if (urlTheme && ['nasdaq', 'fallout', 'empire'].includes(urlTheme)) return urlTheme
    return (localStorage.getItem('theme') as ThemeId) || 'nasdaq'
  })
  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem('theme', theme)
  }, [theme])
  return <Ctx.Provider value={{ theme, setTheme }}>{children}</Ctx.Provider>
}

export const useTheme = () => useContext(Ctx)
