<script setup lang="ts">
import { apiGet } from '@/views/dashboards/fall-risk/useFallRiskApi'

const route = useRoute()
const id = computed(() => route.params.id)

const record = ref<any>(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    record.value = await apiGet<any>(`/assessments/${id.value}`)
  }
  catch (e) {
    console.error('Failed to load assessment:', e)
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

const features = computed(() => {
  const r = record.value
  if (!r)
    return []
  return [
    { label: 'Age', value: r.age },
    { label: 'Sex', value: r.sex === 'F' ? 'Female' : r.sex === 'M' ? 'Male' : '—' },
    { label: 'Night bed exits', value: r.night_bed_exits },
    { label: 'Night activity (min)', value: r.night_activity_duration_min },
    { label: 'Past falls', value: r.past_falls },
    { label: 'Mobility score', value: r.mobility_score },
    { label: 'High-risk medication', value: r.high_risk_medication ? 'Yes' : 'No' },
    { label: 'Cognitive impairment', value: r.cognitive_impairment },
    { label: 'Polypharmacy count', value: r.polypharmacy_count },
    { label: 'Orthostatic hypotension', value: r.orthostatic_hypotension ? 'Yes' : 'No' },
    { label: 'TUG (seconds)', value: r.tug_seconds },
  ]
})

const interventions = computed(() => record.value?.intervention ?? [])
const lime = computed(() => record.value?.lime_explanations ?? [])

function formatDate(iso: string) {
  if (!iso)
    return '—'
  return new Date(iso).toLocaleString()
}
</script>

<template>
  <div v-if="record">
    <VRow>
      <VCol cols="12">
        <VCard>
          <VCardText class="d-flex align-center gap-4 flex-wrap">
            <VBtn
              icon="tabler-arrow-left"
              variant="text"
              @click="router.push('/dashboards/fall-risk-dashboard')"
            />

            <div class="d-flex align-center gap-3">
              <VChip
                :color="riskColor"
                size="large"
                class="font-weight-medium"
              >
                {{ record.fall_risk_level }} Risk
              </VChip>
              <span class="text-body-2 text-medium-emphasis">
                {{ record.resident_id ?? `Assessment #${record.id}` }}
              </span>
            </div>

            <span class="text-body-2 text-medium-emphasis ms-auto">
              Assessed {{ formatDate(record.created_at) }}
            </span>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>

    <VRow class="mt-4">
      <VCol
        cols="12"
        md="6"
      >
        <VCard>
          <VCardItem>
            <VCardTitle>Resident Profile</VCardTitle>
          </VCardItem>

          <VCardText>
            <VList density="compact">
              <VListItem
                v-for="f in features"
                :key="f.label"
                class="px-0"
              >
                <VListItemTitle class="text-body-2 text-medium-emphasis">
                  {{ f.label }}
                </VListItemTitle>
                <template #append>
                  <span class="text-body-1 font-weight-medium">{{ f.value }}</span>
                </template>
              </VListItem>
            </VList>
          </VCardText>
        </VCard>
      </VCol>

      <VCol
        cols="12"
        md="6"
      >
        <VCard>
          <VCardItem>
            <VCardTitle>Recommended Interventions</VCardTitle>
            <VCardSubtitle v-if="!interventions.length">
              No specific intervention needed.
            </VCardSubtitle>
          </VCardItem>

          <VCardText v-if="interventions.length">
            <VAlert
              v-for="it in interventions"
              :key="it.feature"
              :color="riskColor"
              variant="tonal"
              class="mb-3"
            >
              <div class="font-weight-medium">{{ it.label }}</div>
              <div class="text-body-2">{{ it.action }}</div>
            </VAlert>
          </VCardText>
        </VCard>

        <VCard class="mt-4">
          <VCardItem>
            <VCardTitle>Why this risk level</VCardTitle>
          </VCardItem>

          <VCardText v-if="lime.length">
            <VList density="compact">
              <VListItem
                v-for="(e, i) in lime"
                :key="i"
                class="px-0"
              >
                <VListItemTitle class="text-body-2">
                  {{ e.condition }}
                </VListItemTitle>
                <template #append>
                  <span class="text-body-2 text-medium-emphasis">{{ e.direction }}</span>
                </template>
              </VListItem>
            </VList>
          </VCardText>

          <VCardText v-else>
            <span class="text-body-2 text-medium-emphasis">No explanation available.</span>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>
