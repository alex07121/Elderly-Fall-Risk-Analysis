<script setup lang="ts">
import { apiGet } from './useFallRiskApi'

const summary = ref<any>(null)
const error = ref('')
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    summary.value = await apiGet<any>('/assessments/summary')
    error.value = ''
  }
  catch (e: any) {
    error.value = e?.message || String(e)
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

const refreshKey = inject<Ref<number>>('refreshKey', ref(0))
watch(refreshKey, load)

const cards = computed(() => [
  { label: 'Total Residents', value: summary.value?.total ?? 0, color: 'primary', icon: 'tabler-users' },
  { label: 'High Risk', value: summary.value?.high ?? 0, color: 'error', icon: 'tabler-alert-triangle' },
  { label: 'Medium Risk', value: summary.value?.medium ?? 0, color: 'warning', icon: 'tabler-alert-circle' },
  { label: 'Low Risk', value: summary.value?.low ?? 0, color: 'success', icon: 'tabler-circle-check' },
])
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

  <div v-else-if="loading && !summary">
    Loading statistics...
  </div>

  <VRow v-else>
    <VCol
      v-for="card in cards"
      :key="card.label"
      cols="12"
      sm="6"
      md="3"
    >
      <VCard>
        <VCardText class="d-flex align-center gap-4">
          <VAvatar
            :color="card.color"
            variant="tonal"
            size="48"
            rounded
          >
            <VIcon
              :icon="card.icon"
              size="24"
            />
          </VAvatar>

          <div>
            <div class="text-body-2 text-medium-emphasis">
              {{ card.label }}
            </div>
            <div class="text-h5 font-weight-medium">
              {{ card.value }}
            </div>
          </div>
        </VCardText>
      </VCard>
    </VCol>
  </VRow>
</template>
