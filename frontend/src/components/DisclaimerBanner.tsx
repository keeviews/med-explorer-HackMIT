import { AlertTriangle } from "lucide-react"

type DisclaimerBannerProps = {
  text: string
}

export function DisclaimerBanner({ text }: DisclaimerBannerProps) {
  return (
    <div role="note" className="border-b border-amber-300/80 bg-amber-100 text-amber-950">
      <div className="mx-auto flex max-w-5xl gap-2 px-4 py-2.5 sm:px-6">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <p className="text-sm font-medium">{text}</p>
      </div>
    </div>
  )
}
