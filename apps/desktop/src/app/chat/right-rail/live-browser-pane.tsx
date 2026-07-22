import { useEffect, useRef, useState } from 'react'
import { useStore } from '@nanostores/react'
import {
  IconArrowLeft,
  IconArrowRight,
  IconRefresh,
  IconLock,
  IconExternalLink
} from '@tabler/icons-react'

import { fetchBrowserLatest } from '@/lucifex'
import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'
import { $activeSessionId } from '@/store/session'

export function LiveBrowserPane() {
  const [dataUrl, setDataUrl] = useState<string | null>(null)
  const [timestamp, setTimestamp] = useState<number>(0)
  const [active, setActive] = useState<boolean>(false)
  const [currentUrl, setCurrentUrl] = useState<string>('about:blank')
  const sessionId = useStore($activeSessionId)

  // sessionStartedAt: records the unix seconds when the current session became
  // active. Screenshots with timestamps older than this are stale leftovers from
  // a previous session and are silently discarded even if they pass the ETag check.
  const sessionStartedAtRef = useRef<number>(Date.now() / 1000)
  const prevSessionRef = useRef<string | null | undefined>(undefined)

  // Reset all screenshot state when the active session changes so we never
  // show a stale screenshot from a previous session/project.
  useEffect(() => {
    if (prevSessionRef.current === undefined) {
      // First render — just record the initial session, no reset needed.
      prevSessionRef.current = sessionId
      return
    }
    if (prevSessionRef.current !== sessionId) {
      prevSessionRef.current = sessionId
      // Record the wall-clock time the new session started so we can
      // filter out stale screenshots from the previous session.
      sessionStartedAtRef.current = Date.now() / 1000
      setDataUrl(null)
      setTimestamp(0)
      setActive(false)
      setCurrentUrl('about:blank')
    }
  }, [sessionId])

  useEffect(() => {
    let cancelled = false
    // Reset ETag guard on every new polling lifecycle (incl. session switch).
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
        if (res.data_url && typeof res.timestamp === 'number' && res.timestamp !== lastMtime) {
          // Reject screenshots that predate the current session start.
          // This prevents a leftover latest_browser.png from a previous session
          // from appearing as a valid "current" screenshot when a new session opens.
          if (res.timestamp < sessionStartedAtRef.current) {
            // Stale screenshot from a previous session — silently skip.
            // Update lastMtime so we don't keep re-fetching the same stale file.
            lastMtime = res.timestamp
            return
          }
          lastMtime = res.timestamp
          setDataUrl(res.data_url)
          setTimestamp(res.timestamp)
          if (res.url) {
            setCurrentUrl(res.url)
          }
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
  // Re-run the polling loop when the session changes so lastMtime resets cleanly.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-(--ui-editor-surface-background)">
      {/* Active/Inactive Browser Banner */}
      <div className="flex h-8 shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-3 bg-(--ui-sidebar-surface-background)">
        <span className="text-[0.625rem] font-bold uppercase tracking-wider text-muted-foreground/80 flex items-center gap-1.5">
          <span className={cn("size-2 rounded-full", active ? "bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-muted-foreground/30")} />
          {active ? 'Navegador Ativo' : 'Navegador Ocioso'}
        </span>
        {timestamp > 0 && (
          <span className="text-[0.5625rem] text-muted-foreground/50 font-mono">
            Sincronizado: {new Date(timestamp * 1000).toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Premium Browser Header Mockup */}
      <div className="flex h-11 shrink-0 items-center justify-start gap-2 border-b border-(--ui-stroke-tertiary) px-3 bg-(--ui-sidebar-surface-background)/50 backdrop-blur-sm">
        {/* Navigation Controls */}
        <div className="flex items-center gap-1">
          <button className="p-1 rounded text-muted-foreground/40 hover:bg-(--chrome-action-hover) cursor-not-allowed transition-colors" disabled>
            <IconArrowLeft className="size-3.5" />
          </button>
          <button className="p-1 rounded text-muted-foreground/40 hover:bg-(--chrome-action-hover) cursor-not-allowed transition-colors" disabled>
            <IconArrowRight className="size-3.5" />
          </button>
          <button className="p-1 rounded text-muted-foreground/60 hover:text-foreground hover:bg-(--chrome-action-hover) transition-colors" title="Recarregar captura">
            <IconRefresh className={cn("size-3.5", active && "animate-spin [animation-duration:3s]")} />
          </button>
        </div>

        {/* Address Bar */}
        <div className="flex-1 flex items-center gap-1.5 px-3 py-1 rounded-md bg-zinc-950/20 border border-(--ui-stroke-tertiary) h-7 min-w-0 select-all group">
          <IconLock className="size-3 text-emerald-500 shrink-0" />
          <span className="text-[0.6875rem] text-muted-foreground/80 font-mono truncate select-all flex-1">
            {currentUrl}
          </span>
        </div>

        {/* External Link */}
        <button
          className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-(--chrome-action-hover) transition-colors"
          onClick={() => {
            if (currentUrl && currentUrl !== 'about:blank') {
              void window.lucifexDesktop?.openExternal(currentUrl)
            }
          }}
          title="Abrir no navegador do sistema"
        >
          <IconExternalLink className="size-3.5" />
        </button>
      </div>

      {/* Viewport Area */}
      <div className="min-h-0 flex-1 overflow-y-auto w-full bg-zinc-950/10 relative scrollbar-thin">
        {dataUrl ? (
          <img
            alt="Browser View"
            className="w-full h-auto block select-none pointer-events-none transition-opacity duration-300"
            src={dataUrl}
          />
        ) : (
          <div className="flex flex-col items-center justify-center p-8 absolute inset-0 text-center animate-fade-in">
            <div className="grid size-12 place-items-center rounded-full bg-primary/5 text-primary border border-primary/10 shadow-[0_0_15px_rgba(var(--primary-rgb),0.05)]">
              <Codicon name="browser" size="1.25rem" />
            </div>
            <h3 className="mt-4 text-xs font-semibold text-foreground/80">Navegador em Standby</h3>
            <p className="mt-2 text-[0.7rem] leading-normal text-muted-foreground/60 max-w-xs">
              O feed ao vivo iniciará automaticamente quando o agente abrir uma página ou navegar pela web.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
