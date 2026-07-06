import { useStore } from '@nanostores/react'
import { useEffect, useRef, useState } from 'react'

import { cn } from '@/lib/utils'
import { $desktopBoot } from '@/store/boot'
import { $gatewayState } from '@/store/session'

type Phase = 'live' | 'text-out' | 'overlay-out' | 'gone'

const PREVIEW_CONNECT_MS = 2600
const PREVIEW_REPLAY_MS = 1100
const TEXT_OUT_MS = 360
const POST_TEXT_HOLD_MS = 300
const OVERLAY_OUT_MS = 520

function forcedPreview(): boolean {
  if (!import.meta.env.DEV || typeof window === 'undefined') return false
  try {
    return new URLSearchParams(window.location.search).get('connecting') === '1'
  } catch {
    return false
  }
}

export function GatewayConnectingOverlay() {
  const gatewayState = useStore($gatewayState)
  const boot = useStore($desktopBoot)
  const [previewing] = useState(forcedPreview)
  const [phase, setPhase] = useState<Phase>('live')
  const shownRef = useRef(false)

  const initialBootActive = boot.visible || boot.running || boot.progress < 100
  const connecting = gatewayState !== 'open' && !boot.error && initialBootActive

  if (previewing || connecting) {
    shownRef.current = true
  }

  useEffect(() => {
    if (phase !== 'live') return

    if (previewing) {
      const id = window.setTimeout(() => setPhase('text-out'), PREVIEW_CONNECT_MS)
      return () => window.clearTimeout(id)
    }

    if (gatewayState === 'open' && shownRef.current) {
      setPhase('text-out')
    }
  }, [phase, previewing, gatewayState])

  useEffect(() => {
    if (phase === 'text-out') {
      const id = window.setTimeout(() => setPhase('overlay-out'), TEXT_OUT_MS + POST_TEXT_HOLD_MS)
      return () => window.clearTimeout(id)
    }
    if (phase === 'overlay-out') {
      const id = window.setTimeout(() => setPhase('gone'), OVERLAY_OUT_MS)
      return () => window.clearTimeout(id)
    }
    if (phase === 'gone' && previewing) {
      const id = window.setTimeout(() => setPhase('live'), PREVIEW_REPLAY_MS)
      return () => window.clearTimeout(id)
    }
  }, [phase, previewing])

  if (boot.error && !previewing) return null
  if (phase === 'gone' && !previewing) return null
  if (!previewing && !connecting && !shownRef.current) return null

  const leaving = phase !== 'live'
  const overlayHidden = phase === 'overlay-out' || phase === 'gone'

  return (
    <div
      className={cn(
        'fixed inset-0 z-[1200] flex flex-col items-center justify-center transition-opacity duration-500 ease-out',
        overlayHidden ? 'pointer-events-none opacity-0' : 'opacity-100'
      )}
      style={{ background: '#000' }}
    >
      <div
        className={cn(
          'flex flex-col items-center transition duration-500 ease-out',
          leaving ? 'translate-y-4 opacity-0' : 'translate-y-0 opacity-100'
        )}
      >
        <h1
          className="lucifexia-wordmark-loading select-none"
          style={{
            fontFamily: "'Collapse', 'Arial Black', sans-serif",
            fontWeight: 700,
            fontSize: 'clamp(3rem, 10vw, 7rem)',
            letterSpacing: '0.15em',
            lineHeight: 1,
            background: 'linear-gradient(90deg, #ffffff 0%, #ff2222 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            animation: 'lucifex-pulse 2s ease-in-out infinite alternate',
          }}
        >
          LUCIFEXIA
        </h1>
        <style>{`
          @keyframes lucifex-pulse {
            0%   { background-position: 0% 50%;   opacity: 0.85; }
            100% { background-position: 100% 50%; opacity: 1; }
          }
          .lucifexia-wordmark-loading {
            background-size: 200% auto;
            animation: lucifex-pulse 2s ease-in-out infinite alternate;
          }
        `}</style>
      </div>
    </div>
  )
}
