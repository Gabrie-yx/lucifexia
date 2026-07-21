import { useQuery } from '@tanstack/react-query'

import { getLucifexConfigRecord } from '@/lucifex'
import { queryClient, writeCache } from '@/lib/query-client'
import type { LucifexConfigRecord } from '@/types/lucifex'

// One shared cache for the whole profile config record (`GET /api/config`).
// Every settings surface (MCP, model, config) reads and writes through this key
// so a save in one shows in the others, and revisiting a tab paints the cache
// instead of blanking on a fresh fetch.
//
// Distinct from session/hooks/use-lucifex-config.ts, which is side-effecting —
// it pushes personality/cwd/voice/… into the session stores for live chat.
export const LUCIFEX_CONFIG_KEY = ['lucifex-config-record'] as const

// staleTime 0 → serve cache instantly, background-revalidate on every mount.
export const useLucifexConfigRecord = () =>
  useQuery({ queryKey: LUCIFEX_CONFIG_KEY, queryFn: getLucifexConfigRecord, staleTime: 0 })

export const setLucifexConfigCache = writeCache<LucifexConfigRecord>(LUCIFEX_CONFIG_KEY)

export const invalidateLucifexConfig = () => queryClient.invalidateQueries({ queryKey: LUCIFEX_CONFIG_KEY })
