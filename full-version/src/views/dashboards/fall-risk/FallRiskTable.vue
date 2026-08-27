<script setup lang="ts">
import { apiDelete, apiGet, apiPost } from './useFallRiskApi'

const headers = [
  { title: 'Resident', key: 'resident' },
  { title: 'Risk', key: 'fall_risk_level' },
  { title: 'Age / Sex', key: 'age_sex' },
  { title: 'Assessed', key: 'created_at' },
  { title: 'Actions', key: 'actions', sortable: false },
]

const itemsPerPage = ref(10)
const page = ref(1)
const riskFilter = ref('')
const items = ref<any[]>([])
const totalItems = ref(0)
const loading = ref(false)
const error = ref('')
const selected = ref<any[]>([])
const containsCjk = (value: unknown) => /[\u3400-\u9fff]/u.test(String(value ?? ''))

function englishText(value: unknown, fallback: string): string {
  const text = String(value ?? '').trim()

  return text && !containsCjk(text) ? text : fallback
}

function englishError(value: unknown): string {
  const text = String(value ?? '').trim()

  return text && !containsCjk(text) ? text : 'The request could not be completed. Check the backend connection and try again.'
}

const riskOptions = [
  { title: 'High risk', value: 'HIGH' },
  { title: 'Medium risk', value: 'MEDIUM' },
  { title: 'Low risk', value: 'LOW' },
]

async function loadItems() {
  loading.value = true
  error.value = ''
  try {
    const data = await apiGet<any>('/assessments', {
      page: page.value,
      itemsPerPage: itemsPerPage.value,
      risk_level: riskFilter.value || undefined,
    })
    items.value = data.items ?? []
    totalItems.value = data.total ?? 0
  }
  catch (e: any) {
    error.value = englishError(e?.message || String(e))
  }
  finally {
    loading.value = false
  }
}

onMounted(loadItems)

watch([page, itemsPerPage, riskFilter], loadItems)

const refreshKey = inject<Ref<number>>('refreshKey', ref(0))
watch(refreshKey, loadItems)

const riskFocus = inject<Ref<string>>('riskFocus', ref(''))
watch(riskFocus, value => {
  if (riskFilter.value === value)
    return

  page.value = 1
  riskFilter.value = value
})

watch(riskFilter, value => {
  if (riskFocus.value !== value)
    riskFocus.value = value
})

const router = useRouter()

function openDetail(id: number) {
  router.push(`/dashboards/fall-risk-dashboard/${id}`)
}

function formatDate(iso: string) {
  if (!iso)
    return '—'
  return new Date(iso).toLocaleString('en-US')
}

function shortResidentId(item: any) {
  const value = englishText(item.resident_id, `#${item.id}`)

  if (value.startsWith('P')) {
    const numericId = Number(value.slice(1))

    return Number.isFinite(numericId) ? `P${numericId}` : 'P'
  }

  return value.length > 4 ? value.slice(-4) : value
}

function residentDisplayId(item: any) {
  return englishText(item.resident_id, `Assessment #${item.id}`)
}

function riskColor(level: string) {
  if (level === 'HIGH')
    return 'error'
  if (level === 'MEDIUM')
    return 'warning'
  return 'success'
}

function riskLabel(level: string) {
  return {
    HIGH: 'High risk',
    MEDIUM: 'Medium risk',
    LOW: 'Low risk',
  }[level] || 'Unknown risk'
}

function sexLabel(value: unknown) {
  const normalized = String(value ?? '').trim().toUpperCase()

  return normalized === 'F' || normalized === 'FEMALE'
    ? 'Female'
    : normalized === 'M' || normalized === 'MALE' ? 'Male' : '—'
}

async function deleteOne(id: number) {
  if (!window.confirm('Delete this assessment record?'))
    return
  try {
    await apiDelete(`/assessments/${id}`)
    refreshKey.value++
  }
  catch (e: any) {
    error.value = englishError(e?.message || String(e))
  }
}

async function deleteSelected() {
  if (!selected.value.length)
    return
  if (!window.confirm(`Delete ${selected.value.length} selected record(s)?`))
    return
  try {
    await apiPost('/assessments/batch-delete', { ids: selected.value })
    selected.value = []
    page.value = 1
    refreshKey.value++
  }
  catch (e: any) {
    error.value = englishError(e?.message || String(e))
  }
}

async function clearAll() {
  if (!window.confirm('Delete ALL assessment records? This cannot be undone.'))
    return
  try {
    await apiDelete('/assessments/all')
    selected.value = []
    page.value = 1
    refreshKey.value++
  }
  catch (e: any) {
    error.value = englishError(e?.message || String(e))
  }
}
</script>

<template>
  <VCard class="risk-table" elevation="0">
    <VCardItem class="risk-table__header d-flex flex-wrap justify-space-between gap-4">
      <div>
        <div class="d-flex align-center flex-wrap ga-2">
          <VCardTitle class="pa-0">Resident assessment queue</VCardTitle>
          <VChip
            v-if="totalItems"
            color="primary"
            variant="tonal"
            size="x-small"
          >
            {{ totalItems }} records
          </VChip>
        </div>
        <div class="text-caption text-medium-emphasis mt-1">
          Resident assessments · Select a row to view the explainable individual report
        </div>
      </div>

      <template #append>
        <div class="risk-table__filter">
          <VSelect
            v-model="riskFilter"
            :items="riskOptions"
            label="Risk level"
            aria-label="Filter by risk level"
            prepend-inner-icon="tabler-filter"
            clearable
            density="compact"
            hide-details
            variant="outlined"
          />
        </div>
      </template>
    </VCardItem>

    <VDivider />

    <div class="risk-table__toolbar d-flex flex-wrap gap-2 pa-4 pb-0">
      <VBtn
        color="error"
        variant="tonal"
        prepend-icon="tabler-trash"
        :disabled="!selected.length"
        @click="deleteSelected"
      >
        Delete selected ({{ selected.length }})
      </VBtn>

      <VBtn
        color="error"
        variant="outlined"
        prepend-icon="tabler-trash-x"
        :disabled="!totalItems"
        @click="clearAll"
      >
        Clear all
      </VBtn>
    </div>

    <VAlert
      v-if="error"
      color="error"
      variant="tonal"
      class="ma-4"
    >
      {{ error }}
    </VAlert>

    <div v-if="!error" class="risk-table__table-wrap">
      <VDataTableServer
        v-model="selected"
        v-model:items-per-page="itemsPerPage"
        v-model:page="page"
        :items="items"
        :items-length="totalItems"
        :headers="headers"
        :loading="loading"
        item-value="id"
        show-select
        class="text-no-wrap"
        @click:row="(_: any, row: any) => openDetail(row.item.id)"
      >
      <template #item.resident="{ item }">
        <div class="d-flex align-center gap-x-3">
          <VAvatar
            size="34"
            variant="tonal"
            :color="riskColor(item.fall_risk_level)"
          >
            <span class="text-caption font-weight-bold">{{ shortResidentId(item) }}</span>
          </VAvatar>
          <div>
            <span class="text-body-2 font-weight-medium">{{ residentDisplayId(item) }}</span>
            <div class="text-caption text-medium-emphasis">ID · {{ item.id }}</div>
          </div>
        </div>
      </template>

      <template #item.fall_risk_level="{ item }">
        <VChip
          :color="riskColor(item.fall_risk_level)"
          size="small"
          class="font-weight-medium"
        >
          {{ riskLabel(item.fall_risk_level) }}
        </VChip>
      </template>

      <template #item.age_sex="{ item }">
        <span class="text-body-2">{{ item.age }} / {{ sexLabel(item.sex) }}</span>
      </template>

      <template #item.created_at="{ item }">
        <span class="text-body-2">{{ formatDate(item.created_at) }}</span>
      </template>

      <template #item.actions="{ item }">
        <div class="d-flex gap-1">
          <VBtn
            icon
            size="small"
            variant="text"
            color="primary"
            aria-label="View assessment details"
            @click.stop="openDetail(item.id)"
          >
            <VIcon icon="tabler-eye" size="20" />
          </VBtn>

          <VBtn
            icon
            size="small"
            variant="text"
            color="error"
            aria-label="Delete assessment record"
            @click.stop="deleteOne(item.id)"
          >
            <VIcon icon="tabler-trash" size="20" />
          </VBtn>
        </div>
      </template>

      <template #bottom>
        <TablePagination
          v-model:page="page"
          :items-per-page="itemsPerPage"
          :total-items="totalItems"
        />
      </template>
      </VDataTableServer>
    </div>
  </VCard>
</template>

<style scoped>
.risk-table {
  height: 100%;
  overflow: hidden;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 18px;
}

.risk-table__header {
  min-height: 88px;
}

.risk-table__filter {
  inline-size: 230px;
}

.risk-table__table-wrap {
  overflow-x: auto;
}

.risk-table__table-wrap :deep(.v-data-table) {
  min-width: 690px;
}

.risk-table__table-wrap :deep(table) {
  width: 100%;
}

.risk-table__table-wrap :deep(.v-data-table__th) {
  color: rgba(var(--v-theme-on-surface), 0.58);
  font-size: 0.69rem;
  font-weight: 750;
  letter-spacing: 0.045em;
  text-transform: uppercase;
}

.risk-table__table-wrap :deep(.v-data-table__tr) {
  cursor: pointer;
  transition: background-color 160ms ease;
}

.risk-table__table-wrap :deep(.v-data-table__tr:hover) {
  background: rgba(var(--v-theme-primary), 0.035);
}

.risk-table__table-wrap :deep(.v-data-table__td),
.risk-table__table-wrap :deep(.v-data-table__th) {
  border-bottom-color: rgba(var(--v-theme-on-surface), 0.07) !important;
}

.risk-table__table-wrap :deep(.v-data-table-footer) {
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.07);
}

@media (max-width: 760px) {
  .risk-table__filter {
    inline-size: 100%;
  }

  .risk-table__header :deep(.v-card-item__append) {
    flex-basis: 100%;
  }

  .risk-table__table-wrap :deep(.v-data-table) {
    width: 100%;
    min-width: 0;
  }

  .risk-table__table-wrap :deep(table) {
    width: 100%;
    table-layout: fixed;
  }

  .risk-table__table-wrap :deep(.v-data-table__td),
  .risk-table__table-wrap :deep(.v-data-table__th) {
    overflow: hidden;
    white-space: normal !important;
  }

  .risk-table__table-wrap :deep(th:nth-child(1)),
  .risk-table__table-wrap :deep(td:nth-child(1)) {
    width: 36px !important;
    min-width: 36px !important;
    max-width: 36px !important;
    padding-inline: 0 !important;
  }

  .risk-table__table-wrap :deep(th:nth-child(2)),
  .risk-table__table-wrap :deep(td:nth-child(2)) {
    width: 40% !important;
    min-width: 0 !important;
  }

  .risk-table__table-wrap :deep(th:nth-child(3)),
  .risk-table__table-wrap :deep(td:nth-child(3)) {
    width: 31% !important;
    min-width: 0 !important;
  }

  .risk-table__table-wrap :deep(th:nth-child(6)),
  .risk-table__table-wrap :deep(td:nth-child(6)) {
    width: 29% !important;
    min-width: 0 !important;
  }

  .risk-table__table-wrap :deep(.v-data-table__td--select-row) {
    width: 36px !important;
    min-width: 36px !important;
    max-width: 36px !important;
    padding: 0 !important;
  }

  .risk-table__table-wrap :deep(.v-btn--icon) {
    width: 38px !important;
    height: 38px !important;
  }

  /* Keep resident, risk and actions visible on narrow screens. */
  .risk-table__table-wrap :deep(th:nth-child(4)),
  .risk-table__table-wrap :deep(td:nth-child(4)),
  .risk-table__table-wrap :deep(th:nth-child(5)),
  .risk-table__table-wrap :deep(td:nth-child(5)) {
    display: none;
  }

  .risk-table__table-wrap :deep(.v-data-table__td) {
    padding-inline: 0.45rem;
  }

  .risk-table__table-wrap :deep(.v-data-table__td:first-of-type) {
    padding-inline-start: 0.75rem;
  }
}
</style>
