const APP_VERSION = __LODEX_APP_VERSION__
const BUILD_VERSION = __LODEX_BUILD_VERSION__
const STORAGE_KEY = 'lodex-build-version'
const VERSION_PARAM = 'v'

function versionedUrl(build = BUILD_VERSION) {
  const url = new URL(window.location.href)
  url.searchParams.set(VERSION_PARAM, build)
  return url
}

async function clearBrowserCaches() {
  if ('caches' in window) {
    const names = await caches.keys()
    await Promise.all(names.map(name => caches.delete(name)))
  }
  if ('serviceWorker' in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations()
    await Promise.all(registrations.map(registration => registration.update().catch(() => undefined)))
  }
}

function rememberBuild(build) {
  try { localStorage.setItem(STORAGE_KEY, build) } catch {}
}

function rememberedBuild() {
  try { return localStorage.getItem(STORAGE_KEY) || '' } catch { return '' }
}

function stampCurrentUrl(build = BUILD_VERSION) {
  const current = new URL(window.location.href)
  if (current.searchParams.get(VERSION_PARAM) === build) return
  current.searchParams.set(VERSION_PARAM, build)
  window.history.replaceState(window.history.state, '', current)
}

async function recoverFromMismatch(nextBuild) {
  rememberBuild(nextBuild)
  await clearBrowserCaches()
  window.location.replace(versionedUrl(nextBuild))
}

export async function installBuildVersionGuard() {
  const previousBuild = rememberedBuild()
  if (previousBuild && previousBuild !== BUILD_VERSION) {
    await recoverFromMismatch(BUILD_VERSION)
    return
  }

  rememberBuild(BUILD_VERSION)
  stampCurrentUrl(BUILD_VERSION)

  // version.json is emitted on every Vite build and explicitly bypasses the
  // service-worker navigation fallback. A newer server build can therefore
  // evict stale PWA caches even when an older tab has remained open.
  try {
    const response = await fetch(`/version.json?t=${Date.now()}`, {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    })
    if (!response.ok) return
    const server = await response.json()
    if (server?.build && server.build !== BUILD_VERSION) {
      await recoverFromMismatch(server.build)
    }
  } catch {
    // Being offline must not stop LODEX from opening as an installed PWA.
  }
}

export { APP_VERSION, BUILD_VERSION }
