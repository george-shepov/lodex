<script setup>
import { computed, ref } from 'vue'
import {
  CUSTOMER_SEGMENT_KEY,
  HOME_PROJECT_SIZE_KEY,
  readStoredHomeProjectSize,
  readStoredSegment,
} from '../segmentState.mjs'

const segments = [
  {
    key: 'home',
    title: 'LODEX Home',
    choice: 'My home',
    description: 'Repairs, installations, improvements, renovations, and whole-home projects for homeowners.',
  },
  {
    key: 'business',
    title: 'LODEX Business',
    choice: 'My rental property or business',
    description: 'Landlords, short-term rentals, stores, offices, restaurants, and independently managed properties.',
  },
  {
    key: 'enterprise',
    title: 'LODEX Enterprise',
    choice: 'My company manages properties, facilities, or multiple locations',
    description: 'Property managers, leasing companies, corporate housing, facilities, portfolios, institutional, and public-sector work.',
  },
]

const homeProjectSizes = [
  { key: 'small', label: 'Small repair / installation', note: 'Nearby initial amount starts at $50.' },
  { key: 'several', label: 'Several repairs or improvements', note: 'Nearby diagnostic amount starts at $100.' },
  { key: 'major', label: 'Major renovation / whole-home project', note: 'On-site consultation starts at $150.' },
]

const selected = ref(readStoredSegment())
const selectedHomeSize = ref(readStoredHomeProjectSize())
const stage = ref(selected.value === 'home' && !selectedHomeSize.value ? 'home_size' : 'segment')
const open = ref(!selected.value || (selected.value === 'home' && !selectedHomeSize.value))
const activeSegment = computed(() => segments.find(segment => segment.key === selected.value) || null)

function store(key, value) {
  try { window.localStorage.setItem(key, value) } catch {}
}

function notify() {
  window.dispatchEvent(new CustomEvent('lodex:segment-changed', {
    detail: { segment: selected.value, projectSizeClass: selected.value === 'home' ? selectedHomeSize.value : '' },
  }))
}

function finishSelection() {
  notify()
  open.value = false
  stage.value = 'segment'
  window.setTimeout(() => document.querySelector('#intake')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80)
}

function chooseSegment(segment) {
  selected.value = segment.key
  store(CUSTOMER_SEGMENT_KEY, segment.key)
  if (segment.key === 'home') {
    stage.value = 'home_size'
    return
  }
  selectedHomeSize.value = ''
  try { window.localStorage.removeItem(HOME_PROJECT_SIZE_KEY) } catch {}
  finishSelection()
}

function chooseHomeSize(size) {
  selectedHomeSize.value = size.key
  store(HOME_PROJECT_SIZE_KEY, size.key)
  finishSelection()
}

function changeSelection() {
  stage.value = 'segment'
  open.value = true
}
</script>

<template>
  <div v-if="open" class="segment-gateway" role="dialog" aria-modal="true" aria-labelledby="segment-gateway-title">
    <div class="segment-shell">
      <img class="segment-logo" src="/lodex-logo-home-business.webp" alt="LODEX Home & Business Services" />
      <img class="segment-family" src="/lodex-division-family.svg" alt="LODEX Home, LODEX Business, and LODEX Enterprise service divisions" />

      <template v-if="stage === 'segment'">
        <p class="segment-kicker">Start with the right LODEX team</p>
        <h1 id="segment-gateway-title">What kind of project are you managing?</h1>
        <div class="segment-grid">
          <button v-for="segment in segments" :key="segment.key" type="button" class="segment-card" @click="chooseSegment(segment)">
            <span class="segment-title">{{ segment.title }}</span>
            <strong>{{ segment.choice }}</strong>
            <span class="segment-description">{{ segment.description }}</span>
            <span class="segment-choose">Choose {{ segment.title.replace('LODEX ', '') }} →</span>
          </button>
        </div>
        <p class="segment-footnote">Government and public-sector requests are handled through LODEX Enterprise. You can change this selection at any time.</p>
      </template>

      <template v-else>
        <button type="button" class="segment-back" @click="stage = 'segment'">← Back to customer type</button>
        <p class="segment-kicker">LODEX Home</p>
        <h1 id="segment-gateway-title">What best describes your project?</h1>
        <p class="segment-intro">One early choice sets the base amount. Route distance is calculated separately on the server after we receive the project address.</p>
        <div class="home-size-grid">
          <button v-for="size in homeProjectSizes" :key="size.key" type="button" class="home-size-card" @click="chooseHomeSize(size)">
            <strong>{{ size.label }}</strong>
            <span>{{ size.note }}</span>
            <small>Continue →</small>
          </button>
        </div>
      </template>
    </div>
  </div>

  <button v-else-if="activeSegment" type="button" class="segment-switcher" @click="changeSelection">
    <span>{{ activeSegment.title }}<template v-if="selectedHomeSize"> · {{ selectedHomeSize }}</template></span>
    <small>Change</small>
  </button>
</template>

<style scoped>
.segment-gateway{position:fixed;inset:0;z-index:100000;overflow-y:auto;padding:clamp(18px,3vw,38px);background:radial-gradient(circle at 50% 0%,rgba(205,158,55,.2),transparent 34%),linear-gradient(145deg,rgba(6,8,11,.99),rgba(20,23,28,.99));color:#f5f7f8}.segment-shell{width:min(1120px,100%);margin:0 auto;text-align:center}.segment-logo{display:block;width:min(360px,72vw);max-height:116px;object-fit:contain;margin:0 auto 12px}.segment-family{display:block;width:min(880px,100%);max-height:190px;object-fit:contain;margin:0 auto 14px;border-radius:14px}.segment-kicker{margin:10px 0 5px;color:#e2b852;font-size:.73rem;font-weight:850;letter-spacing:.16em;text-transform:uppercase}h1{max-width:850px;margin:5px auto 24px;font-size:clamp(2rem,4vw,3.8rem);line-height:1.02;letter-spacing:-.04em}.segment-intro{max-width:720px;margin:-12px auto 26px;color:#c8ccd2;line-height:1.6}.segment-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.segment-card,.home-size-card{display:flex;flex-direction:column;align-items:flex-start;gap:12px;border:1px solid rgba(217,174,77,.38);border-radius:20px;background:linear-gradient(180deg,rgba(255,255,255,.075),rgba(255,255,255,.025));color:inherit;text-align:left;cursor:pointer;box-shadow:0 22px 55px rgba(0,0,0,.28);transition:transform 160ms ease,border-color 160ms ease,background 160ms ease}.segment-card{min-height:285px;padding:26px 24px 22px}.segment-card:hover,.segment-card:focus-visible,.home-size-card:hover,.home-size-card:focus-visible{transform:translateY(-4px);border-color:rgba(244,196,86,.95);background:linear-gradient(180deg,rgba(217,174,77,.14),rgba(255,255,255,.04));outline:none}.segment-title{color:#e2b852;font-size:.75rem;font-weight:850;letter-spacing:.12em;text-transform:uppercase}.segment-card strong{font-size:clamp(1.25rem,2vw,1.65rem);line-height:1.15}.segment-description{color:#c2c7cd;line-height:1.55}.segment-choose{width:100%;margin-top:auto;padding-top:15px;border-top:1px solid rgba(255,255,255,.13);color:#f2c965;font-weight:850}.segment-footnote{margin:20px 0 0;color:#969da5;font-size:.88rem}.segment-back{display:block;margin:0 auto 16px;border:0;background:none;color:#d7dde1;font-weight:750;cursor:pointer}.home-size-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.home-size-card{min-height:190px;padding:26px}.home-size-card strong{font-size:1.35rem;line-height:1.25}.home-size-card span{color:#bdc4ca;line-height:1.5}.home-size-card small{margin-top:auto;color:#edc663;font-weight:850}.segment-switcher{position:fixed;left:16px;bottom:16px;z-index:9000;display:flex;align-items:center;gap:10px;padding:9px 12px;border:1px solid rgba(217,174,77,.48);border-radius:999px;background:rgba(12,14,18,.92);color:#f4f5f6;box-shadow:0 10px 28px rgba(0,0,0,.3);backdrop-filter:blur(12px);cursor:pointer}.segment-switcher span{font-weight:800}.segment-switcher small{color:#e4bd61}
@media(max-width:760px){.segment-gateway{padding:14px}.segment-logo{width:min(280px,74vw)}.segment-family{max-height:130px;margin-bottom:8px}h1{margin-bottom:18px}.segment-grid,.home-size-grid{grid-template-columns:1fr}.segment-card{min-height:0;padding:20px}.home-size-card{min-height:150px;padding:20px}.segment-switcher{right:12px;left:12px;justify-content:center}.segment-description{font-size:.94rem}}
</style>
