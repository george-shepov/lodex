import { createApp } from 'vue'
import App from './App.vue'
import InstallLodex from './components/InstallLodex.vue'
import { installLodexEnhancements } from './enhancements.js'
import { withInferredIntakeService } from './intakeServiceInference.mjs'
import { guardIntakeReply } from './intakeQuestionGuard.mjs'
import './shadcn.css'
import './style.css'
import './virtual.css'
import './enhancements.css'
import './admin.css'

function installIntakeServiceInference() {
  const nativeFetch = window.fetch.bind(window)

  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || ''
    if (!/\/api\/intake\/chat(?:\?|$)/.test(url) || typeof init?.body !== 'string') {
      return nativeFetch(input, init)
    }

    let intakePayload = null
    try {
      const payload = JSON.parse(init.body)
      const enrichedPayload = withInferredIntakeService(payload)
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

installIntakeServiceInference()
createApp(App).mount('#app')
installLodexEnhancements()

const installRoot = document.querySelector('#pwa-install')
if (installRoot) createApp(InstallLodex).mount(installRoot)
