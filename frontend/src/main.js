import { createApp } from 'vue'
import App from './App.vue'
import InstallLodex from './components/InstallLodex.vue'
import { installLodexEnhancements } from './enhancements.js'
import './shadcn.css'
import './style.css'
import './virtual.css'
import './enhancements.css'
import './admin.css'

createApp(App).mount('#app')
installLodexEnhancements()

const installRoot = document.querySelector('#pwa-install')
if (installRoot) createApp(InstallLodex).mount(installRoot)
