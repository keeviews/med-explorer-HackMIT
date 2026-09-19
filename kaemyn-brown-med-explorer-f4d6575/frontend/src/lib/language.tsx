import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react"

import { COPY, type LanguageMode } from "@/lib/copy"

const STORAGE_KEY = "discussmeds.language"

type LanguageContextValue = {
  mode: LanguageMode
  simple: boolean
  setMode: (mode: LanguageMode) => void
  copy: (typeof COPY)[LanguageMode]
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

function loadMode(): LanguageMode {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === "detailed" || raw === "simple") return raw
  } catch {
    /* ignore */
  }
  return "simple"
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<LanguageMode>(() => loadMode())

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, mode)
  }, [mode])

  const value = useMemo(
    () => ({
      mode,
      simple: mode === "simple",
      setMode: setModeState,
      copy: COPY[mode],
    }),
    [mode],
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage(): LanguageContextValue {
  const value = useContext(LanguageContext)
  if (!value) throw new Error("useLanguage must be used within LanguageProvider")
  return value
}
