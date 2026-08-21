<script setup lang="ts">
import FallRiskStats from '@/views/dashboards/fall-risk/FallRiskStats.vue'
import FallRiskDistribution from '@/views/dashboards/fall-risk/FallRiskDistribution.vue'
import FallRiskTable from '@/views/dashboards/fall-risk/FallRiskTable.vue'
</script>

<template>
  <div>
    <FallRiskStats />

    <VRow class="mt-4">
      <VCol
        cols="12"
        md="5"
      >
        <FallRiskDistribution />
      </VCol>

      <VCol
        cols="12"
        md="7"
      >
        <FallRiskTable />
      </VCol>
    </VRow>
  </div>
</template>
