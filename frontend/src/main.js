import { createApp } from 'vue'
import App from './App.vue'
import InstallLodex from './components/InstallLodex.vue'
import SegmentGateway from './components/SegmentGateway.vue'
import { installBuildVersionGuard } from './buildVersion.js'
import { installLodexEnhancements } from './enhancements.js'
import { withInferredIntakeService } from './intakeServiceInference.mjs'
import { guardIntakeReply } from './intakeQuestionGuard.mjs'
import { installChatReplyFocus } from './chatReplyFocus.mjs'
import { createUploadAccumulator } from './uploadAccumulator.mjs'
import { lzGalleryProjects } from './lzGallery'
import { applyGalleryCuration } from './galleryCuration.mjs'
import { withCustomerSegment } from './segmentState.mjs'
import './shadcn.css'
import './style.css'
import './virtual.css'
import './enhancements.css'
import './admin.css'

function installVirtualRoomAlertGuard() {
  const NativeWebSocket = window.WebSocket
  if (!NativeWebSocket) return

  window.WebSocket = class LodexWebSocket extends NativeWebSocket {
    constructor(url, protocols) {
      const value = String(url || '')
      const match = value.match(/\/api\/virtual\/rooms\/([^/?#]+)/i)
      if (match && window.location.pathname !== '/admin') {
        const roomCode = decodeURIComponent(match[1]).trim().toUpperCase()
        if (roomCode) {
          fetch('/api/support/virtual-room', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_code: roomCode }),
            keepalive: true,
          }).catch(() => {})
        }
      }
      super(url, protocols)
    }
  }
}

function installLodexRequestGuards() {
  const nativeFetch = window.fetch.bind(window)
  const uploadAccumulator = createUploadAccumulator(window.sessionStorage)

  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || ''

    if (/\/api\/intake\/upload(?:\?|$)/.test(url)) {
      const response = await nativeFetch(input, init)
      if (response.ok) {
        try {
          const data = await response.clone().json()
          const description = init?.body instanceof FormData ? init.body.get('description') || '' : ''
          uploadAccumulator.remember({ ...data, description })
        } catch {
          // The upload itself succeeded; tracking failure must not break intake.
        }
      }
      return response
    }

    if (/\/api\/appointments\/request(?:\?|$)/.test(url) && typeof init?.body === 'string') {
      let tracked = false
      try {
        const payload = JSON.parse(init.body)
        const enriched = withCustomerSegment(uploadAccumulator.enrich(payload))
        init = { ...init, body: JSON.stringify(enriched) }
        tracked = true
      } catch {
        // Preserve the original appointment request if it is not JSON.
      }
      const response = await nativeFetch(input, init)
      if (tracked && response.ok) uploadAccumulator.clear()
      return response
    }

    if (/\/api\/payments\/checkout(?:\?|$)/.test(url) && typeof init?.body === 'string') {
      try {
        const payload = JSON.parse(init.body)
        init = { ...init, body: JSON.stringify(withCustomerSegment(payload)) }
      } catch {
        // Preserve the original checkout request if it is not JSON.
      }
      return nativeFetch(input, init)
    }

    if (!/\/api\/intake\/chat(?:\?|$)/.test(url) || typeof init?.body !== 'string') {
      return nativeFetch(input, init)
    }

    let intakePayload = null
    try {
      const payload = JSON.parse(init.body)
      const inferredPayload = withInferredIntakeService(payload)
      const enrichedPayload = withCustomerSegment(inferredPayload)
      intakePayload = enrichedPayload
      if (enrichedPayload !== payload) {
        init = {
          ...init,
          body: JSON.stringify(enrichedPayload),
        }
      }
    } catch {
      // Preserve the original request if a caller sends non-JSON intake data.
    }

    const response = await nativeFetch(input, init)
    if (!intakePayload || !response.ok) return response

    try {
      const responsePayload = await response.clone().json()
      const guardedPayload = guardIntakeReply(intakePayload, responsePayload)
      if (guardedPayload === responsePayload) return response

      const headers = new Headers(response.headers)
      headers.delete('content-length')
      headers.delete('content-encoding')
      headers.set('content-type', 'application/json')
      return new Response(JSON.stringify(guardedPayload), {
        status: response.status,
        statusText: response.statusText,
        headers,
      })
    } catch {
      return response
    }
  }
}

// Stamp the current page with the build id and self-heal stale PWA/browser
// caches when production moves to a newer build.
installBuildVersionGuard()

applyGalleryCuration(lzGalleryProjects)
installLodexRequestGuards()
installVirtualRoomAlertGuard()
createApp(App).mount('#app')
installLodexEnhancements()
installChatReplyFocus()

const segmentRoot = document.createElement('div')
segmentRoot.id = 'lodex-segment-gateway'
document.body.appendChild(segmentRoot)
createApp(SegmentGateway).mount(segmentRoot)

const installRoot = document.querySelector('#pwa-install')
if (installRoot) createApp(InstallLodex).mount(installRoot)
