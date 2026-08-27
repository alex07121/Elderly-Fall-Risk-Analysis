<script setup lang="ts">
import { computed } from 'vue'

type LimeExplanation = {
  feature?: string
  label?: string
  label_en?: string
  /** Legacy localized fields are retained for API compatibility but never rendered. */
  label_zh?: string
  value?: unknown
  condition?: string
  weight?: number | string
  risk_weight?: number | string
  direction?: string
  impact?: string
  rank?: number
  lime_weight?: number | string
  score?: number | string
  risk_signal?: string
  is_elevated?: boolean
  model_effect?: string
  model_effect_en?: string
  model_effect_zh?: string
  attention_rule?: string
  attention_rule_en?: string
  attention_rule_zh?: string
  lime_available?: boolean
}

type AssessmentRecord = {
  age?: number | null
  sex?: string | null
  fall_risk_level?: string | null
  lime_explanations?: LimeExplanation[] | null
  risk_drivers?: LimeExplanation[] | null
  [key: string]: unknown
}

const props = defineProps<{
  record: AssessmentRecord
}>()

type FeatureMeta = {
  key: string
  label: string
  unit?: string
  format?: (value: unknown) => string
}

const yesNo = (value: unknown) => {
  if (typeof value === 'string') {
    if (/^(yes|true|1)$/i.test(value.trim()))
      return 'Yes'
    if (/^(no|false|0)$/i.test(value.trim()))
      return 'No'
  }

  return Number(value) === 1 ? 'Yes' : 'No'
}
const numberText = (value: unknown) => {
  if (value === null || value === undefined || value === '')
    return '—'

  const number = Number(value)
  if (!Number.isFinite(number))
    return String(value)

  return Number.isInteger(number) ? String(number) : number.toFixed(1)
}

function appendUnit(meta: FeatureMeta | undefined, formatted: string, rawValue: unknown): string {
  if (!meta?.unit || formatted === '—')
    return formatted

  const singularUnits: Record<string, string> = {
    years: 'year',
    falls: 'fall',
    medicines: 'medicine',
    days: 'day',
    minutes: 'minute',
    seconds: 'second',
    'times/night': 'time/night',
  }
  const unit = Number(rawValue) === 1 ? singularUnits[meta.unit] || meta.unit : meta.unit

  return `${formatted} ${unit}`
}

const FEATURE_META: FeatureMeta[] = [
  { key: 'age', label: 'Age', unit: 'years', format: numberText },
  {
    key: 'sex',
    label: 'Sex',
    format: value => {
      const normalized = String(value ?? '').trim().toUpperCase()
      return normalized === 'F' || normalized === 'FEMALE'
        ? 'Female'
        : normalized === 'M' || normalized === 'MALE' ? 'Male' : '—'
    },
  },
  { key: 'night_bed_exits', label: 'Night-time bed exits', unit: 'times/night', format: numberText },
  { key: 'night_activity_duration_min', label: 'Night-time activity duration', unit: 'minutes', format: numberText },
  { key: 'past_falls', label: 'Falls in the past year', unit: 'falls', format: numberText },
  { key: 'mobility_score', label: 'Mobility score', unit: '/10', format: numberText },
  { key: 'high_risk_medication', label: 'Medicine linked to falls', format: yesNo },
  { key: 'cognitive_impairment', label: 'Cognitive impairment', format: value => ({ 0: 'None', 1: 'Mild', 2: 'Moderate-to-severe' } as Record<number, string>)[Number(value)] ?? '—' },
  { key: 'polypharmacy_count', label: 'Number of medicines', unit: 'medicines', format: numberText },
  { key: 'orthostatic_hypotension', label: 'Postural hypotension', format: yesNo },
  { key: 'tug_seconds', label: 'Timed Up & Go (TUG)', unit: 'seconds', format: numberText },
  { key: 'days_since_last_fall', label: 'Time since the last fall', unit: 'days', format: numberText },
  { key: 'syncopal_fall', label: 'Fall with loss of consciousness', format: yesNo },
  { key: 'fall_cluster_30d', label: 'Two or more falls within 30 days', format: yesNo },
]

const featureByKey = new Map(FEATURE_META.map(feature => [feature.key, feature]))

const ATTENTION_RULES_EN: Record<string, string> = {
  age: 'System attention threshold: age ≥75 years (care recommendations on this page cover ages 60–74 only).',
  night_bed_exits: 'System attention threshold: at least 2 bed exits per night (adjustable to the facility care plan).',
  night_activity_duration_min: 'System attention threshold: more than 30 minutes of night-time activity (adjustable to the facility care plan).',
  past_falls: 'System attention threshold: at least one fall in the past year (adjustable to the facility care plan).',
  mobility_score: 'System attention threshold: mobility score ≤4/10 (adjustable to the facility care plan).',
  high_risk_medication: 'Record flags medicine linked to falls; ask a nurse, pharmacist, or prescriber to review.',
  cognitive_impairment: 'System attention threshold: documented mild or greater cognitive impairment (adjustable to the facility care plan).',
  polypharmacy_count: 'System attention threshold: four or more medicines documented (adjustable to the facility care plan).',
  orthostatic_hypotension: 'Record flags postural hypotension; follow facility protocol to review symptoms and blood pressure.',
  tug_seconds: 'CDC STEADI attention threshold: TUG ≥12 seconds.',
  days_since_last_fall: 'System attention threshold: a fall occurred within the last 30 days (adjustable to the facility care plan).',
  syncopal_fall: 'Record flags a fall associated with fainting or loss of consciousness; follow the facility emergency/fall protocol.',
  fall_cluster_30d: 'System attention threshold: repeated falls within 30 days (adjustable to the facility care plan).',
}

const hasCjk = (value: string) => /[\u3400-\u9fff]/.test(value)

const legacyValueTranslations: Record<string, string> = {
  '\u662f': 'Yes',
  '\u5426': 'No',
  '\u5973': 'Female',
  '\u7537': 'Male',
  '\u65e0': 'None',
  '\u8f7b\u5ea6': 'Mild',
  '\u4e2d\u91cd\u5ea6': 'Moderate-to-severe',
  '\u672a\u8bb0\u5f55': 'Not recorded',
}

function englishFallback(value: unknown, fallback: string): string {
  const text = String(value ?? '').trim()
  return text && !hasCjk(text) ? text : fallback
}

function inferFeatureKeys(explanation: LimeExplanation): string[] {
  const explicit = typeof explanation.feature === 'string' ? explanation.feature : ''
  const condition = String(explanation.condition ?? '')
  const source = `${explicit} ${condition}`.toLowerCase()

  // Composite suggestions may be returned by a future API revision. Keep each
  // known feature visible instead of collapsing it into an opaque key.
  const keys = FEATURE_META
    .filter(feature => source.includes(feature.key.toLowerCase()))
    .map(feature => feature.key)

  if (keys.length)
    return keys

  const explicitKey = explicit.toLowerCase().trim()
  return featureByKey.has(explicitKey) ? [explicitKey] : []
}

function formatFeatureValue(keys: string[], explanation: LimeExplanation): string {
  if (keys.includes('days_since_last_fall') && Number(props.record.past_falls) === 0)
    return 'Not recorded'

  if (explanation.value !== undefined && explanation.value !== null && explanation.value !== '') {
    const rawSupplied = String(explanation.value).trim()
    const supplied = legacyValueTranslations[rawSupplied] || rawSupplied
    if (/^(yes|true)$/i.test(supplied))
      return 'Yes'
    if (/^(no|false)$/i.test(supplied))
      return 'No'
    if (/^female$/i.test(supplied))
      return 'Female'
    if (/^male$/i.test(supplied))
      return 'Male'
    if (/^none$/i.test(supplied) && keys.includes('cognitive_impairment'))
      return 'None'
    if (/^mild$/i.test(supplied) && keys.includes('cognitive_impairment'))
      return 'Mild'
    if (/^moderate-to-severe$/i.test(supplied) && keys.includes('cognitive_impairment'))
      return 'Moderate-to-severe'

    // Older API rows sometimes return a bare numeric value while newer rows
    // include the unit in the display value. Add the known unit for the
    // former, so caregivers see “12 seconds” rather than an unexplained “12”.
    if (keys.length === 1 && /^[-+]?\d+(?:\.\d+)?$/.test(supplied.trim())) {
      const meta = featureByKey.get(keys[0])
      const formatted = meta?.format ? meta.format(supplied) : supplied
      return appendUnit(meta, formatted, supplied)
    }

    const normalized = supplied
      .replace(/\bsecs?\b/gi, 'seconds')
      .replace(/\bmins?\b/gi, 'minutes')
      .replace(/\bseconds?\b/gi, 'seconds')
      .replace(/\bminutes?\b/gi, 'minutes')
      .replace(/\bdays?\b/gi, 'days')
      // A few imported legacy rows contain localized units. Keep those rows
      // readable without allowing non-English text to leak into this card.
      .replace(/\u79d2/g, 'seconds')
      .replace(/\u5206\u949f/g, 'minutes')
      .replace(/\u5929/g, 'days')

    return hasCjk(normalized) ? fallbackFeatureValue(keys) : normalized
  }

  return fallbackFeatureValue(keys)
}

function translateCondition(condition: string, keys: string[]): string {
  let translated = condition
  keys.forEach(key => {
    const label = featureByKey.get(key)?.label ?? key
    translated = translated.replace(
      new RegExp(`(^|[^A-Za-z0-9_])${key}(?=$|[^A-Za-z0-9_])`, 'gi'),
      `$1${label}`,
    )
  })
  const normalized = translated
    .replace(/\u662f/g, 'Yes')
    .replace(/\u5426/g, 'No')
    .replace(/\u79d2/g, 'seconds')
    .replace(/\u5206\u949f/g, 'minutes')
    .replace(/\u5929/g, 'days')
  return normalized && !hasCjk(normalized) ? normalized : 'This feature in the current assessment'
}

function fallbackFeatureValue(keys: string[]): string {
  const values = keys.map(key => {
    const meta = featureByKey.get(key)
    const value = props.record[key]
    const formatted = meta?.format ? meta.format(value) : numberText(value)
    return appendUnit(meta, formatted, value)
  })

  return values.join(' · ') || '—'
}

function numericWeight(value: unknown): number {
  const weight = Number(value)
  return Number.isFinite(weight) ? weight : 0
}

const riskLevel = computed(() => String(props.record?.fall_risk_level ?? '').toUpperCase())

const riskTitle = computed(() => ({
  HIGH: 'High risk',
  MEDIUM: 'Medium risk',
  LOW: 'Low risk',
}[riskLevel.value] ?? 'Current risk'))

function modelEffectText(
  suppliedValue: unknown,
  level: string,
  weight: number,
  riskWeight: number,
): string {
  const supplied = String(suppliedValue ?? '').trim()
  if (supplied && !hasCjk(supplied)) {
    const normalized = supplied.toLowerCase().replace(/[\s-]+/g, '_')
    const known: Record<string, string> = {
      neutral: 'Minimal effect',
      supports_current_level: 'Supports the current medium risk level',
      away_from_current_level: 'Moves away from the current medium risk level (not necessarily higher or lower)',
      risk_direction: 'Raises the current risk level',
      protective_direction: 'Moves away from the current risk level',
      risk: 'Raises the current risk level',
      protective: 'Protective factor',
      increases_current_risk_class: 'Raises the current risk level',
      pulls_away_from_current_risk_class: 'Moves away from the current risk level',
    }
    if (known[normalized])
      return known[normalized]

    return supplied
  }

  if (weight === 0)
    return 'Minimal effect'
  if (level === 'MEDIUM')
    return weight > 0
      ? 'Supports the current medium risk level'
      : 'Moves away from the current medium risk level (not necessarily higher or lower)'

  return riskWeight > 0 ? 'Raises the current risk level' : 'Moves away from the current risk level'
}

const rawExplanations = computed<LimeExplanation[]>(() => {
  const preferred = props.record?.risk_drivers
  if (Array.isArray(preferred) && preferred.length)
    return preferred

  const legacy = props.record?.lime_explanations
  return Array.isArray(legacy) ? legacy : []
})

const allDrivers = computed(() => rawExplanations.value
  .map((item, index) => {
    const keys = inferFeatureKeys(item)
    const weight = numericWeight(item.weight ?? item.lime_weight ?? item.score)
    const riskWeight = numericWeight(item.risk_weight ?? (riskLevel.value === 'LOW' ? -weight : weight))
    const direction = String(item.direction ?? '').toLowerCase()
    const pushesPrediction = direction.includes('push') || (!direction && weight >= 0)
    const level = riskLevel.value

    let impact: 'risk' | 'protective' | 'neutral' = 'neutral'
    if (level === 'HIGH' || level === 'MEDIUM')
      impact = pushesPrediction ? 'risk' : 'protective'
    else if (level === 'LOW')
      impact = pushesPrediction ? 'protective' : 'risk'

    const finalImpact: 'risk' | 'protective' | 'neutral' = item.impact === 'risk' || item.impact === 'protective' || item.impact === 'neutral' ? item.impact : impact
    const modelEffect = modelEffectText(item.model_effect || item.model_effect_en, level, weight, riskWeight)
    const impactLabel = level === 'MEDIUM'
      ? modelEffect
      : finalImpact === 'risk'
        ? 'Raises the current risk level'
        : finalImpact === 'protective'
          ? 'Protective / moves away from the current level'
          : 'Minimal effect'
    const rank = Number(item.rank)
    const fallbackLabel = keys.map(key => featureByKey.get(key)?.label ?? key).join(' + ') || 'Model feature'
    const label = englishFallback(item.label || item.label_en, fallbackLabel)
    const attentionRule = englishFallback(
      item.attention_rule || item.attention_rule_en,
      keys.map(key => ATTENTION_RULES_EN[key]).find(Boolean) || '',
    )

    return {
      ...item,
      keys,
      label,
      labelEn: label,
      valueText: formatFeatureValue(keys, item),
      conditionText: translateCondition(String(item.condition ?? ''), keys),
      weight,
      riskWeight,
      weightText: `${weight >= 0 ? '+' : ''}${weight.toFixed(4)}`,
      riskWeightText: `${riskWeight >= 0 ? '+' : ''}${riskWeight.toFixed(4)}`,
      directionText: modelEffect,
      impact: finalImpact,
      impactLabel,
      modelEffect,
      attentionRule,
      limeAvailable: item.lime_available !== false,
      elevated: item.is_elevated === true || item.risk_signal === 'elevated',
      rank: Number.isFinite(rank) && rank > 0 ? rank : index + 1,
    }
  }))

const sortByContribution = <T extends { riskWeight: number; elevated: boolean; label: string }>(items: T[]) => items.slice().sort((a, b) => {
  return Math.abs(b.riskWeight) - Math.abs(a.riskWeight)
    || (a.elevated === b.elevated ? 0 : a.elevated ? -1 : 1)
    || a.label.localeCompare(b.label)
})

const attentionDrivers = computed(() => sortByContribution(allDrivers.value.filter(driver => driver.elevated)))
const modelOnlyRiskDrivers = computed(() => sortByContribution(allDrivers.value.filter(driver => !driver.elevated && driver.impact === 'risk')))

function decorateDrivers(source: typeof allDrivers.value, referenceSource: typeof allDrivers.value = source) {
  const visible = source.slice(0, 5)
  const maxRiskWeight = Math.max(...referenceSource.map(driver => Math.abs(driver.riskWeight)), 0.0001)

  return visible.map((item, index) => {
    const ratio = Math.abs(item.riskWeight) / maxRiskWeight
    const priorityLabel = ratio >= 0.67 ? 'High' : ratio >= 0.33 ? 'Medium' : 'Low'

    return {
      ...item,
      rank: index + 1,
      priorityLabel,
      priorityColor: priorityLabel === 'High' ? 'error' : priorityLabel === 'Medium' ? 'warning' : 'info',
      impactColor: riskLevel.value === 'MEDIUM'
        ? 'info'
        : item.impact === 'risk' ? 'error' : item.impact === 'protective' ? 'success' : 'info',
      bar: Math.round(ratio * 100),
      statusLabel: item.elevated ? 'Review current value' : item.impact === 'risk' ? 'Model direction (below attention threshold)' : 'Protective / background',
    }
  })
}

const drivers = computed(() => decorateDrivers(
  attentionDrivers.value.length
    ? attentionDrivers.value
    : modelOnlyRiskDrivers.value.length
      ? modelOnlyRiskDrivers.value
      : sortByContribution(allDrivers.value),
))
const missingLimeCount = computed(() => drivers.value.filter(driver => !driver.limeAvailable).length)
</script>

<template>
  <VCard
    class="risk-drivers-card"
    :class="{ 'risk-drivers-card--high': riskLevel === 'HIGH' }"
  >
    <VCardItem>
      <template #prepend>
        <VAvatar
          color="error"
          variant="tonal"
          rounded
        >
          <VIcon icon="tabler-chart-arcs-3" />
        </VAvatar>
      </template>
      <VCardTitle>Why is this rated {{ riskTitle }}?</VCardTitle>
      <VCardSubtitle>
        Review flagged values and the inputs that contributed most to this result.
      </VCardSubtitle>
    </VCardItem>

    <VDivider />

    <VCardText>
      <VAlert
        v-if="!drivers.length"
        color="info"
        variant="tonal"
        density="compact"
      >
        No LIME explanation is available for this record. Run the assessment again.
      </VAlert>

      <template v-else>
        <div
          v-for="driver in drivers"
          :key="`${driver.condition}-${driver.rank}`"
          class="risk-driver"
        >
          <div class="risk-driver__head">
            <VChip
              :color="driver.priorityColor"
              size="small"
              variant="tonal"
              class="risk-driver__priority"
            >
              {{ driver.priorityLabel }} contribution
            </VChip>

            <div class="risk-driver__identity">
              <div class="text-body-2 font-weight-bold">
                {{ driver.label }}
              </div>
              <div class="text-caption text-medium-emphasis">
                Current value: {{ driver.valueText }}
                <span
                  v-if="driver.elevated || driver.impact === 'risk'"
                  class="risk-driver__signal"
                >
                  · {{ driver.statusLabel }}
                </span>
              </div>
            </div>

            <VChip
              :color="driver.impactColor"
              size="small"
              variant="tonal"
              class="risk-driver__impact"
            >
              {{ driver.elevated ? 'Review current value' : driver.impactLabel }}
            </VChip>

            <span class="risk-driver__weight text-caption font-weight-bold">
              {{ riskLevel === 'MEDIUM' ? 'Current-level contribution' : 'Risk contribution' }} {{ driver.riskWeightText }}
            </span>
          </div>

          <VProgressLinear
            :model-value="driver.bar"
            :color="driver.impactColor"
            height="7"
            rounded
            class="my-2"
            :aria-label="`${driver.label} relative model contribution ${driver.bar}%`"
          />

        </div>

        <VAlert
          v-if="missingLimeCount"
          color="warning"
          variant="tonal"
          density="compact"
          class="mt-3 mb-0"
        >
          {{ missingLimeCount }} input{{ missingLimeCount === 1 ? '' : 's' }} {{ missingLimeCount === 1 ? 'has' : 'have' }} no valid local weight{{ missingLimeCount === 1 ? '' : 's' }}. Treat this as an on-site attention cue, not a LIME ranking.
        </VAlert>

      </template>
    </VCardText>
  </VCard>
</template>

<style scoped>
.risk-drivers-card {
  border: 1px solid rgba(var(--v-theme-primary), 0.14);
}

.risk-drivers-card--high {
  border-color: rgba(var(--v-theme-error), 0.42);
}

.risk-driver {
  padding-block: 0.9rem;
  border-block-end: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.risk-driver:last-of-type {
  border-block-end: 0;
}

.risk-driver__head {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.risk-driver__priority,
.risk-driver__impact {
  flex: 0 0 auto;
}

.risk-driver__identity {
  min-inline-size: 0;
  flex: 1 1 auto;
}

.risk-driver__identity > div:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.risk-driver__weight {
  min-inline-size: 3.9rem;
  color: rgba(var(--v-theme-on-surface), 0.72);
  text-align: end;
}

.risk-driver__signal {
  color: rgb(var(--v-theme-error));
  font-weight: 600;
}

@media (max-width: 600px) {
  .risk-driver__head {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .risk-driver__identity {
    min-inline-size: calc(100% - 5.5rem);
  }

  .risk-driver__impact {
    margin-inline-start: 2.5rem;
  }

  .risk-driver__weight {
    margin-inline-start: auto;
  }
}
</style>
