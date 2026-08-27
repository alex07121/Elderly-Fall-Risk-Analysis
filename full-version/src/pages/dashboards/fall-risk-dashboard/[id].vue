<script setup lang="ts">
import { apiGet, downloadFile } from '@/views/dashboards/fall-risk/useFallRiskApi'
import RiskDriversCard from '@/views/dashboards/fall-risk/RiskDriversCard.vue'

definePage({
  meta: {
    public: true,
  },
})

const route = useRoute('dashboards-fall-risk-dashboard-id')
const id = computed(() => route.params.id)

const record = ref<any>(null)
const loading = ref(true)
const error = ref('')
const downloading = ref(false)
const downloadError = ref('')
const downloadNotice = ref(false)

const containsCjk = (value: unknown) => /[\u3400-\u9fff]/u.test(String(value ?? ''))

function englishText(value: unknown, fallback: string): string {
  const text = String(value ?? '').trim()

  return text && !containsCjk(text) ? text : fallback
}

function englishError(value: unknown, fallback: string): string {
  const text = englishText(value, '')

  return text || fallback
}

function residentDisplayId(value: unknown, fallbackId: unknown): string {
  return englishText(value, `Assessment #${fallbackId ?? '—'}`)
}

async function load() {
  loading.value = true
  error.value = ''
  record.value = null
  try {
    record.value = await apiGet<any>(`/assessments/${id.value}`)
  }
  catch (e: any) {
    error.value = englishError(e?.message || String(e), 'Unable to load this assessment. Check the backend connection and try again.')
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

const riskLabel = computed(() => ({
  HIGH: 'High risk',
  MEDIUM: 'Medium risk',
  LOW: 'Low risk',
}[String(record.value?.fall_risk_level ?? '').toUpperCase()] ?? 'Current risk'))

const dataQuality = computed(() => {
  const items = record.value?.data_quality
  return Array.isArray(items) ? items : []
})

function dataQualityMessage(item: { field?: string; message?: string; message_en?: string }): string {
  if (item.message_en)
    return englishText(item.message_en, 'Some source data was normalized for display.')

  if (!containsCjk(item.message))
    return String(item.message ?? '')

  if (item.field === 'days_since_last_fall')
    return 'No fall history is recorded; the original zero-day value is displayed as Not recorded.'

  return 'Some source data was normalized for display.'
}

const features = computed(() => {
  const r = record.value
  if (!r)
    return []

  const hasFallHistory = Number(r.past_falls) > 0

  return [
    { label: 'Age', value: r.age ? `${r.age} years` : '—' },
    { label: 'Sex', value: r.sex === 'F' ? 'Female' : r.sex === 'M' ? 'Male' : '—' },
    { label: 'Night-time bed exits', value: `${r.night_bed_exits ?? '—'} per night` },
    { label: 'Night-time activity duration', value: `${r.night_activity_duration_min ?? '—'} minutes` },
    { label: 'Falls in the past year', value: `${r.past_falls ?? '—'} falls` },
    { label: 'Mobility score', value: `${r.mobility_score ?? '—'} / 10` },
    { label: 'Medicine linked to falls', value: Number(r.high_risk_medication) === 1 ? 'Yes' : 'No' },
    { label: 'Cognitive impairment', value: ({ 0: 'None', 1: 'Mild', 2: 'Moderate-to-severe' } as Record<number, string>)[Number(r.cognitive_impairment)] ?? '—' },
    { label: 'Number of medicines', value: `${r.polypharmacy_count ?? '—'} medicines` },
    { label: 'Postural hypotension', value: Number(r.orthostatic_hypotension) === 1 ? 'Yes' : 'No' },
    { label: 'Timed Up & Go (TUG)', value: r.tug_seconds === null || r.tug_seconds === undefined ? '—' : `${r.tug_seconds} seconds` },
    { label: 'Time since the last fall', value: hasFallHistory && r.days_since_last_fall !== null && r.days_since_last_fall !== undefined ? `${r.days_since_last_fall} days` : 'Not recorded' },
    { label: 'Fall with loss of consciousness', value: Number(r.syncopal_fall) === 1 ? 'Yes' : 'No' },
    { label: 'Two or more falls within 30 days', value: Number(r.fall_cluster_30d) === 1 ? 'Yes' : 'No' },
  ]
})

type SuggestionItem = {
  priority?: number
  lime_priority?: number
  priority_level?: string
  priority_label?: string
  feature: string
  label?: string
  label_zh?: string
  action: string
  action_zh?: string
  attention_rule?: string
  value?: unknown
  weight?: number | string
  risk_weight?: number | string
  direction?: string
  references?: SuggestionReference[]
  reference?: SuggestionReference | SuggestionReference[]
  reference_title?: string
  reference_title_zh?: string
  reference_url?: string
  clinical_attention?: boolean
  risk_direction?: string
  model_effect?: string
  model_effect_zh?: string
  attention_rule_zh?: string
  lime_available?: boolean
  clinical_override?: boolean
}

type SuggestionReference = {
  id?: string
  title: string
  title_zh?: string
  url: string
}

type Suggestion = {
  band: string | number | null
  not_suggestion: boolean
  suggestion_status?: 'suggested' | 'not_suggested'
  not_suggestion_age_band?: string | null
  items: SuggestionItem[]
  priority_basis?: string
  priority_basis_zh?: string
  references?: SuggestionReference[]
  reason?: string
  reason_zh?: string
}

const suggestion = computed<Suggestion>(() => record.value?.suggestion ?? record.value?.suggestions ?? { band: null, not_suggestion: true, items: [] })
const residentAge = computed(() => Number(record.value?.age))
const isNotSuggestedAge = computed(() => Number.isFinite(residentAge.value) && residentAge.value >= 75 && residentAge.value <= 100)
const recommendationsNotSuggested = computed(() => suggestion.value.not_suggestion || isNotSuggestedAge.value)
const suggestionItems = computed(() => Array.isArray(suggestion.value.items) ? suggestion.value.items : [])
const suggestionsWithoutLime = computed(() => suggestionItems.value.filter(item => item.lime_available === false).length)
const unrankedSuggestions = computed(() => suggestionItems.value.filter(item => item.lime_available === false))

const evidenceReferences: Record<string, SuggestionReference> = {
  niceNg249: {
    id: 'NICE-NG249',
    title: 'NICE NG249: Falls assessment and prevention',
    title_zh: 'NICE NG249: Falls assessment and prevention',
    url: 'https://www.nice.org.uk/guidance/ng249/chapter/Recommendations',
  },
  cdcTug: {
    id: 'CDC-STEADI-TUG',
    title: 'CDC STEADI: Timed Up & Go (TUG) Assessment',
    title_zh: 'CDC STEADI: Timed Up & Go (TUG) assessment',
    url: 'https://www.cdc.gov/steadi/media/pdfs/STEADI-Assessment-TUG-508.pdf',
  },
  cdcCarePlan: {
    id: 'CDC-STEADI-CARE-PLAN',
    title: 'CDC STEADI: Coordinated Care Plan to Prevent Older Adult Falls',
    title_zh: 'CDC STEADI: Coordinated care plan to prevent older adult falls',
    url: 'https://www.cdc.gov/steadi/pdf/Steadi-Coordinated-Care-Plan.pdf',
  },
  cdcPostural: {
    id: 'CDC-STEADI-POSTURAL',
    title: 'CDC STEADI: Postural Hypotension',
    title_zh: 'CDC STEADI: Postural hypotension and management',
    url: 'https://stacks.cdc.gov/view/cdc/49080',
  },
  niceTloc: {
    id: 'NICE-CG109',
    title: 'NICE CG109: Transient loss of consciousness (blackouts)',
    title_zh: 'NICE CG109: Transient loss of consciousness (blackouts)',
    url: 'https://www.nice.org.uk/guidance/cg109/chapter/Recommendations',
  },
  cdcMedicines: {
    id: 'CDC-STEADI-MEDS',
    title: 'CDC STEADI: Medications Linked to Falls',
    title_zh: 'CDC STEADI: Medications linked to falls',
    url: 'https://www.cdc.gov/steadi/media/pdfs/steadi-factsheet-medslinkedtofalls-508.pdf',
  },
  cdcHomeSafety: {
    id: 'CDC-STEADI-HOME-SAFETY',
    title: 'CDC STEADI: Check for Safety Home Fall Prevention Checklist',
    title_zh: 'CDC STEADI: Check for safety home fall-prevention checklist',
    url: 'https://stacks.cdc.gov/view/cdc/59197',
  },
  agsBeers: {
    id: 'AGS-BEERS-2023',
    title: '2023 AGS Beers Criteria',
    title_zh: '2023 AGS Beers Criteria for potentially inappropriate medication use',
    url: 'https://doi.org/10.1111/jgs.18372',
  },
}

// Used only for legacy API rows that do not yet carry references.  Do not
// attach a generic link to an unrelated action; an unknown action is shown as
// lacking a verified source so a caregiver can ask the clinical lead.
const fallbackReferencesByFeature: Record<string, SuggestionReference[]> = {
  past_falls: [evidenceReferences.niceNg249, evidenceReferences.cdcCarePlan],
  days_since_last_fall: [evidenceReferences.niceNg249],
  tug_seconds: [evidenceReferences.cdcTug, evidenceReferences.cdcCarePlan],
  mobility_score: [evidenceReferences.niceNg249, evidenceReferences.cdcCarePlan],
  high_risk_medication: [evidenceReferences.cdcMedicines, evidenceReferences.agsBeers],
  polypharmacy_count: [evidenceReferences.cdcCarePlan, evidenceReferences.agsBeers],
  orthostatic_hypotension: [evidenceReferences.cdcPostural, evidenceReferences.niceNg249],
  cognitive_impairment: [evidenceReferences.niceNg249],
  night_bed_exits: [evidenceReferences.niceNg249, evidenceReferences.cdcCarePlan, evidenceReferences.cdcHomeSafety],
  night_activity_duration_min: [evidenceReferences.niceNg249, evidenceReferences.cdcCarePlan],
  syncopal_fall: [evidenceReferences.niceTloc, evidenceReferences.niceNg249],
  fall_cluster_30d: [evidenceReferences.niceNg249, evidenceReferences.cdcCarePlan],
}

function normalizeReferences(value: unknown): SuggestionReference[] {
  const values = Array.isArray(value) ? value : value ? [value] : []
  return values.flatMap(item => {
    if (!item || typeof item !== 'object')
      return []
    const candidate = item as Partial<SuggestionReference>
    if (typeof candidate.url !== 'string')
      return []

    const title = englishText(
      candidate.title,
      englishText(candidate.title_zh, 'Evidence reference'),
    )
    if (!title)
      return []

    return [{ ...candidate, title, url: candidate.url } as SuggestionReference]
  })
}

function suggestionReferences(item: SuggestionItem): SuggestionReference[] {
  const fromApi = normalizeReferences(item.references?.length ? item.references : item.reference)
  const removeAgeScopedSources = (references: SuggestionReference[]) => Number(record.value?.age) < 65
    ? references.filter(reference => reference.id !== evidenceReferences.agsBeers.id && !reference.url.includes('10.1111/jgs.18372'))
    : references
  if (fromApi.length)
    return removeAgeScopedSources(fromApi)

  // A few older API responses expose only the flattened reference fields.
  if (item.reference_url) {
    const flattened = [{
      id: item.reference_url,
      title: englishText(item.reference_title, englishText(item.reference_title_zh, 'Evidence reference')),
      title_zh: item.reference_title_zh,
      url: item.reference_url,
    }]
    return removeAgeScopedSources(flattened)
  }

  const featureFallback = fallbackReferencesByFeature[String(item.feature || '').toLowerCase()] ?? []
  if (featureFallback.length) {
    // AGS Beers is scoped to adults aged 65 and over.  CDC/NICE sources stay
    // available for the 60-64 portion of the configured band.
    return removeAgeScopedSources(featureFallback)
  }

  // Do not attach an aggregate source list to an unknown feature: that can
  // make an unrelated guideline look like evidence for the action.  The
  // The template shows an explicit "No verified source available" warning instead.
  return []
}

function featureTokens(feature: string): string[] {
  return feature
    .toLowerCase()
    .split(/[+\s/,]+/)
    .map(token => token.trim())
    .filter(Boolean)
}

function limeWeightForSuggestion(item: SuggestionItem): number {
  const explicit = Number(item.risk_weight ?? item.weight)
  if (Number.isFinite(explicit))
    return Math.abs(explicit)

  const tokens = featureTokens(String(item.feature || ''))
  const explanations = Array.isArray(record.value?.lime_explanations)
    ? record.value.lime_explanations
    : Array.isArray(record.value?.risk_drivers) ? record.value.risk_drivers : []
  const matches = explanations.filter((explanation: any) => {
    const source = `${explanation.feature || ''} ${explanation.condition || ''}`.toLowerCase()
    return tokens.some(token => source.includes(token))
  })

  return matches.reduce((max: number, explanation: any) => Math.max(max, Math.abs(Number(explanation.weight) || 0)), 0)
}

function suggestionRiskWeightText(item: SuggestionItem): string {
  const weight = Number(item.risk_weight ?? item.weight)
  if (!Number.isFinite(weight))
    return ''

  return Math.abs(weight).toFixed(4)
}

function suggestionModelEffect(item: SuggestionItem): string {
  if (item.model_effect && !containsCjk(item.model_effect))
    return item.model_effect

  const weight = Number(item.risk_weight ?? item.weight)
  if (!Number.isFinite(weight))
    return ''
  if (String(record.value?.fall_risk_level).toUpperCase() === 'MEDIUM')
    return weight > 0 ? 'Supports the current medium-risk classification' : weight < 0 ? 'Away from the current medium-risk classification (not higher or lower)' : 'Minimal influence'
  return weight > 0 ? 'Raises the current risk class' : weight < 0 ? 'Moves away from the current risk class' : 'Minimal influence'
}

function itemPriority(item: SuggestionItem): number | null {
  const numeric = Number(item.priority ?? item.lime_priority)
  if (Number.isFinite(numeric) && numeric >= 1 && numeric <= 3)
    return numeric

  const level = String(item.priority_level || item.priority_label || '').toLowerCase()
  if (level.includes('high'))
    return 1
  if (level.includes('medium'))
    return 2
  if (level.includes('low'))
    return 3

  return null
}

function suggestionAction(item: SuggestionItem): string {
  // The API owns the evidence-backed wording and the references attached to
  // it. Do not replace it with a second, potentially inconsistent rule set in
  // the browser. Legacy rows still get a clear fallback instead of blank text.
  return englishText(
    item.action,
    englishText(item.action_zh, 'Use on-site observations and ask the nurse or clinician to confirm the next care step.'),
  )
}

function suggestionLabel(item: SuggestionItem): string {
  const featureLabels: Record<string, string> = {
    sex: 'Sex',
    age: 'Age',
    night_bed_exits: 'Night-time bed exits',
    night_activity_duration_min: 'Night-time activity duration',
    past_falls: 'Falls in the past year',
    mobility_score: 'Mobility score',
    high_risk_medication: 'Medicine linked to falls',
    cognitive_impairment: 'Cognitive impairment',
    polypharmacy_count: 'Number of medicines',
    orthostatic_hypotension: 'Postural hypotension',
    tug_seconds: 'Timed Up & Go (TUG)',
    days_since_last_fall: 'Time since the last fall',
    syncopal_fall: 'Fall with loss of consciousness',
    fall_cluster_30d: 'Two or more falls within 30 days',
  }

  return englishText(
    item.label,
    featureLabels[String(item.feature || '').toLowerCase()] || englishText(item.feature, 'Assessment input'),
  )
}

function suggestionAttentionRule(item: SuggestionItem): string {
  if (item.attention_rule && !containsCjk(item.attention_rule))
    return item.attention_rule

  const rules: Record<string, string> = {
    age: 'System flag: age ≥75 (action guidance on this page covers ages 60–74).',
    night_bed_exits: 'System flag: ≥2 exits per night (the facility may adjust this in its care plan).',
    night_activity_duration_min: 'System flag: more than 30 minutes of night-time activity (the facility may adjust this in its care plan).',
    past_falls: 'System flag: at least one fall in the past year (the facility may adjust this in its care plan).',
    mobility_score: 'System flag: mobility score ≤4/10 (the facility may adjust this in its care plan).',
    high_risk_medication: 'A medicine linked to falls is recorded; ask a nurse, pharmacist or prescriber to review it.',
    cognitive_impairment: 'System flag: mild or greater cognitive impairment is recorded (the facility may adjust this in its care plan).',
    polypharmacy_count: 'System flag: four or more medicines are recorded (the facility may adjust this in its care plan).',
    orthostatic_hypotension: 'Postural hypotension is recorded; follow the facility process to review symptoms and blood pressure.',
    tug_seconds: 'CDC STEADI flag: TUG ≥12 seconds.',
    days_since_last_fall: 'System flag: a fall occurred within the past 30 days (the facility may adjust this in its care plan).',
    syncopal_fall: 'A fall with fainting or loss of consciousness is recorded; follow the emergency/fall protocol.',
    fall_cluster_30d: 'System flag: repeated falls within 30 days (the facility may adjust this in its care plan).',
  }

  return rules[String(item.feature || '').toLowerCase()] || ''
}

const suggestionGroups = computed(() => {
  if (recommendationsNotSuggested.value)
    return []

  const items = suggestionItems.value
  const rankedItems = items
    .filter(item => item.lime_available !== false)
    .map((item, index) => ({
      item,
      index,
      weight: limeWeightForSuggestion(item),
      explicitPriority: itemPriority(item),
    }))

  // New API rows already carry the LIME-relative priority. Legacy rows use the
  // same relative-magnitude rule rather than an arbitrary list position.
  const fallback = rankedItems
    .filter(entry => entry.explicitPriority === null)
    .sort((a, b) => b.weight - a.weight || a.index - b.index)
  const maxFallbackWeight = Math.max(...fallback.map(entry => entry.weight), 0)
  const fallbackPriority = new Map(fallback.map(entry => {
    const ratio = maxFallbackWeight > 0 ? entry.weight / maxFallbackWeight : 0
    return [entry.index, ratio >= 0.67 ? 1 : ratio >= 0.33 ? 2 : 3]
  }))

  const meta = [
    { key: 1, title: 'High priority · larger model contribution', color: 'error' },
    { key: 2, title: 'Medium priority · moderate model contribution', color: 'warning' },
    { key: 3, title: 'Low priority · smaller model contribution', color: 'info' },
  ]

  return meta
    .map(g => ({
      ...g,
      items: rankedItems
        .filter(entry => (entry.explicitPriority ?? fallbackPriority.get(entry.index)) === g.key)
        .sort((a, b) => b.weight - a.weight || a.index - b.index)
        .map(entry => ({ ...entry.item, limeWeight: entry.weight })),
    }))
    .filter(g => g.items.length)
})

function formatDate(iso: string) {
  if (!iso)
    return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime()))
    return iso
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function handleDownloadPdf() {
  if (!record.value || downloading.value)
    return

  downloadError.value = ''
  downloadNotice.value = false
  downloading.value = true
  try {
    // Keep the downloaded file recognisable when it is later attached to a
    // handover note or stored in a resident folder.
    const residentSource = String(record.value.resident_id || record.value.id)
    const resident = residentSource.replace(/[^a-z0-9_-]+/gi, '-').replace(/^-+|-+$/g, '') || `id-${record.value.id}`
    const risk = String(record.value.fall_risk_level || 'assessment').toLowerCase()
    const filename = `fall-risk-report-${resident}-${risk}.pdf`
    await downloadFile(`/assessments/${id.value}/pdf`, filename)
    downloadNotice.value = true
  }
  catch (e: any) {
    downloadError.value = `PDF download failed: ${englishError(e?.message || e, 'The report could not be generated.')}`
  }
  finally {
    downloading.value = false
  }
}
</script>

<template>
  <!-- Loading -->
  <div v-if="loading" class="pa-8 text-center text-medium-emphasis">
    Loading assessment…
  </div>

  <!-- Error -->
  <VAlert
    v-else-if="error"
    color="error"
    variant="tonal"
    class="ma-4"
  >
    Load failed: {{ error }}
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
          aria-label="Back to fall-risk list"
          @click="router.push('/dashboards/fall-risk-dashboard')"
        />

        <VChip
          :color="riskColor"
          size="large"
          variant="elevated"
          class="font-weight-bold"
        >
          {{ riskLabel }}
        </VChip>

        <div class="d-flex flex-column">
          <span class="text-h6">{{ residentDisplayId(record.resident_id, record.id) }}</span>
          <span class="text-body-2 text-medium-emphasis">
            {{ record.sex === 'F' ? 'Female' : record.sex === 'M' ? 'Male' : '—' }} · {{ record.age }} years · Assessed {{ formatDate(record.created_at) }}
          </span>
        </div>

        <VSpacer />

        <div class="pdf-download-action">
          <div class="pdf-download-action__meta">
            <VAvatar
              color="error"
              variant="tonal"
              size="36"
              class="pdf-download-action__icon"
            >
              <VIcon
                icon="tabler-file-type-pdf"
                size="20"
              />
            </VAvatar>
            <div class="d-none d-sm-flex flex-column">
              <span class="text-body-2 font-weight-medium">Care report</span>
              <span class="text-caption text-medium-emphasis">PDF · Resident details + care advice</span>
            </div>
          </div>
          <VBtn
            color="primary"
            variant="tonal"
            prepend-icon="tabler-download"
            :loading="downloading"
            :aria-label="downloading ? 'Generating care report PDF' : 'Download care report PDF'"
            @click="handleDownloadPdf"
          >
            <span class="d-none d-sm-inline">Download care report</span>
            <span class="d-sm-none">Download PDF</span>
          </VBtn>
        </div>
      </VCardText>
    </VCard>

    <VAlert
      v-if="downloadError"
      color="error"
      variant="tonal"
      density="compact"
      closable
      class="mb-4"
      @click:close="downloadError = ''"
    >
      {{ downloadError }}
    </VAlert>

    <VSnackbar
      v-model="downloadNotice"
      color="success"
      location="top end"
      :timeout="3500"
    >
      Care report download started
    </VSnackbar>

    <!-- HIGH risk banner -->
    <VAlert
      v-if="record.fall_risk_level === 'HIGH'"
      type="error"
      variant="tonal"
      class="mb-4"
      icon="tabler-alert-triangle"
      title="High fall risk"
    >
      This resident is classified as high risk. Review the current inputs in “Why this risk level?” below, then notify the nurse or clinician according to the facility care plan.
    </VAlert>

    <VRow>
      <!-- Left: Resident profile -->
      <VCol
        cols="12"
        md="5"
        class="detail-profile"
      >
        <VCard>
          <VCardItem>
            <VCardTitle>Resident profile</VCardTitle>
            <VCardSubtitle>14 inputs used by this model</VCardSubtitle>
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

          <VAlert
            v-if="dataQuality.length"
            color="warning"
            variant="tonal"
            density="compact"
            class="mx-4 mb-4"
          >
            <div class="font-weight-medium mb-1">Data note</div>
            <div
              v-for="item in dataQuality"
              :key="item.field"
              class="text-body-2"
            >
              {{ dataQualityMessage(item) }}
            </div>
          </VAlert>
        </VCard>
      </VCol>

      <!-- Right: Suggestion (60-74 age band, evidence-based) -->
      <VCol
        cols="12"
        md="7"
        class="detail-explanation"
      >
        <!-- Local explanation card: the caregiver can see exactly which input
          features contributed most to this resident's current model output. -->
        <RiskDriversCard
          :record="record"
          class="mb-4"
        />

        <VCard :class="record.fall_risk_level === 'HIGH' ? 'border-error' : ''">
          <VCardItem>
            <VCardTitle>
              <VIcon
                icon="tabler-first-aid-kit"
                class="me-2"
              />
              Care recommendations
            </VCardTitle>
            <VCardSubtitle v-if="!recommendationsNotSuggested && suggestion.band">
              Age band {{ suggestion.band }} · Actionable care steps ranked by this assessment’s LIME weights
            </VCardSubtitle>
              <VCardSubtitle v-else-if="isNotSuggestedAge">
              Age band 75–100 · Not suggested
            </VCardSubtitle>
            <VCardSubtitle v-else>
              This age is outside the 60–74 recommendation band
            </VCardSubtitle>
          </VCardItem>

          <VCardText v-if="recommendationsNotSuggested">
            <VAlert
              color="info"
              variant="tonal"
              density="compact"
            >
              <div
                v-if="isNotSuggestedAge"
                class="font-weight-medium mb-1"
              >
                Not suggested（75–100 岁）
              </div>
              <div>
                {{ isNotSuggestedAge
                  ? 'Personalized care actions on this page are configured for ages 60–74. No recommendations are generated for ages 75–100; follow the facility’s standard fall-assessment process.'
                  : 'Action guidance on this page is configured for residents aged 60–74. No guidance is shown for this record; follow the facility’s standard fall-assessment process.' }}
              </div>
            </VAlert>
          </VCardText>

          <template v-else>
            <VDivider />

            <VCardText v-if="suggestionsWithoutLime">
              <VAlert
                color="warning"
                variant="tonal"
                density="compact"
                class="mb-0"
              >
                {{ suggestionsWithoutLime }} recommendation(s) have no valid LIME weight. They are shown as on-site attention prompts and should not be described as high, medium or low contribution.
              </VAlert>
            </VCardText>

            <VCardText v-if="unrankedSuggestions.length">
              <div class="d-flex align-center gap-2 mb-2">
                <span
                  class="priority-dot"
                  style="background: rgb(var(--v-theme-warning))"
                />
                <span class="text-subtitle-2 font-weight-medium">On-site attention · no valid LIME priority</span>
              </div>

              <div
                v-for="it in unrankedSuggestions"
                :key="`unranked-${it.feature}`"
                class="suggestion-item"
              >
                <div class="text-body-2 font-weight-medium">
                  {{ suggestionLabel(it) }}
                </div>
                <div class="text-body-2 mt-1">
                  {{ suggestionAction(it) }}
                </div>
                <div
                  v-if="suggestionAttentionRule(it)"
                  class="text-caption text-warning mt-1"
                >
                  Attention flag: {{ suggestionAttentionRule(it) }}
                </div>
                <div class="text-caption text-medium-emphasis mt-1">
                  No local model weight is available for this record; do not place this item in a high, medium or low contribution group.
                </div>

                <div
                  v-if="suggestionReferences(it).length"
                  class="suggestion-reference-row"
                >
                  <VIcon
                    icon="tabler-book-2"
                    size="15"
                    class="me-1"
                  />
                  <span class="text-caption text-medium-emphasis me-1">Evidence:</span>
                  <a
                    v-for="reference in suggestionReferences(it)"
                    :key="reference.id || reference.url"
                    :href="reference.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="suggestion-reference-link"
                  >
                    {{ reference.title }}
                  </a>
                </div>
                <div
                  v-else
                  class="suggestion-reference-row text-caption text-warning"
                >
                  <VIcon
                    icon="tabler-alert-circle"
                    size="15"
                    class="me-1"
                  />
                  No verified source is available. Ask the nurse or clinician to confirm this recommendation before acting on it.
                </div>
              </div>
            </VCardText>

            <VCardText v-if="!suggestionGroups.length && !unrankedSuggestions.length">
              <span class="text-body-2 text-medium-emphasis">No specific action matched this record. Continue the facility’s standard fall-prevention measures and reassess as needed.</span>
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
                  class="suggestion-item"
                >
                  <div class="d-flex align-start gap-2">
                    <span class="text-caption font-weight-bold mt-1">{{ idx + 1 }}.</span>
                    <div class="flex-grow-1">
                      <div class="text-body-2 font-weight-medium">
                        {{ suggestionLabel(it) }}
                      </div>
                      <div class="text-body-2 mt-1">
                        {{ suggestionAction(it) }}
                      </div>
                      <div
                        v-if="suggestionModelEffect(it)"
                        class="text-caption text-medium-emphasis mt-1"
                      >
                        Model direction: {{ suggestionModelEffect(it) }}
                        <span v-if="it.lime_available === false">(no valid LIME weight)</span>
                      </div>
                      <div
                        v-if="suggestionAttentionRule(it)"
                        class="text-caption text-warning mt-1"
                      >
                        Attention flag: {{ suggestionAttentionRule(it) }}
                      </div>
                      <div
                        v-if="suggestionRiskWeightText(it)"
                        class="text-caption text-medium-emphasis mt-1"
                      >
                        Absolute LIME contribution for this assessment: {{ suggestionRiskWeightText(it) }}
                        <VChip
                          v-if="it.clinical_attention"
                          color="error"
                          size="x-small"
                          variant="tonal"
                          class="ms-1"
                        >
                          Nurse/clinician review required
                        </VChip>
                        <VChip
                          v-if="it.clinical_override && !it.clinical_attention"
                          color="warning"
                          size="x-small"
                          variant="tonal"
                          class="ms-1"
                        >
                          Clinical trigger; do not interpret as directional
                        </VChip>
                      </div>
                    </div>
                  </div>

                  <div
                    v-if="suggestionReferences(it).length"
                    class="suggestion-reference-row"
                  >
                    <VIcon
                      icon="tabler-book-2"
                      size="15"
                      class="me-1"
                    />
                    <span class="text-caption text-medium-emphasis me-1">Evidence:</span>
                    <a
                      v-for="reference in suggestionReferences(it)"
                      :key="reference.id || reference.url"
                      :href="reference.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="suggestion-reference-link"
                    >
                      {{ reference.title }}
                    </a>
                  </div>
                  <div
                    v-else
                    class="suggestion-reference-row text-caption text-warning"
                  >
                    <VIcon
                      icon="tabler-alert-circle"
                      size="15"
                      class="me-1"
                    />
                    No verified source is available. Ask the nurse or clinician to confirm this recommendation before acting on it.
                  </div>
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
.pdf-download-action {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.3rem;
  padding-inline-start: 0.45rem;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 12px;
  background: rgba(var(--v-theme-surface), 0.76);
}
.pdf-download-action__meta {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
}
.pdf-download-action__icon {
  flex: 0 0 auto;
}
.priority-dot {
  inline-size: 10px;
  block-size: 10px;
  border-radius: 50%;
  flex: 0 0 10px;
}
.suggestion-item {
  padding-block: 0.55rem;
}
.suggestion-reference-row {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-block-start: 0.55rem;
  padding-inline-start: 1.35rem;
  line-height: 1.45;
}
.suggestion-reference-link {
  color: rgb(var(--v-theme-primary));
  font-size: 0.75rem;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.suggestion-reference-link:hover {
  color: rgb(var(--v-theme-primary-darken-1));
}

@media (max-width: 959px) {
  .detail-explanation {
    order: 1;
  }

  .detail-profile {
    order: 2;
  }
}
</style>
