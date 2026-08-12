import { createApp } from 'vue'
import App from './App.vue'
import InstallLodex from './components/InstallLodex.vue'
import { installLodexEnhancements } from './enhancements.js'
import './shadcn.css'
import './style.css'
import './virtual.css'
import './enhancements.css'
import './admin.css'

function inferIntakeServiceCategory(payload) {
  if (String(payload?.service_category || '').trim()) return ''

  const userTurns = Array.isArray(payload?.conversation)
    ? payload.conversation
        .filter(turn => turn?.role === 'user')
        .map(turn => turn?.text || '')
        .join(' ')
    : ''
  const text = [payload?.message, payload?.project_summary, userTurns]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()

  const repairCue = /\b(?:repair(?:s|ed|ing)?|broken|loose|handyman|maintenance|leak(?:s|ed|ing)?|stuck|jammed)\b|\bfix(?:\s*it|es|ed|ing)?\b/i
  if (repairCue.test(text)) return 'Handyman & Property Maintenance'

  return ''
}

function installIntakeServiceInference() {
  const nativeFetch = window.fetch.bind(window)

  window.fetch = (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || ''
    if (!/\/api\/intake\/chat(?:\?|$)/.test(url) || typeof init?.body !== 'string') {
      return nativeFetch(input, init)
    }

    try {
      const payload = JSON.parse(init.body)
      const inferredService = inferIntakeServiceCategory(payload)
      if (inferredService) {
        init = {
          ...init,
          body: JSON.stringify({ ...payload, service_category: inferredService }),
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
