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

      // 1. Live Browser stream auto-open & tab activation on browser tools start
      if (event.type === 'tool.start') {
        const toolName = typeof payload.name === 'string' ? payload.name : ''
        if (toolName.startsWith('browser_') || toolName === 'web_extract_stealth' || toolName === 'web_scrape_structured') {
          setPaneOpen('preview', true)
          selectRightRailTab(RIGHT_RAIL_BROWSER_TAB_ID)
        }
      }

      // 2. Auto-Preview files (HTML, SVG, MD, images) on tool completion
      if (event.type === 'tool.complete') {
        const filePath = typeof payload.path === 'string' ? payload.path : (typeof payload.TargetFile === 'string' ? payload.TargetFile : '')
        if (filePath) {
          const lower = filePath.toLowerCase()
          const isPreviewable = lower.endsWith('.html') || lower.endsWith('.svg') || lower.endsWith('.md') || lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.webp')
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
