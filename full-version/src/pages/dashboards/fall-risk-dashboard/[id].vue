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
  ]
})

const interventions = computed(() => record.value?.intervention ?? [])
const lime = computed(() => record.value?.lime_explanations ?? [])

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
      This resident is at high risk of falling. Please review the recommended interventions below
      and apply them as soon as possible.
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
            <VCardSubtitle>11 features used by the model</VCardSubtitle>
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

      <!-- Right: Interventions + LIME -->
      <VCol
        cols="12"
        md="7"
      >
        <!-- Interventions (key for family / supervisor) -->
        <VCard :class="record.fall_risk_level === 'HIGH' ? 'border-error' : ''">
          <VCardItem>
            <VCardTitle>
              <VIcon
                icon="tabler-first-aid-kit"
                class="me-2"
              />
              Recommended Care Interventions
            </VCardTitle>
            <VCardSubtitle v-if="!interventions.length">
              No specific intervention needed for this resident.
            </VCardSubtitle>
            <VCardSubtitle v-else>
              Actionable steps to reduce fall risk — share with care team and family.
            </VCardSubtitle>
          </VCardItem>

          <VDivider v-if="interventions.length" />

          <VCardText v-if="interventions.length">
            <div
              v-for="(it, idx) in interventions"
              :key="it.feature"
              class="intervention-row mb-3"
            >
              <div class="d-flex align-center gap-2 mb-1">
                <VAvatar
                  :color="riskColor"
                  size="28"
                  variant="tonal"
                >
                  <span class="text-caption font-weight-bold">{{ idx + 1 }}</span>
                </VAvatar>
                <span class="text-subtitle-2 font-weight-medium">{{ it.label }}</span>
              </div>
              <div class="text-body-2 ms-10">
                {{ it.action }}
              </div>
            </div>
          </VCardText>
        </VCard>

        <!-- LIME explanation -->
        <VCard class="mt-4">
          <VCardItem>
            <VCardTitle>
              <VIcon
                icon="tabler-brain"
                class="me-2"
              />
              Why this risk level
            </VCardTitle>
            <VCardSubtitle>Model explanation (top risk factors)</VCardSubtitle>
          </VCardItem>

          <VDivider />

          <VCardText v-if="lime.length">
            <div
              v-for="(e, i) in lime"
              :key="i"
              class="mb-3"
            >
              <div class="d-flex align-center gap-2">
                <VChip
                  v-if="e.direction?.includes('HIGH')"
                  size="small"
                  color="error"
                  variant="tonal"
                >
                  {{ e.direction }}
                </VChip>
                <VChip
                  v-else
                  size="small"
                  color="success"
                  variant="tonal"
                >
                  {{ e.direction }}
                </VChip>
                <span class="text-body-2">{{ e.condition }}</span>
              </div>
              <div class="text-caption text-medium-emphasis ms-1 mt-1">
                weight: {{ e.weight }}
              </div>
            </div>
          </VCardText>

          <VCardText v-else>
            <span class="text-body-2 text-medium-emphasis">No explanation available.</span>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>

<style scoped>
.border-error {
  border: 1px solid rgb(var(--v-theme-error));
}
.intervention-row:last-child {
  margin-bottom: 0 !important;
}
</style>