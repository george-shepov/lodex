import { createApp } from 'vue'
import App from './App.vue'
import InstallLodex from './components/InstallLodex.vue'
import { installLodexEnhancements } from './enhancements.js'
import { withInferredIntakeService } from './intakeServiceInference.mjs'
import './shadcn.css'
import './style.css'
import './virtual.css'
import './enhancements.css'
import './admin.css'

function installIntakeServiceInference() {
  const nativeFetch = window.fetch.bind(window)

  window.fetch = (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || ''
    if (!/\/api\/intake\/chat(?:\?|$)/.test(url) || typeof init?.body !== 'string') {
      return nativeFetch(input, init)
    }

    try {
      const payload = JSON.parse(init.body)
      const enrichedPayload = withInferredIntakeService(payload)
      if (enrichedPayload !== payload) {
        init = {
          ...init,
          body: JSON.stringify(enrichedPayload),
        }
      }
    } catch {
      // Preserve the original request if a caller sends non-JSON intake data.
    }

    return nativeFetch(input, init)
  }
}

installIntakeServiceInference()
createApp(App).mount('#app')
installLodexEnhancements()

const installRoot = document.querySelector('#pwa-install')
if (installRoot) createApp(InstallLodex).mount(installRoot)
