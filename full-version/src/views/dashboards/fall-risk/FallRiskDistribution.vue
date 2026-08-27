<script setup lang="ts">
import { useTheme } from 'vuetify'
import { apiGet } from './useFallRiskApi'

interface RiskSummary {
  total: number
  high: number
  medium: number
  low: number
}

const vuetifyTheme = useTheme()
const summary = ref<RiskSummary | null>(null)
const error = ref('')
const loading = ref(true)
const containsCjk = (value: unknown) => /[\u3400-\u9fff]/u.test(String(value ?? ''))

function englishError(value: unknown): string {
  const text = String(value ?? '').trim()

  return text && !containsCjk(text) ? text : 'Unable to load risk distribution. Check the backend connection and try again.'
}

async function load() {
  loading.value = true
  try {
    summary.value = await apiGet<RiskSummary>('/assessments/summary')
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

const segments = computed(() => [
  {
    key: 'high',
    filter: 'HIGH',
    label: 'High risk',
    labelEn: 'Priority action',
    value: summary.value?.high ?? 0,
    color: 'error',
    hex: vuetifyTheme.current.value.colors.error,
  },
  {
    key: 'medium',
    filter: 'MEDIUM',
    label: 'Medium risk',
    labelEn: 'Ongoing follow-up',
    value: summary.value?.medium ?? 0,
    color: 'warning',
    hex: vuetifyTheme.current.value.colors.warning,
  },
  {
    key: 'low',
    filter: 'LOW',
    label: 'Low risk',
    labelEn: 'Continue monitoring',
    value: summary.value?.low ?? 0,
    color: 'success',
    hex: vuetifyTheme.current.value.colors.success,
  },
])

const series = computed(() => segments.value.map(segment => segment.value))

const chartAriaLabel = computed(() => {
  const detail = segments.value.map(segment => `${segment.label}: ${segment.value} residents`).join(', ')

  return `Risk distribution chart: ${detail}`
})

function percent(value: number) {
  const total = summary.value?.total ?? 0

  return total ? Math.round((value / total) * 100) : 0
}

function focusRisk(filter: string) {
  riskFocus.value = riskFocus.value === filter ? '' : filter
}

const chartOptions = computed(() => {
  const currentTheme = vuetifyTheme.current.value.colors

  return {
    chart: {
      type: 'donut',
      fontFamily: 'Public Sans, sans-serif',
      parentHeightOffset: 0,
      toolbar: { show: false },
    },
    labels: segments.value.map(segment => segment.label),
    colors: segments.value.map(segment => segment.hex),
    stroke: {
      width: 5,
      colors: [currentTheme.surface],
    },
    legend: { show: false },
    dataLabels: { enabled: false },
    plotOptions: {
      pie: {
        expandOnClick: false,
        donut: {
          size: '76%',
          labels: {
            show: true,
            name: {
              show: true,
              offsetY: 23,
              color: currentTheme['on-surface'],
              fontSize: '12px',
              formatter: () => 'Residents monitored',
            },
            value: {
              show: true,
              offsetY: -9,
              color: currentTheme['on-surface'],
              fontSize: '30px',
              fontWeight: 700,
              formatter: (value: string) => value,
            },
            total: {
              show: true,
              showAlways: true,
              label: 'Residents monitored',
              color: currentTheme['on-surface'],
              fontSize: '12px',
              fontWeight: 500,
              formatter: () => String(summary.value?.total ?? 0),
            },
          },
        },
      },
    },
    tooltip: {
      y: {
        formatter: (value: number) => `${value} residents`,
      },
    },
    states: {
      hover: { filter: { type: 'none' } },
      active: { filter: { type: 'none' } },
    },
  }
})
</script>

<template>
  <VCard class="risk-distribution" elevation="0">
    <VCardItem class="pb-0">
      <template #prepend>
        <VAvatar color="primary" variant="tonal" rounded size="40">
          <VIcon icon="tabler-chart-donut-3" size="21" />
        </VAvatar>
      </template>

      <VCardTitle>Risk distribution</VCardTitle>
      <VCardSubtitle>Risk distribution · Current assessment mix</VCardSubtitle>

      <template #append>
        <VChip color="success" variant="tonal" size="small">
          <VIcon icon="tabler-point-filled" size="15" start />
          Live
        </VChip>
      </template>
    </VCardItem>

    <VCardText class="pt-2">
      <VAlert
        v-if="error"
        color="error"
        variant="tonal"
      >
        Failed to load risk distribution: {{ error }}
      </VAlert>

      <div v-else-if="loading && !summary" class="risk-distribution__loading">
        <VSkeletonLoader type="image, list-item-two-line" />
      </div>

      <div v-else class="risk-distribution__content">
        <div
          class="risk-distribution__chart"
          role="img"
          :aria-label="chartAriaLabel"
        >
          <VueApexCharts
            :options="chartOptions"
            :series="series"
            :height="246"
          />
        </div>

        <div class="risk-distribution__legend">
          <div
            v-for="segment in segments"
            :key="segment.key"
            class="risk-distribution__legend-item"
            :class="{ 'risk-distribution__legend-item--active': riskFocus === segment.filter }"
            role="button"
            tabindex="0"
            :aria-pressed="riskFocus === segment.filter"
            @click="focusRisk(segment.filter)"
            @keydown.enter="focusRisk(segment.filter)"
            @keydown.space.prevent="focusRisk(segment.filter)"
          >
            <div class="d-flex align-center justify-space-between ga-3">
              <div class="d-flex align-center ga-2">
                <span
                  class="risk-distribution__dot"
                  :style="{ backgroundColor: segment.hex }"
                />
                <div>
                  <div class="text-body-2 font-weight-semibold">
                    {{ segment.label }}
                  </div>
                  <div class="text-caption text-medium-emphasis">
                    {{ segment.labelEn }}
                  </div>
                </div>
              </div>
              <div class="text-end">
                <div class="text-body-2 font-weight-bold">
                  {{ segment.value }} residents
                </div>
                <div class="text-caption text-medium-emphasis">
                  {{ percent(segment.value) }}%
                </div>
              </div>
            </div>

            <div class="risk-distribution__bar">
              <span
                :style="{
                  width: `${percent(segment.value)}%`,
                  backgroundColor: segment.hex,
                }"
              />
            </div>
          </div>
        </div>
      </div>

      <div v-if="summary" class="risk-distribution__callout">
        <VIcon icon="tabler-bell-ringing" color="error" size="20" />
        <div>
          <div class="text-body-2 font-weight-semibold">
            {{ summary.high }} high-risk residents need priority review
          </div>
          <div class="text-caption text-medium-emphasis">
            During handover, address the high-risk queue first, then schedule medium-risk reassessments.
          </div>
        </div>
      </div>
    </VCardText>
  </VCard>
</template>

<style scoped>
.risk-distribution {
  height: auto;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 18px;
}

.risk-distribution :deep(.v-card-subtitle) {
  overflow: visible;
  white-space: normal;
  text-overflow: clip;
}

.risk-distribution__content {
  display: grid;
  align-items: center;
  grid-template-columns: minmax(190px, 0.9fr) minmax(180px, 1.1fr);
}

.risk-distribution__chart {
  min-width: 0;
}

.risk-distribution__legend {
  display: grid;
  gap: 0.85rem;
}

.risk-distribution__legend-item {
  min-width: 0;
  padding: 0.35rem 0.45rem;
  border-radius: 9px;
  cursor: pointer;
  transition: background-color 160ms ease;
}

.risk-distribution__legend-item:hover,
.risk-distribution__legend-item--active {
  background: rgba(var(--v-theme-on-surface), 0.045);
}

.risk-distribution__dot {
  width: 10px;
  height: 10px;
  flex: 0 0 auto;
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(var(--v-theme-on-surface), 0.04);
}

.risk-distribution__bar {
  height: 4px;
  margin-block-start: 0.45rem;
  overflow: hidden;
  border-radius: 99px;
  background: rgba(var(--v-theme-on-surface), 0.07);
}

.risk-distribution__bar span {
  display: block;
  height: 100%;
  min-width: 3px;
  border-radius: inherit;
}

.risk-distribution__callout {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border: 1px solid rgba(var(--v-theme-error), 0.14);
  border-radius: 12px;
  background: rgba(var(--v-theme-error), 0.055);
}

.risk-distribution__loading {
  min-height: 330px;
}

@media (max-width: 680px) {
  .risk-distribution__content {
    grid-template-columns: 1fr;
  }

  .risk-distribution__chart {
    margin-block-end: -0.5rem;
  }
}
</style>
