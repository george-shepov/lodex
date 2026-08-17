<script setup>
import { computed, ref } from 'vue'

const STORAGE_KEY = 'lodex-customer-segment-v1'

const segments = [
  {
    key: 'home',
    title: 'LODEX Home',
    subtitle: 'Home Services',
    eyebrow: 'Homes · rentals · condos',
    description: 'Repairs, renovations, installations, sourcing, cleanup, and ongoing property care.',
    fee: '$150 on-site consultation',
    feeNote: '100% credited to the approved project.',
    icon: '⌂',
  },
  {
    key: 'business',
    title: 'LODEX Business',
    subtitle: 'Business Services',
    eyebrow: 'Stores · offices · hospitality',
    description: 'Punch lists, fixtures, maintenance, installations, procurement, turnovers, and project coordination.',
    fee: '$300 on-site consultation',
    feeNote: '100% credited to the approved project.',
    icon: '▦',
  },
  {
    key: 'enterprise',
    title: 'LODEX Enterprise',
    subtitle: 'Enterprise Services',
    eyebrow: 'Facilities · portfolios · multi-site',
    description: 'Larger facilities, multi-location work, recurring programs, rollout support, and custom scopes.',
    fee: 'Custom assessment',
    feeNote: 'We confirm the assessment fee after reviewing scope and locations.',
    icon: '▥',
  },
]

function readStoredSegment() {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY)
    return segments.some(segment => segment.key === value) ? value : ''
  } catch {
    return ''
  }
}

const selected = ref(readStoredSegment())
const open = ref(!selected.value)
const activeSegment = computed(() => segments.find(segment => segment.key === selected.value) || null)

function chooseSegment(segment) {
  selected.value = segment.key
  try {
    window.localStorage.setItem(STORAGE_KEY, segment.key)
  } catch {
    // Intake still works if browser storage is unavailable.
  }
  window.dispatchEvent(new CustomEvent('lodex:segment-changed', { detail: { segment: segment.key } }))
  open.value = false
  window.setTimeout(() => document.querySelector('#intake')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80)
}
</script>

<template>
  <div v-if="open" class="segment-gateway" role="dialog" aria-modal="true" aria-labelledby="segment-gateway-title">
    <div class="segment-shell">
      <img class="segment-logo" src="/lodex-logo-transparent.png" alt="LODEX Home & Business Services" />
      <p class="segment-kicker">Start here</p>
      <h1 id="segment-gateway-title">What kind of property are we helping with?</h1>
      <p class="segment-intro">
        Choose the LODEX team that fits the job. We will tailor the intake, visit, and consultation fee from there.
      </p>

      <div class="segment-grid">
        <button
          v-for="segment in segments"
          :key="segment.key"
          type="button"
          class="segment-card"
          @click="chooseSegment(segment)"
        >
          <span class="segment-icon" aria-hidden="true">{{ segment.icon }}</span>
          <span class="segment-eyebrow">{{ segment.eyebrow }}</span>
          <strong>{{ segment.title }}</strong>
          <span class="segment-subtitle">{{ segment.subtitle }}</span>
          <span class="segment-description">{{ segment.description }}</span>
          <span class="segment-fee">{{ segment.fee }}</span>
          <span class="segment-fee-note">{{ segment.feeNote }}</span>
          <span class="segment-choose">Choose {{ segment.title.replace('LODEX ', '') }} →</span>
        </button>
      </div>

      <p class="segment-footnote">Not sure? Choose the closest fit. LODEX can move the request to the right team after review.</p>
    </div>
  </div>

  <button v-else-if="activeSegment" type="button" class="segment-switcher" @click="open = true">
    <span>{{ activeSegment.title }}</span>
    <small>Change</small>
  </button>
</template>

<style scoped>
.segment-gateway {
  position: fixed;
  inset: 0;
  z-index: 100000;
  overflow-y: auto;
  padding: clamp(20px, 4vw, 48px);
  background:
    radial-gradient(circle at 50% 0%, rgba(205, 158, 55, 0.2), transparent 34%),
    linear-gradient(145deg, rgba(6, 8, 11, 0.985), rgba(20, 23, 28, 0.985));
  color: #f5f7f8;
}

.segment-shell {
  width: min(1180px, 100%);
  margin: 0 auto;
  text-align: center;
}

.segment-logo {
  width: min(430px, 82vw);
  max-height: 138px;
  object-fit: contain;
  margin: 0 auto 18px;
}

.segment-kicker,
.segment-eyebrow {
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #d9ae4d;
  font-size: 0.76rem;
  font-weight: 800;
}

h1 {
  margin: 6px auto 10px;
  max-width: 820px;
  font-size: clamp(2rem, 4vw, 4rem);
  line-height: 1.02;
  letter-spacing: -0.035em;
}

.segment-intro {
  max-width: 760px;
  margin: 0 auto 30px;
  color: #c8ccd2;
  font-size: clamp(1rem, 1.8vw, 1.18rem);
  line-height: 1.6;
}

.segment-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.segment-card {
  min-height: 430px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 28px 24px 24px;
  border: 1px solid rgba(217, 174, 77, 0.35);
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.025));
  color: inherit;
  text-align: center;
  cursor: pointer;
  box-shadow: 0 22px 55px rgba(0,0,0,0.28);
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}

.segment-card:hover,
.segment-card:focus-visible {
  transform: translateY(-5px);
  border-color: rgba(244, 196, 86, 0.92);
  background: linear-gradient(180deg, rgba(217,174,77,0.13), rgba(255,255,255,0.035));
  outline: none;
}

.segment-icon {
  display: grid;
  place-items: center;
  width: 84px;
  height: 72px;
  margin-bottom: 5px;
  font-size: 3rem;
  line-height: 1;
  color: #e1b64d;
  text-shadow: 0 2px 0 #111, 0 0 18px rgba(225,182,77,0.18);
}

.segment-card strong {
  font-size: 1.65rem;
  letter-spacing: -0.025em;
}

.segment-subtitle {
  color: #eef0f2;
  font-weight: 700;
}

.segment-description {
  color: #bcc2c9;
  line-height: 1.55;
  min-height: 96px;
}

.segment-fee {
  margin-top: auto;
  color: #f3c862;
  font-size: 1.14rem;
  font-weight: 850;
}

.segment-fee-note {
  min-height: 42px;
  color: #aeb5bd;
  font-size: 0.88rem;
  line-height: 1.4;
}

.segment-choose {
  margin-top: 8px;
  width: 100%;
  border-radius: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #d5a93f, #f1ce72);
  color: #15120a;
  font-weight: 900;
}

.segment-footnote {
  margin: 24px 0 0;
  color: #9299a2;
  font-size: 0.9rem;
}

.segment-switcher {
  position: fixed;
  left: 16px;
  bottom: 16px;
  z-index: 9000;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border: 1px solid rgba(217, 174, 77, 0.48);
  border-radius: 999px;
  background: rgba(12, 14, 18, 0.9);
  color: #f4f5f6;
  box-shadow: 0 10px 28px rgba(0,0,0,0.3);
  backdrop-filter: blur(12px);
}

.segment-switcher span { font-weight: 800; }
.segment-switcher small { color: #d9ae4d; }

@media (max-width: 850px) {
  .segment-grid { grid-template-columns: 1fr; }
  .segment-card { min-height: auto; }
  .segment-description, .segment-fee-note { min-height: 0; }
  .segment-gateway { padding: 18px 14px 34px; }
}
</style>
