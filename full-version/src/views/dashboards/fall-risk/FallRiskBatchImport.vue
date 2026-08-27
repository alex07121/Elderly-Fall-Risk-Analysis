<script setup lang="ts">
import { computed, ref } from 'vue'

interface BatchImportResult {
  success: number
  skipped: number
  total: number
  errors?: string[]
  message?: string
}

interface BatchImportProps {
  apiBase?: string
  uploadPath?: string
  templateUrl?: string
  maxFileSizeMb?: number
}

const props = withDefaults(defineProps<BatchImportProps>(), {
  apiBase: () => import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  uploadPath: () => import.meta.env.VITE_BATCH_IMPORT_PATH || '/batch-predict',
  templateUrl: '',
  maxFileSizeMb: 10,
})

const emit = defineEmits<{
  (event: 'uploaded', payload: BatchImportResult): void
  (event: 'error', error: Error): void
}>()

const dialog = ref(false)
const file = ref<File | File[] | null>(null)
const loading = ref(false)
const downloadingTemplate = ref(false)
const error = ref('')
const result = ref<BatchImportResult | null>(null)
const guidePanel = ref<number | null>(null)

const selectedFile = computed(() => Array.isArray(file.value) ? file.value[0] : file.value)
const apiRoot = computed(() => props.apiBase.replace(/\/$/, ''))
const endpoint = computed(() => `${apiRoot.value}/${props.uploadPath.replace(/^\//, '')}`)
const templateHref = computed(() => props.templateUrl || `${apiRoot.value}/batch-template`)
const visibleErrors = computed(() => (result.value?.errors || [])
  .slice(0, 5)
  .map(rowError => englishError(rowError, 'A row could not be imported.')))
const remainingErrors = computed(() => Math.max(0, (result.value?.errors?.length || 0) - visibleErrors.value.length))
const resultColor = computed(() => result.value?.skipped ? 'warning' : 'success')

const containsCjk = (value: unknown) => /[\u3400-\u9fff]/u.test(String(value ?? ''))

function englishError(value: unknown, fallback: string): string {
  const text = String(value ?? '').trim()

  return text && !containsCjk(text) ? text : fallback
}

const fieldGuide = [
  { field: 'sex', label: 'Sex', range: 'Male / Female' },
  { field: 'age', label: 'Age', range: '60–100' },
  { field: 'night_bed_exits', label: 'Night-time bed exits', range: '0–8' },
  { field: 'night_activity_duration_min', label: 'Night-time activity duration (minutes)', range: '0–120' },
  { field: 'past_falls', label: 'Past falls', range: '0–5' },
  { field: 'mobility_score', label: 'Mobility score', range: '1–10' },
  { field: 'high_risk_medication', label: 'High-risk medication', range: 'Yes / No' },
  { field: 'cognitive_impairment', label: 'Cognitive impairment', range: '0 / 1 / 2' },
  { field: 'polypharmacy_count', label: 'Number of medications', range: '0–14' },
  { field: 'orthostatic_hypotension', label: 'Orthostatic hypotension', range: 'Yes / No' },
  { field: 'tug_seconds', label: 'Timed Up and Go (TUG) test (seconds)', range: '8–31.9' },
  { field: 'days_since_last_fall', label: 'Days since last fall (optional)', range: '0–365' },
  { field: 'syncopal_fall', label: 'Syncope-related fall (optional)', range: 'Yes / No' },
  { field: 'fall_cluster_30d', label: 'Recurrent falls within 30 days (optional)', range: 'Yes / No' },
]

function reset() {
  file.value = null
  loading.value = false
  downloadingTemplate.value = false
  error.value = ''
  result.value = null
  guidePanel.value = null
}

function openDialog() {
  reset()
  dialog.value = true
}

async function downloadTemplate() {
  downloadingTemplate.value = true
  error.value = ''

  try {
    const response = await fetch(templateHref.value)
    if (!response.ok)
      throw new Error(`Template download failed (HTTP ${response.status})`)

    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'fall-risk-import-template.xlsx'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  catch (cause: any) {
    const downloadError = cause instanceof Error ? cause : new Error(String(cause))

    error.value = englishError(downloadError.message, 'Template download failed. Check that the backend service is running.')
    emit('error', downloadError)
  }
  finally {
    downloadingTemplate.value = false
  }
}

function parseErrorPayload(payload: unknown, fallback: string) {
  if (typeof payload === 'string' && payload.trim())

    return englishError(payload, fallback)

  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail?: unknown }).detail
    if (typeof detail === 'string' && detail.trim())

      return englishError(detail, fallback)
  }

  return fallback
}

async function submit() {
  const fileToUpload = selectedFile.value
  if (!fileToUpload) {
    error.value = 'Please select an Excel or CSV file first.'

    return
  }

  const extension = fileToUpload.name.toLowerCase().split('.').pop()
  if (!extension || !['xlsx', 'xlsm', 'csv'].includes(extension)) {
    error.value = 'Unsupported file format. Upload an .xlsx, .xlsm, or .csv file.'

    return
  }

  const maxBytes = props.maxFileSizeMb * 1024 * 1024
  if (fileToUpload.size > maxBytes) {
    error.value = `File must be no larger than ${props.maxFileSizeMb} MB.`

    return
  }

  loading.value = true
  error.value = ''
  result.value = null

  try {
    const body = new FormData()

    body.append('file', fileToUpload)

    const response = await fetch(endpoint.value, {
      method: 'POST',
      body,
    })

    const contentType = response.headers.get('content-type') || ''

    const payload: unknown = contentType.includes('application/json')
      ? await response.json()
      : await response.text()

    if (!response.ok)
      throw new Error(parseErrorPayload(payload, `Batch import failed (HTTP ${response.status})`))

    const normalized: BatchImportResult = {
      success: Number((payload as any)?.success || 0),
      skipped: Number((payload as any)?.skipped || 0),
      total: Number((payload as any)?.total || 0),
      errors: Array.isArray((payload as any)?.errors) ? (payload as any).errors : [],
      message: typeof (payload as any)?.message === 'string' ? (payload as any).message : undefined,
    }

    result.value = normalized

    emit('uploaded', normalized)
  }
  catch (cause: any) {
    const uploadError = cause instanceof Error ? cause : new Error(String(cause))

    error.value = englishError(uploadError.message, 'Upload failed. Check that the backend service is running.')
    emit('error', uploadError)
  }
  finally {
    loading.value = false
  }
}
</script>

<template>
  <VBtn
    color="success"
    variant="tonal"
    prepend-icon="tabler-file-upload"
    data-testid="batch-import-button"
    @click="openDialog"
  >
    Batch import data
  </VBtn>

  <VDialog
    v-model="dialog"
    max-width="680"
    scrollable
    :persistent="loading"
  >
    <VCard class="batch-import">
      <VCardItem>
        <template #prepend>
          <VAvatar
            color="success"
            variant="tonal"
            rounded
          >
            <VIcon icon="tabler-file-spreadsheet" />
          </VAvatar>
        </template>
        <VCardTitle>Batch import risk assessment data</VCardTitle>
        <VCardSubtitle>Batch import resident assessments</VCardSubtitle>
        <template #append>
          <VBtn
            icon="tabler-x"
            variant="text"
            aria-label="Close batch import"
            :disabled="loading"
            @click="dialog = false"
          />
        </template>
      </VCardItem>

      <VDivider />

      <VCardText class="pa-6">
        <div class="batch-import__steps">
          <div><span>1</span> Download template</div>
          <div><span>2</span> Enter data</div>
          <div><span>3</span> Upload and predict</div>
        </div>

        <p class="text-body-2 text-medium-emphasis mb-4">
          Enter one resident per row. Supported formats: <strong>.xlsx</strong>, <strong>.xlsm</strong>, and <strong>.csv</strong>. Enter numeric values within the ranges shown in the template.
        </p>

        <VBtn
          type="button"
          variant="tonal"
          color="primary"
          prepend-icon="tabler-download"
          :loading="downloadingTemplate"
          :disabled="loading || downloadingTemplate"
          class="mb-5"
          @click="downloadTemplate"
        >
          Download Excel template
        </VBtn>

        <VExpansionPanels
          v-model="guidePanel"
          variant="accordion"
          class="mb-5"
        >
          <VExpansionPanel title="View field requirements / Column guide">
            <VExpansionPanelText>
              <VTable
                density="compact"
                class="batch-import__guide"
              >
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Description</th>
                    <th>Allowed range</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="item in fieldGuide"
                    :key="item.field"
                  >
                    <td class="text-caption">
                      {{ item.field }}
                    </td>
                    <td>
                      {{ item.label }}
                    </td>
                    <td>
                      {{ item.range }}
                    </td>
                  </tr>
                </tbody>
              </VTable>
            </VExpansionPanelText>
          </VExpansionPanel>
        </VExpansionPanels>

        <VFileInput
          v-model="file"
          label="Upload completed file"
          placeholder="Choose an .xlsx, .xlsm, or .csv file"
          accept=".xlsx,.xlsm,.csv,text/csv"
          prepend-icon="tabler-cloud-upload"
          show-size
          clearable
          :disabled="loading"
          data-testid="batch-import-file"
        />

        <VAlert
          v-if="error"
          color="error"
          variant="tonal"
          class="mt-4"
        >
          {{ error }}
        </VAlert>

        <VAlert
          v-if="result"
          :color="resultColor"
          variant="tonal"
          class="mt-4"
        >
          <div class="font-weight-medium mb-1">
            {{ result.skipped ? 'Batch prediction complete (some rows skipped)' : 'Batch prediction complete' }}
          </div>
          <div>
            Imported <strong>{{ result.success }}</strong> records successfully; skipped <strong>{{ result.skipped }}</strong> ({{ result.total }} total).
          </div>
          <ul
            v-if="visibleErrors.length"
            class="batch-import__errors mt-2"
          >
            <li
              v-for="(rowError, index) in visibleErrors"
              :key="`${index}-${rowError}`"
            >
              {{ rowError }}
            </li>
          </ul>
          <div
            v-if="remainingErrors"
            class="text-caption mt-1"
          >
            {{ remainingErrors }} more errors hidden.
          </div>
        </VAlert>
      </VCardText>

      <VDivider />

      <VCardActions class="pa-5">
        <VSpacer />
        <VBtn
          variant="text"
          :disabled="loading"
          @click="dialog = false"
        >
          Cancel
        </VBtn>
        <VBtn
          color="success"
          prepend-icon="tabler-player-play"
          :loading="loading"
          :disabled="!selectedFile"
          data-testid="batch-import-submit"
          @click="submit"
        >
          Upload and run prediction
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.batch-import__steps {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  margin-block-end: 20px;
  color: rgba(var(--v-theme-on-surface), 0.72);
  font-size: 0.875rem;
  font-weight: 600;
}

.batch-import__steps div {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.batch-import__steps span {
  display: inline-grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 50%;
  color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.12);
  font-size: 0.75rem;
}

.batch-import__errors {
  padding-inline-start: 1.2rem;
  font-size: 0.82rem;
}

.batch-import__guide {
  font-size: 0.8rem;
}

.batch-import__guide th,
.batch-import__guide td {
  white-space: nowrap;
}

@media (max-width: 600px) {
  .batch-import__steps {
    gap: 10px;
    font-size: 0.8rem;
  }
}
</style>
