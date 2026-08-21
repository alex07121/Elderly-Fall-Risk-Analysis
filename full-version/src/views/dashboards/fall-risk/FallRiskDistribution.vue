<script setup lang="ts">
import { apiGet } from './useFallRiskApi'

const summary = ref<any>(null)
const error = ref('')

async function load() {
  try {
    summary.value = await apiGet<any>('/assessments/summary')
    error.value = ''
  }
  catch (e: any) {
    error.value = e?.message || String(e)
  }
}

onMounted(load)

const series = computed(() => [
  summary.value?.high ?? 0,
  summary.value?.medium ?? 0,
  summary.value?.low ?? 0,
])

const chartOptions = computed(() => ({
  chart: { type: 'donut' },
  labels: ['High Risk', 'Medium Risk', 'Low Risk'],
  colors: ['#EA5455', '#FF9F43', '#28C76F'],
  legend: { position: 'bottom' },
  dataLabels: { enabled: true, formatter: (val: number) => `${Math.round(val)}%` },
  plotOptions: {
    pie: {
      donut: { size: '70%' },
    },
  },
}))
</script>

<template>
  <VCard>
    <VCardItem>
      <VCardTitle>Risk Distribution</VCardTitle>
    </VCardItem>

    <VCardText>
      <VAlert
        v-if="error"
        color="error"
        variant="tonal"
      >
        Failed to load: {{ error }}
      </VAlert>

      <VueApexCharts
        v-else-if="summary"
        :options="chartOptions"
        :series="series"
        :height="300"
      />

      <div v-else>
        Loading chart...
      </div>
    </VCardText>
  </VCard>
</template>
