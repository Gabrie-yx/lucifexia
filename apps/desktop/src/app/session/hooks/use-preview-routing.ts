import { useStore } from '@nanostores/react'
import { type MutableRefObject, useCallback, useEffect } from 'react'

import { gatewayEventCompletedFileDiff } from '@/lib/gateway-events'
import {
  $previewTarget,
  $sessionPreviewRegistry,
  beginPreviewServerRestart,
  completePreviewServerRestart,
  getSessionPreviewRecord,
  progressPreviewServerRestart,
  requestPreviewReload,
  setPreviewTarget
} from '@/store/preview'
import { $currentCwd } from '@/store/session'
import type { RpcEvent } from '@/types/lucifex'
import { setPaneOpen } from '@/store/panes'
import { selectRightRailTab, RIGHT_RAIL_BROWSER_TAB_ID, RIGHT_RAIL_PREVIEW_TAB_ID } from '@/store/layout'
import { normalizeOrLocalPreviewTarget } from '@/lib/local-preview'

type EventHandler = (event: RpcEvent) => void

// -----------------------------------------------------------------------
// Dev-server URL detection patterns for Node.js and other ecosystems.
// Scans terminal output and returns the first local URL found.
// Covers: Vite, CRA, Next.js, Nuxt, Astro, SvelteKit, Express/Koa/Fastify,
//         Deno, Bun serve, Django, FastAPI/uvicorn, Flask.
// -----------------------------------------------------------------------
const DEV_SERVER_PATTERNS: RegExp[] = [
  // Vite: "Local: http://localhost:5173/"
  /Local:\s+(https?:\/\/localhost:\d+\S*)/i,
  // Vite alt: "➜  Local:   http://localhost:5173/"
  /\u279c\s+Local:\s+(https?:\/\/localhost:\d+\S*)/i,
  // CRA / webpack: "Local:            http://localhost:3000"
  /(?:Local|On Your Network):\s+(https?:\/\/localhost:\d+\S*)/i,
  // Next.js: "ready - started server on 0.0.0.0:3000, url: http://localhost:3000"
  /url:\s+(https?:\/\/localhost:\d+\S*)/i,
  // Next.js newer: "▲ Next.js ... Local: http://localhost:3000"
  /Next\.js[^\n]*?Local:\s+(https?:\/\/localhost:\d+)/i,
  // Nuxt/Astro: "Local:    http://localhost:3000/"
  // SvelteKit: "Local: http://localhost:5173"
  // Generic: anything that says "http://localhost:PORT"
  /(?:listening|running|available|serving|started)[\s\S]{0,80}(https?:\/\/(?:localhost|127\.0\.0\.1):\d+)/i,
  // Fallback: bare "http://localhost:PORT" in output
  /(https?:\/\/(?:localhost|127\.0\.0\.1):\d{2,5}(?:\/\S*)?)/,
]

function extractDevServerUrl(terminalOutput: string): string | null {
  for (const pattern of DEV_SERVER_PATTERNS) {
    const m = pattern.exec(terminalOutput)
    if (m?.[1]) {
      // Strip trailing punctuation / ANSI artifacts
      return m[1].replace(/[\x1B]\[[0-9;]*m/g, '').replace(/[,;\s]+$/, '')
    }
  }
  return null
}

interface PreviewRoutingOptions {
  activeSessionIdRef: MutableRefObject<string | null>
  baseHandleGatewayEvent: EventHandler
  currentCwd: string
  currentView: string
  requestGateway: <T = unknown>(method: string, params?: Record<string, unknown>) => Promise<T>
  routedSessionId: string | null
  selectedStoredSessionId: string | null
}

function asRecord(payload: unknown): Record<string, unknown> {
  return payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : {}
}

function activePreviewSessionId(
  activeSessionIdRef: MutableRefObject<string | null>,
  routedSessionId: string | null,
  selectedStoredSessionId: string | null
): string {
  return selectedStoredSessionId || routedSessionId || activeSessionIdRef.current || ''
}

export function usePreviewRouting({
  activeSessionIdRef,
  baseHandleGatewayEvent,
  currentCwd,
  currentView,
  requestGateway,
  routedSessionId,
  selectedStoredSessionId
}: PreviewRoutingOptions) {
  const previewRegistry = useStore($sessionPreviewRegistry)
  const previewSessionId = activePreviewSessionId(activeSessionIdRef, routedSessionId, selectedStoredSessionId)

  // Restore a *user-opened* preview when its session becomes active. Tool
  // results no longer auto-register/open a preview — the inline preview card in
  // the tool row is the only entry point, so HTML artifacts never pop the rail
  // open on their own.
  useEffect(() => {
    if (currentView !== 'chat' || !previewSessionId) {
      setPreviewTarget(null)

      return
    }

    const record = getSessionPreviewRecord(previewSessionId)

    setPreviewTarget(record?.normalized ?? null)
  }, [currentView, previewRegistry, previewSessionId])

  const restartPreviewServer = useCallback(
    async (url: string, context?: string) => {
      const sessionId = activeSessionIdRef.current

      if (!sessionId) {
        throw new Error('No active session for background restart')
      }

      const cwd = $currentCwd.get() || currentCwd || ''

      const result = await requestGateway<{ task_id?: string }>('preview.restart', {
        context: context || undefined,
        cwd: cwd || undefined,
        session_id: sessionId,
        url
      })

      const taskId = result.task_id || ''

      if (!taskId) {
        throw new Error('Background restart did not return a task id')
      }

      beginPreviewServerRestart(taskId, url)

      return taskId
    },
    [activeSessionIdRef, currentCwd, requestGateway]
  )

  const handleDesktopGatewayEvent = useCallback<EventHandler>(
    event => {
      baseHandleGatewayEvent(event)

      if (event.type === 'preview.restart.complete') {
        const { task_id, text } = asRecord(event.payload)

        if (typeof task_id === 'string' && task_id) {
          completePreviewServerRestart(task_id, typeof text === 'string' ? text : '')
        }
      } else if (event.type === 'preview.restart.progress') {
        const { task_id, text } = asRecord(event.payload)

        if (typeof task_id === 'string' && task_id) {
          progressPreviewServerRestart(task_id, typeof text === 'string' ? text : '')
        }
      }

      if (event.session_id && event.session_id !== activeSessionIdRef.current) {
        return
      }

      const payload = asRecord(event.payload)

      // 1. Live Browser stream auto-open & tab activation on browser tool start
      if (event.type === 'tool.start') {
        const toolName = typeof payload.name === 'string' ? payload.name : ''
        if (toolName.startsWith('browser_') || toolName === 'web_extract_stealth' || toolName === 'web_scrape_structured') {
          setPaneOpen('preview', true)
          selectRightRailTab(RIGHT_RAIL_BROWSER_TAB_ID)
        }
      }

      // 2. Auto-Preview files (HTML, SVG, MD, images) on tool completion.
      //    The path lives inside payload.args (tool.complete payload shape:
      //    { tool_id, name, args: { TargetFile|path, ... }, result, summary }).
      //    Reading it from the top-level payload is always undefined — Bug #2 fix.
      if (event.type === 'tool.complete') {
        const args = asRecord(payload.args)
        const toolName = typeof payload.name === 'string' ? payload.name : ''

        // Explicit open_preview tool handler
        if (toolName === 'open_preview') {
          const pathOrUrl = typeof args.path_or_url === 'string' ? args.path_or_url : ''
          if (pathOrUrl) {
            const cwd = $currentCwd.get() || currentCwd || ''
            normalizeOrLocalPreviewTarget(pathOrUrl, cwd).then(target => {
              if (target) {
                setPreviewTarget(target)
                setPaneOpen('preview', true)
                selectRightRailTab(RIGHT_RAIL_PREVIEW_TAB_ID)
              }
            }).catch(err => {
              console.error('Failed to open preview:', err)
            })
          }
        }

        const filePath =
          typeof args.TargetFile === 'string' ? args.TargetFile
          : typeof args.path === 'string' ? args.path
          : typeof args.file_path === 'string' ? args.file_path
          : ''

        if (filePath) {
          const lower = filePath.toLowerCase()
          const isPreviewable =
            lower.endsWith('.html') || lower.endsWith('.htm') ||
            lower.endsWith('.svg') || lower.endsWith('.md') ||
            lower.endsWith('.png') || lower.endsWith('.jpg') ||
            lower.endsWith('.jpeg') || lower.endsWith('.webp') ||
            lower.endsWith('.gif')
          if (isPreviewable) {
            const cwd = $currentCwd.get() || currentCwd || ''
            normalizeOrLocalPreviewTarget(filePath, cwd).then(target => {
              if (target) {
                setPreviewTarget(target)
                setPaneOpen('preview', true)
                selectRightRailTab(RIGHT_RAIL_PREVIEW_TAB_ID)
              }
            }).catch(err => {
              console.error('Failed to auto-preview file:', err)
            })
          }
        }

        // 3. Node.js / universal dev-server auto-detection.
        //    When the agent runs npm/pnpm/deno/bun/python dev commands, the
        //    terminal output includes a "Local: http://localhost:PORT" line.
        //    Detect it and route the preview automatically — no manual copy-paste.
        if (typeof payload.name === 'string' && payload.name === 'terminal') {
          const result = asRecord(payload.result)
          const termOut = typeof result.output === 'string' ? result.output : ''
          if (termOut) {
            const devUrl = extractDevServerUrl(termOut)
            if (devUrl) {
              normalizeOrLocalPreviewTarget(devUrl, $currentCwd.get() || currentCwd || '').then(target => {
                if (target) {
                  setPreviewTarget(target)
                  setPaneOpen('preview', true)
                  selectRightRailTab(RIGHT_RAIL_PREVIEW_TAB_ID)
                }
              }).catch(() => {
                // non-fatal — preview is best-effort
              })
            }
          }
        }
      }

      // Only refresh an already-open live preview when a file changes; never
      // open one unprompted. (Preview links are surfaced from the tool row into
      // the status stack — see tool-fallback.tsx.)
      if ($previewTarget.get()?.kind === 'url' && gatewayEventCompletedFileDiff(event)) {
        requestPreviewReload()
      }
    },
    [activeSessionIdRef, baseHandleGatewayEvent, currentCwd]
  )

  return { handleDesktopGatewayEvent, restartPreviewServer }
}
