<script setup lang="ts">
import { apiGet } from './useFallRiskApi'

const headers = [
  { title: 'Resident', key: 'resident' },
  { title: 'Risk Level', key: 'fall_risk_level' },
  { title: 'Age / Sex', key: 'age_sex' },
  { title: 'Assessed At', key: 'created_at' },
]

const itemsPerPage = ref(10)
const page = ref(1)
const riskFilter = ref('')
const items = ref<any[]>([])
const totalItems = ref(0)
const loading = ref(false)
const error = ref('')

const riskOptions = ['HIGH', 'MEDIUM', 'LOW']

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
    error.value = e?.message || String(e)
  }
  finally {
    loading.value = false
  }
}

onMounted(loadItems)

watch([page, itemsPerPage, riskFilter], loadItems)

const router = useRouter()

function openDetail(id: number) {
  router.push(`/dashboards/fall-risk-dashboard/${id}`)
}

function formatDate(iso: string) {
  if (!iso)
    return '—'
  return new Date(iso).toLocaleString()
}

function riskColor(level: string) {
  if (level === 'HIGH')
    return 'error'
  if (level === 'MEDIUM')
    return 'warning'
  return 'success'
}
</script>

<template>
  <VCard>
    <VCardItem class="d-flex flex-wrap justify-space-between gap-4">
      <VCardTitle>Resident Assessments</VCardTitle>

      <template #append>
        <div style="inline-size: 200px;">
          <VSelect
            v-model="riskFilter"
            :items="riskOptions"
            placeholder="All risk levels"
            clearable
            density="compact"
          />
        </div>
      </template>
    </VCardItem>

    <VDivider />

    <VAlert
      v-if="error"
      color="error"
      variant="tonal"
      class="ma-4"
    >
      Failed to load: {{ error }}
    </VAlert>

    <VDataTableServer
      v-else
      v-model:items-per-page="itemsPerPage"
      v-model:page="page"
      :items="items"
      :items-length="totalItems"
      :headers="headers"
      :loading="loading"
      item-value="id"
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
            <span class="text-caption">{{ item.resident_id ?? `#${item.id}` }}</span>
          </VAvatar>
          <span class="text-body-2">{{ item.resident_id ?? `Assessment #${item.id}` }}</span>
        </div>
      </template>

      <template #item.fall_risk_level="{ item }">
        <VChip
          :color="riskColor(item.fall_risk_level)"
          size="small"
          class="font-weight-medium"
        >
          {{ item.fall_risk_level }}
        </VChip>
      </template>

      <template #item.age_sex="{ item }">
        <span class="text-body-2">{{ item.age }} / {{ item.sex ?? '—' }}</span>
      </template>

      <template #item.created_at="{ item }">
        <span class="text-body-2">{{ formatDate(item.created_at) }}</span>
      </template>

      <template #bottom>
        <TablePagination
          v-model:page="page"
          :items-per-page="itemsPerPage"
          :total-items="totalItems"
        />
      </template>
    </VDataTableServer>
  </VCard>
</template>
