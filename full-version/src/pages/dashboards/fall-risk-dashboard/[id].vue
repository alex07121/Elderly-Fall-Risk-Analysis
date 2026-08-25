<script setup lang="ts">
import { apiGet, downloadFile } from '@/views/dashboards/fall-risk/useFallRiskApi'

const route = useRoute()
const id = computed(() => route.params.id)

const record = ref<any>(null)
const loading = ref(true)
const error = ref('')
const downloading = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  record.value = null
  try {
    record.value = await apiGet<any>(`/assessments/${id.value}`)
  }
  catch (e: any) {
    error.value = e?.message || String(e)
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

watch(id, load)

const router = useRouter()

const riskColor = computed(() => {
  if (record.value?.fall_risk_level === 'HIGH')
    return 'error'
  if (record.value?.fall_risk_level === 'MEDIUM')
    return 'warning'
  return 'success'
})

const riskBannerClass = computed(() => {
  if (record.value?.fall_risk_level === 'HIGH')
    return 'bg-error text-white'
  if (record.value?.fall_risk_level === 'MEDIUM')
    return 'bg-warning text-white'
  return 'bg-success text-white'
})

const features = computed(() => {
  const r = record.value
  if (!r)
    return []
  return [
    { label: 'Age', value: r.age },
    { label: 'Sex', value: r.sex === 'F' ? 'Female' : r.sex === 'M' ? 'Male' : '—' },
    { label: 'Night bed exits (per night)', value: r.night_bed_exits },
    { label: 'Night activity duration (min)', value: r.night_activity_duration_min },
    { label: 'Past falls (last year)', value: r.past_falls },
    { label: 'Mobility score (1-10)', value: r.mobility_score },
    { label: 'High-risk medication', value: r.high_risk_medication ? 'Yes' : 'No' },
    { label: 'Cognitive impairment (0/1/2)', value: r.cognitive_impairment },
    { label: 'Polypharmacy count', value: r.polypharmacy_count },
    { label: 'Orthostatic hypotension', value: r.orthostatic_hypotension ? 'Yes' : 'No' },
    { label: 'TUG test (seconds)', value: r.tug_seconds },
    { label: 'Days since last fall', value: r.days_since_last_fall ?? '—' },
    { label: 'Syncopal fall (loss of consciousness)', value: r.syncopal_fall ? 'Yes' : 'No' },
    { label: 'Acute fall cluster (2+ in 30 days)', value: r.fall_cluster_30d ? 'Yes' : 'No' },
  ]
})

const suggestion = computed(() => record.value?.suggestion ?? { band: null, not_suggestion: true, items: [] })

const suggestionGroups = computed(() => {
  if (suggestion.value.not_suggestion)
    return []
  const meta = [
    { key: 1, title: 'Act now', color: 'error' },
    { key: 2, title: 'This week', color: 'warning' },
    { key: 3, title: 'Routine', color: 'info' },
  ]
  return meta
    .map(g => ({ ...g, items: suggestion.value.items.filter(it => it.priority === g.key) }))
    .filter(g => g.items.length)
})

function formatDate(iso: string) {
  if (!iso)
    return '—'
  return new Date(iso).toLocaleString()
}

async function handleDownloadPdf() {
  if (!record.value || downloading.value)
    return
  downloading.value = true
  try {
    const filename = `assessment-${record.value.resident_id || record.value.id}.pdf`
    await downloadFile(`/assessments/${id.value}/pdf`, filename)
  }
  catch (e: any) {
    error.value = `PDF download failed: ${e?.message || e}`
  }
  finally {
    downloading.value = false
  }
}
</script>

<template>
  <!-- Loading -->
  <div v-if="loading" class="pa-8 text-center text-medium-emphasis">
    Loading assessment...
  </div>

  <!-- Error -->
  <VAlert
    v-else-if="error"
    color="error"
    variant="tonal"
    class="ma-4"
  >
    Failed to load: {{ error }}
    <template #append>
      <VBtn
        size="small"
        variant="text"
        @click="load"
      >
        Retry
      </VBtn>
    </template>
  </VAlert>

  <!-- Detail -->
  <div v-else-if="record">
    <!-- Header: back / id / risk / actions -->
    <VCard class="mb-4">
      <VCardText class="d-flex align-center gap-3 flex-wrap">
        <VBtn
          icon="tabler-arrow-left"
          variant="text"
          @click="router.push('/dashboards/fall-risk-dashboard')"
        />

        <VChip
          :color="riskColor"
          size="large"
          variant="elevated"
          class="font-weight-bold"
        >
          {{ record.fall_risk_level }} RISK
        </VChip>

        <div class="d-flex flex-column">
          <span class="text-h6">{{ record.resident_id ?? `Assessment #${record.id}` }}</span>
          <span class="text-body-2 text-medium-emphasis">
            {{ record.sex === 'F' ? 'Female' : record.sex === 'M' ? 'Male' : '—' }} · Age {{ record.age }} · Assessed {{ formatDate(record.created_at) }}
          </span>
        </div>

        <VSpacer />

        <VBtn
          color="primary"
          variant="elevated"
          prepend-icon="tabler-download"
          :loading="downloading"
          @click="handleDownloadPdf"
        >
          Download PDF
        </VBtn>
      </VCardText>
    </VCard>

    <!-- HIGH risk banner -->
    <VAlert
      v-if="record.fall_risk_level === 'HIGH'"
      type="error"
      variant="tonal"
      class="mb-4"
      icon="tabler-alert-triangle"
      title="HIGH FALL RISK"
    >
      This resident is at high risk of falling. Please review the explanation below and call the care team
      to take action as soon as possible.
    </VAlert>

    <VRow>
      <!-- Left: Resident profile -->
      <VCol
        cols="12"
        md="5"
      >
        <VCard>
          <VCardItem>
            <VCardTitle>Resident Profile</VCardTitle>
            <VCardSubtitle>14 features used by the model</VCardSubtitle>
          </VCardItem>

          <VDivider />

          <VList density="compact">
            <template
              v-for="(f, i) in features"
              :key="f.label"
            >
              <VListItem class="px-4">
                <VListItemTitle class="text-body-2 text-medium-emphasis">
                  {{ f.label }}
                </VListItemTitle>
                <template #append>
                  <span class="text-body-1 font-weight-medium">{{ f.value }}</span>
                </template>
              </VListItem>
              <VDivider
                v-if="i < features.length - 1"
                :key="`d-${i}`"
              />
            </template>
          </VList>
        </VCard>
      </VCol>

      <!-- Right: Suggestion (60-74 age band, evidence-based) -->
      <VCol
        cols="12"
        md="7"
      >
        <VCard :class="record.fall_risk_level === 'HIGH' ? 'border-error' : ''">
          <VCardItem>
            <VCardTitle>
              <VIcon
                icon="tabler-first-aid-kit"
                class="me-2"
              />
              Suggestion
            </VCardTitle>
            <VCardSubtitle v-if="suggestion.band">
              Age band {{ suggestion.band }} · evidence-based care steps
            </VCardSubtitle>
          </VCardItem>

          <VCardText v-if="suggestion.not_suggestion">
            <span class="text-body-2 text-medium-emphasis">Not suggestion</span>
          </VCardText>

          <template v-else>
            <VDivider />

            <VCardText v-if="!suggestionGroups.length">
              <span class="text-body-2 text-medium-emphasis">No targeted intervention needed at this time - routine fall prevention continues (non-slip slippers, night light, call bell within reach)</span>
            </VCardText>

            <template
              v-for="g in suggestionGroups"
              :key="g.key"
            >
              <VCardText>
                <div class="d-flex align-center gap-2 mb-2">
                  <span
                    class="priority-dot"
                    :style="{ background: `rgb(var(--v-theme-${g.color}))` }"
                  />
                  <span class="text-subtitle-2 font-weight-medium">{{ g.title }}</span>
                </div>

                <div
                  v-for="(it, idx) in g.items"
                  :key="it.feature"
                  class="d-flex align-start gap-2 mb-1"
                >
                  <span class="text-caption font-weight-bold mt-1">{{ idx + 1 }}.</span>
                  <span class="text-body-2">{{ it.action }}</span>
                </div>
              </VCardText>
            </template>
          </template>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>

<style scoped>
.border-error {
  border: 1px solid rgb(var(--v-theme-error));
}
.priority-dot {
  inline-size: 10px;
  block-size: 10px;
  border-radius: 50%;
  flex: 0 0 10px;
}
</style>
