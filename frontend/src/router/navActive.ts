/**
 * True when a navigation entry leads to the current page or to a page under
 * it ("/abonnements" stays lit on "/abonnements/gerer"); Home ("/") is lit on
 * the home page only.
 */
export function isNavActive(currentPath: string, linkPath: string): boolean {
  if (currentPath === linkPath) return true
  if (linkPath === '/') return false
  return currentPath.startsWith(`${linkPath}/`)
}
