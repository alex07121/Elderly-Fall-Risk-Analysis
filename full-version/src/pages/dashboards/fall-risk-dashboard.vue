<script setup lang="ts">
import FallRiskStats from '@/views/dashboards/fall-risk/FallRiskStats.vue'
import FallRiskDistribution from '@/views/dashboards/fall-risk/FallRiskDistribution.vue'
import FallRiskTable from '@/views/dashboards/fall-risk/FallRiskTable.vue'
import FallRiskBatchImport from '@/views/dashboards/fall-risk/FallRiskBatchImport.vue'

definePage({
  meta: {
    public: true,
  },
})

// Increment after deleting records to trigger all child components to reload.
const refreshKey = ref(0)
const riskFocus = ref('')

provide('refreshKey', refreshKey)
provide('riskFocus', riskFocus)

function handleBatchImported() {
  // Stats, chart and table all subscribe to this shared key.
  refreshKey.value++
}

// When the URL includes :id (the detail page), render the child route;
// otherwise show the stats, chart, and table.
// Use the detail route's typed params so the parent can detect an optional
// child `:id` without falling back to the untyped union of every route.
const route = useRoute('dashboards-fall-risk-dashboard-id')
const isDetail = computed(() => !!route.params.id)

const router = useRouter()

const goToRoleSelection = () => {
  router.push('/')
}

const goToPersonalAssessment = () => {
  router.push('/dashboards/fall-risk')
}
</script>

<template>
  <RouterView v-if="isDetail" />

  <div
    v-else
    class="fall-risk-dashboard"
  >
    <VCard
      class="dashboard-hero mb-6"
      elevation="0"
    >
      <VCardText class="pa-5 pa-md-6">
        <div class="d-flex align-start justify-space-between flex-wrap ga-5">
          <div class="d-flex align-start ga-4">
            <VAvatar
              class="dashboard-hero__icon"
              color="primary"
              variant="tonal"
              size="52"
            >
              <VIcon
                icon="tabler-shield-heart"
                size="30"
              />
            </VAvatar>

            <div>
              <div class="text-overline text-primary font-weight-bold dashboard-hero__eyebrow">
                CARE TEAM · CAREGIVERS
              </div>
              <h1 class="text-h4 text-md-h3 font-weight-bold mb-2 dashboard-hero__title">
                Fall Risk Management Center
                <span class="dashboard-hero__title-en">Fall Risk Care Dashboard</span>
              </h1>
            </div>
          </div>

          <div class="dashboard-hero__actions">
            <div class="d-flex flex-wrap ga-2 justify-end">
            <VBtn
              variant="tonal"
              color="primary"
              prepend-icon="tabler-arrow-left"
              @click="goToRoleSelection"
            >
              Back to role selection
            </VBtn>
            <VBtn
              color="primary"
              prepend-icon="tabler-user-heart"
              @click="goToPersonalAssessment"
            >
              Open personal assessment
            </VBtn>
            <FallRiskBatchImport @uploaded="handleBatchImported" />
            </div>
          </div>
        </div>

        <VDivider class="my-4" />

        <div class="d-flex align-center flex-wrap ga-3 dashboard-hero__legend">
          <div class="dashboard-hero__legend-label">
            <VIcon icon="tabler-shield-check" size="18" color="primary" />
            <span>AI risk levels</span>
          </div>
          <VChip
            color="success"
            size="small"
            variant="tonal"
          >
            Low risk
          </VChip>
          <VChip
            color="warning"
            size="small"
            variant="tonal"
          >
            Medium risk
          </VChip>
          <VChip
            color="error"
            size="small"
            variant="tonal"
          >
            High risk
          </VChip>
        </div>
      </VCardText>
    </VCard>

    <FallRiskStats />

    <div class="dashboard-section-heading mt-6">
      <div>
        <div class="dashboard-section-heading__eyebrow">SITUATION ROOM · LIVE OVERVIEW</div>
        <h2 class="dashboard-section-heading__title">Risk distribution overview</h2>
      </div>
    </div>

    <VRow class="mt-3 dashboard-visuals">
      <VCol
        cols="12"
      >
        <FallRiskDistribution />
      </VCol>
    </VRow>

    <div class="dashboard-section-heading mt-6">
      <div>
        <div class="dashboard-section-heading__eyebrow">CARE QUEUE · FOLLOW-UP</div>
        <h2 class="dashboard-section-heading__title">Individual assessment records</h2>
      </div>
    </div>

    <VRow class="mt-3">
      <VCol cols="12">
        <FallRiskTable />
      </VCol>
    </VRow>
  </div>
</template>

<style scoped>
.dashboard-hero {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid rgba(var(--v-theme-primary), 0.16);
  background:
    linear-gradient(135deg, rgba(var(--v-theme-primary), 0.1), rgba(var(--v-theme-primary), 0.025) 58%, transparent),
    rgb(var(--v-theme-surface));
}

.dashboard-hero::after {
  position: absolute;
  inset-block-start: -80px;
  inset-inline-end: -60px;
  width: 220px;
  height: 220px;
  border: 1px solid rgba(var(--v-theme-primary), 0.12);
  border-radius: 50%;
  content: '';
  pointer-events: none;
}

.dashboard-hero__icon {
  flex: 0 0 auto;
}

.dashboard-hero__eyebrow {
  letter-spacing: 0.08em;
}

.dashboard-hero__title {
  line-height: 1.2;
}

.dashboard-hero__title-en {
  display: block;
  margin-block-start: 0.35rem;
  letter-spacing: 0.01em;
  color: rgba(var(--v-theme-on-surface), 0.58);
  font-size: 0.62em;
  font-weight: 500;
}

.dashboard-hero__actions {
  position: relative;
  z-index: 1;
}

.dashboard-hero__legend {
  position: relative;
  z-index: 1;
}

.dashboard-hero__legend-label {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  color: rgba(var(--v-theme-on-surface), 0.72);
  font-size: 0.82rem;
  font-weight: 650;
}

.dashboard-section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
}

.dashboard-section-heading__eyebrow {
  color: rgb(var(--v-theme-primary));
  font-size: 0.66rem;
  font-weight: 750;
  letter-spacing: 0.1em;
}

.dashboard-section-heading__title {
  margin: 0.25rem 0 0;
  color: rgb(var(--v-theme-on-surface));
  font-size: 1.15rem;
  font-weight: 750;
}

.fall-risk-dashboard {
  max-inline-size: 1480px;
  margin-inline: auto;
  padding-block-end: 1.5rem;
}

.dashboard-visuals :deep(.v-col) {
  display: flex;
  align-items: flex-start;
}

.dashboard-visuals :deep(.v-card) {
  width: 100%;
}

@media (max-width: 600px) {
  .dashboard-hero {
    border-radius: 15px;
  }

  .dashboard-hero__title-en {
    display: none;
  }

  .dashboard-hero__title {
    font-size: 1.55rem !important;
  }

  .dashboard-hero__actions {
    width: 100%;
  }

  .dashboard-hero__actions .v-btn {
    flex: 1 1 100%;
  }

  .dashboard-hero__actions > .d-flex {
    width: 100%;
  }

  .dashboard-hero__actions > .d-flex > * {
    flex: 1 1 100%;
  }

  .dashboard-section-heading {
    display: block;
  }
}
</style>
