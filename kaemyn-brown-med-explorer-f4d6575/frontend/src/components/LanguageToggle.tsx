import { useLanguage } from "@/lib/language"
import { Button } from "@/components/ui/button"

export function LanguageToggle() {
  const { mode, setMode } = useLanguage()
  return (
    <div className="inline-flex rounded-full border border-border bg-card p-0.5 text-xs">
      <Button
        type="button"
        size="sm"
        variant={mode === "simple" ? "default" : "ghost"}
        className="h-8 rounded-full px-3"
        aria-pressed={mode === "simple"}
        onClick={() => setMode("simple")}
      >
        Simple
      </Button>
      <Button
        type="button"
        size="sm"
        variant={mode === "detailed" ? "default" : "ghost"}
        className="h-8 rounded-full px-3"
        aria-pressed={mode === "detailed"}
        onClick={() => setMode("detailed")}
      >
        More detail
      </Button>
    </div>
  )
}
