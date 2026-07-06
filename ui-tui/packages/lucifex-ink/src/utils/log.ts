export function logError(error: unknown): void {
  if (!process.env.LUCIFEX_INK_DEBUG_ERRORS) {
    return
  }

  console.error(error)
}
