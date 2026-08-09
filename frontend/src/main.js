import { createApp } from 'vue'
import App from './App.vue'
import InstallLodex from './components/InstallLodex.vue'
import packageMetadata from '../package.json'
import { enhanceFooter } from './footer.js'
import { enhanceLodexHero } from './hero-refresh.js'
import './shadcn.css'
import './style.css'
import './virtual.css'
import './footer.css'
import './hero-refresh.css'

createApp(App).mount('#app')
enhanceFooter({ version: packageMetadata.version })
enhanceLodexHero()

const installRoot = document.querySelector('#pwa-install')
if (installRoot) createApp(InstallLodex).mount(installRoot)
