<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Button } from '@/components/ui/button'

const visible = ref(false)
const instructionsOpen = ref(false)
const installPrompt = ref(null)

const dismissKey = 'lodex-install-dismissed-at'
const dismissForMs = 7 * 24 * 60 * 60 * 1000

function isStandalone() {
  return window.matchMedia?.('(display-mode: standalone)').matches || window.navigator.standalone === true
}

function isIOS() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

function recentlyDismissed() {
  const value = Number(localStorage.getItem(dismissKey) || 0)
  return value > 0 && Date.now() - value < dismissForMs
}

function handleBeforeInstallPrompt(event) {
  event.preventDefault()
  installPrompt.value = event
  if (!recentlyDismissed()) visible.value = true
}

function handleInstalled() {
  visible.value = false
  instructionsOpen.value = false
  installPrompt.value = null
  localStorage.removeItem(dismissKey)
}

async function install() {
  if (installPrompt.value) {
    await installPrompt.value.prompt()
    const choice = await installPrompt.value.userChoice
    if (choice?.outcome === 'accepted') handleInstalled()
    installPrompt.value = null
    return
  }

  instructionsOpen.value = true
}

function dismiss() {
  localStorage.setItem(dismissKey, String(Date.now()))
  visible.value = false
  instructionsOpen.value = false
}

onMounted(() => {
  if (isStandalone()) return

  window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
  window.addEventListener('appinstalled', handleInstalled)

  if (isIOS() && !recentlyDismissed()) {
    window.setTimeout(() => {
      if (!isStandalone()) visible.value = true
    }, 8000)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
  window.removeEventListener('appinstalled', handleInstalled)
})
</script>

<template>
  <aside
    v-if="visible"
    class="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] left-[max(1rem,env(safe-area-inset-left))] z-[100] w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-border bg-card/95 p-4 text-card-foreground shadow-2xl backdrop-blur"
    aria-label="Install LODEX"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="text-sm font-semibold">Keep LODEX on your phone</p>
        <p class="mt-1 text-sm leading-5 text-muted-foreground">
          Install it like an app for faster project access and upcoming customer notifications.
        </p>
      </div>
      <Button variant="ghost" size="icon" class="-mr-2 -mt-2 shrink-0" aria-label="Dismiss install suggestion" @click="dismiss">
        <span aria-hidden="true" class="text-lg leading-none">×</span>
      </Button>
    </div>

    <div v-if="instructionsOpen" class="mt-3 rounded-lg bg-muted px-3 py-2 text-sm leading-5 text-muted-foreground">
      On iPhone: tap <strong class="text-foreground">Share</strong>, then <strong class="text-foreground">Add to Home Screen</strong>, then Add.
    </div>

    <div class="mt-3 flex gap-2">
      <Button class="min-h-11 flex-1" @click="install">
        {{ installPrompt ? 'Install LODEX' : instructionsOpen ? 'Show me again' : 'Add to iPhone' }}
      </Button>
      <Button variant="outline" class="min-h-11" @click="dismiss">Later</Button>
    </div>
  </aside>
</template>
