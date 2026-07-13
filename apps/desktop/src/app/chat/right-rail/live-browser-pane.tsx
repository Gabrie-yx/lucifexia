import { useEffect, useState } from 'react'

import { fetchBrowserLatest } from '@/lucifex'
import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'

export function LiveBrowserPane() {
  const [dataUrl, setDataUrl] = useState<string | null>(null)
  const [timestamp, setTimestamp] = useState<number>(0)
  const [active, setActive] = useState<boolean>(false)

  useEffect(() => {
    let cancelled = false
    // Track last mtime so we skip re-rendering unchanged screenshots.
    let lastMtime = 0

    const poll = async () => {
      // Skip polling while the browser tab/window is hidden — saves CPU + disk I/O.
      if (document.hidden) return
      try {
        // Pass the current ETag so the server can return 304 (null) if unchanged.
        const etag = lastMtime > 0 ? `"${lastMtime}"` : undefined
        const res = await fetchBrowserLatest(etag)
        if (cancelled) return
        // null = 304 Not Modified — image unchanged, keep current state
        if (res === null) return
        if (res.data_url && res.timestamp !== lastMtime) {
          lastMtime = res.timestamp
          setDataUrl(res.data_url)
          setTimestamp(res.timestamp)
        }
        // Active = screenshot taken within the last 30 seconds
        const diff = Date.now() / 1000 - (res.timestamp || 0)
        setActive(!!res.data_url && diff < 30)
      } catch (err) {
        console.error('Failed to poll latest browser screenshot:', err)
      }
    }

    // Initial poll
    void poll()

    // Poll every 1.2 s. Slightly offset from 1000ms to stagger with other timers.
    const timer = setInterval(() => { void poll() }, 1200)

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-(--ui-editor-surface-background)">
      {/* Pane Header */}
      <div className="flex h-9 shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-3 bg-(--ui-sidebar-surface-background)">
        <span className="text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <span className={cn("size-2 rounded-full", active ? "bg-emerald-500 animate-pulse" : "bg-muted-foreground/30")} />
          {active ? 'Navegador Ativo' : 'Navegador Inativo'}
        </span>
        {timestamp > 0 && (
          <span className="text-[0.6rem] text-muted-foreground/60 font-mono">
            Atualizado: {new Date(timestamp * 1000).toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Pane Body / Screenshot Viewer */}
      <div className="min-h-0 flex-1 overflow-auto p-4 flex flex-col items-center justify-center relative">
        {dataUrl ? (
          <div className="relative border border-(--ui-stroke-secondary) rounded-md overflow-hidden bg-zinc-950/40 shadow-lg max-w-full max-h-full flex items-center justify-center">
            <img
              alt="Browser View"
              className="max-h-full max-w-full object-contain pointer-events-none select-none transition-opacity duration-300"
              src={dataUrl}
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center p-8 text-center max-w-md animate-fade-in">
            <div className="grid size-12 place-items-center rounded-full bg-primary/5 text-primary border border-primary/10 shadow-[0_0_15px_rgba(var(--primary-rgb),0.05)]">
              <Codicon name="browser" size="1.25rem" />
            </div>
            <h3 className="mt-4 text-xs font-semibold text-foreground/80">Navegador em Standby</h3>
            <p className="mt-2 text-[0.7rem] leading-normal text-muted-foreground/60">
              O feed ao vivo iniciará automaticamente quando o agente abrir uma página ou navegar pela web.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
