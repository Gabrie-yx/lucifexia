import { useEffect } from 'react'

/**
 * Backdrop — aplica o radius-scalar da identidade visual Lucifexia.
 * A imagem de fundo de estátua foi removida para manter a identidade limpa.
 */
export function Backdrop() {
  useEffect(() => {
    // Radius original do Lucifexia: 1.5 (bordas bem arredondadas)
    document.documentElement.style.setProperty('--radius-scalar', '1.5')
  }, [])

  return null
}
