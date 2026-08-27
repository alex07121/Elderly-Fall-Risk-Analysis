<script setup lang="ts">
import { apiGet } from './useFallRiskApi'

const summary = ref<any>(null)
const error = ref('')
const loading = ref(true)
const containsCjk = (value: unknown) => /[\u3400-\u9fff]/u.test(String(value ?? ''))

function englishError(value: unknown): string {
  const text = String(value ?? '').trim()

  return text && !containsCjk(text) ? text : 'Unable to load the summary. Check the backend connection and try again.'
}

async function load() {
  loading.value = true
  try {
    summary.value = await apiGet<any>('/assessments/summary')
    error.value = ''
  }
  catch (e: any) {
    error.value = englishError(e?.message || String(e))
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

const refreshKey = inject<Ref<number>>('refreshKey', ref(0))
watch(refreshKey, load)

const riskFocus = inject<Ref<string>>('riskFocus', ref(''))

const cards = computed(() => [
  {
    label: 'Residents monitored',
    labelEn: 'All recorded assessments',
    value: summary.value?.total ?? 0,
    percent: null,
    filter: '',
    color: 'primary',
    icon: 'tabler-users',
    helper: 'All assessments currently on file',
  },
  {
    label: 'High risk · priority action',
    labelEn: 'Act first',
    value: summary.value?.high ?? 0,
    percent: percentage(summary.value?.high, summary.value?.total),
    filter: 'HIGH',
    color: 'error',
    icon: 'tabler-alert-triangle',
    helper: 'Complete a care review today',
  },
  {
    label: 'Medium risk · ongoing follow-up',
    labelEn: 'Follow up',
    value: summary.value?.medium ?? 0,
    percent: percentage(summary.value?.medium, summary.value?.total),
    filter: 'MEDIUM',
    color: 'warning',
    icon: 'tabler-alert-circle',
    helper: 'Schedule a reassessment this week',
  },
  {
    label: 'Low risk · monitor',
    labelEn: 'Maintain',
    value: summary.value?.low ?? 0,
    percent: percentage(summary.value?.low, summary.value?.total),
    filter: 'LOW',
    color: 'success',
    icon: 'tabler-circle-check',
    helper: 'Continue daily prevention measures',
  },
])

function percentage(value: number | undefined, total: number | undefined) {
  if (!total)
    return 0

  return Math.round(((value ?? 0) / total) * 100)
}

function focusRisk(filter: string) {
  if (!filter)
    return

  riskFocus.value = riskFocus.value === filter ? '' : filter
}
</script>

<template>
  <VAlert
    v-if="error"
    color="error"
    variant="tonal"
    class="mb-4"
  >
    Failed to load summary: {{ error }}
  </VAlert>

  <div v-else-if="loading && !summary" class="risk-stats__loading">
    <VRow>
      <VCol
        v-for="index in 4"
        :key="index"
        cols="6"
        sm="6"
        md="3"
      >
        <VSkeletonLoader type="list-item-two-line" class="rounded-lg" />
      </VCol>
    </VRow>
  </div>

  <VRow v-else class="risk-stats">
    <VCol
      v-for="card in cards"
      :key="card.label"
      cols="6"
      sm="6"
      md="3"
    >
      <VCard
        class="risk-stat-card"
        :class="`risk-stat-card--${card.color}`"
        elevation="0"
        :ripple="Boolean(card.filter)"
        :tabindex="card.filter ? 0 : undefined"
        :role="card.filter ? 'button' : undefined"
        :aria-pressed="card.filter ? riskFocus === card.filter : undefined"
        @click="focusRisk(card.filter)"
        @keydown.enter="focusRisk(card.filter)"
        @keydown.space.prevent="focusRisk(card.filter)"
      >
        <VCardText>
          <div class="d-flex align-center justify-space-between mb-4">
            <VAvatar
              :color="card.color"
              variant="tonal"
              size="44"
              rounded
            >
              <VIcon
                :icon="card.icon"
                size="22"
              />
            </VAvatar>

            <VChip
              v-if="card.percent !== null"
              :color="card.color"
              variant="tonal"
              size="small"
              class="risk-stat-card__percent"
            >
              {{ card.percent }}%
            </VChip>
          </div>

          <div class="risk-stat-card__value">
            {{ card.value }}
          </div>
          <div class="risk-stat-card__label">
            {{ card.label }}
          </div>
          <div class="risk-stat-card__en">
            {{ card.labelEn }}
          </div>
          <div v-if="card.percent !== null" class="risk-stat-card__track" aria-hidden="true">
            <span :style="{ width: `${card.percent}%` }" />
          </div>
          <div class="risk-stat-card__helper">
            {{ card.helper }}
          </div>
        </VCardText>
      </VCard>
    </VCol>
  </VRow>
</template>

<style scoped>
.risk-stat-card {
  position: relative;
  overflow: hidden;
  min-block-size: 174px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 16px;
  background: rgb(var(--v-theme-surface));
  transition: transform 180ms ease, box-shadow 180ms ease;
}

.risk-stat-card::after {
  position: absolute;
  inset-block-start: -38px;
  inset-inline-end: -30px;
  width: 112px;
  height: 112px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.06);
  border-radius: 50%;
  content: '';
  pointer-events: none;
}

.risk-stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(var(--v-theme-on-surface), 0.08);
}

.risk-stat-card[role='button'] {
  cursor: pointer;
}

.risk-stat-card[aria-pressed='true'] {
  outline: 2px solid rgba(var(--v-theme-primary), 0.58);
  outline-offset: 2px;
}

.risk-stat-card--error {
  border-color: rgba(var(--v-theme-error), 0.2);
}

.risk-stat-card--warning {
  border-color: rgba(var(--v-theme-warning), 0.2);
}

.risk-stat-card--success {
  border-color: rgba(var(--v-theme-success), 0.2);
}

.risk-stat-card__percent {
  position: relative;
  z-index: 1;
  font-weight: 700;
}

.risk-stat-card__value {
  color: rgb(var(--v-theme-on-surface));
  font-size: 1.85rem;
  font-weight: 750;
  line-height: 1;
}

.risk-stat-card__label {
  margin-block-start: 0.5rem;
  color: rgba(var(--v-theme-on-surface), 0.88);
  font-size: 0.88rem;
  font-weight: 650;
}

.risk-stat-card__en {
  margin-block-start: 0.12rem;
  color: rgba(var(--v-theme-on-surface), 0.5);
  font-size: 0.7rem;
  letter-spacing: 0.01em;
}

.risk-stat-card__track {
  height: 5px;
  margin-block: 0.75rem 0.55rem;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(var(--v-theme-on-surface), 0.08);
}

.risk-stat-card__track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: rgb(var(--v-theme-primary));
}

.risk-stat-card--error .risk-stat-card__track span {
  background: rgb(var(--v-theme-error));
}

.risk-stat-card--warning .risk-stat-card__track span {
  background: rgb(var(--v-theme-warning));
}

.risk-stat-card--success .risk-stat-card__track span {
  background: rgb(var(--v-theme-success));
}

.risk-stat-card__helper {
  color: rgba(var(--v-theme-on-surface), 0.55);
  font-size: 0.7rem;
}

.risk-stats__loading :deep(.v-skeleton-loader) {
  min-height: 174px;
}

@media (max-width: 760px) {
  .risk-stat-card {
    min-block-size: 154px;
  }

  .risk-stat-card__value {
    font-size: 1.55rem;
  }

  .risk-stat-card__label {
    min-block-size: 2.35em;
    font-size: 0.78rem;
    line-height: 1.35;
  }

  .risk-stat-card__en,
  .risk-stat-card__helper {
    display: none;
  }

  .risk-stat-card__track {
    margin-block-start: 0.55rem;
  }
}
</style>
