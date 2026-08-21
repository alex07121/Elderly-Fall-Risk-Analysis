<script setup lang="ts">
import FallRiskStats from '@/views/dashboards/fall-risk/FallRiskStats.vue'
import FallRiskDistribution from '@/views/dashboards/fall-risk/FallRiskDistribution.vue'
import FallRiskTable from '@/views/dashboards/fall-risk/FallRiskTable.vue'

// 删除记录后 +1，触发所有子组件重新加载
const refreshKey = ref(0)
provide('refreshKey', refreshKey)

// 当 URL 携带 :id（detail 页面），渲染子路由；否则显示统计卡+图表+列表
const route = useRoute()
const isDetail = computed(() => !!route.params.id)
</script>

<template>
  <RouterView v-if="isDetail" />

  <div v-else>
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
