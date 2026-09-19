<template>
  <div class="panel">
    <h3>📉 收敛曲线</h3>
    <div ref="chart" class="chart"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useOptimizationStore } from '../store/optimization'

const store = useOptimizationStore()
const chart = ref<HTMLDivElement>()
let instance: echarts.ECharts | null = null

function initChart() {
  if (!chart.value) return
  instance = echarts.init(chart.value)
  window.addEventListener('resize', () => instance?.resize())
}

function updateChart() {
  if (!instance || !store.result) return
  const path = store.currentPath()
  const data = path.map(p => [p.step, p.z])
  instance.setOption({
    backgroundColor: 'transparent',
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'value', name: '迭代步数', nameLocation: 'middle', nameGap: 25 },
    yAxis: { type: 'value', name: 'f(x,y)', nameLocation: 'middle', nameGap: 40 },
    series: [{
      type: 'line', data, smooth: true, symbol: 'none',
      lineStyle: { color: '#667eea', width: 2 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(102,126,234,0.3)' }, { offset: 1, color: 'rgba(102,126,234,0)' }
      ]) }
    }],
    animation: false
  })
}

onMounted(initChart)
watch(() => [store.result, store.animationStep], updateChart, { deep: true })
onUnmounted(() => { instance?.dispose(); instance = null })
</script>

<style scoped>
.panel { background:#fff; border-radius:8px; padding:16px; margin-top:16px; box-shadow:0 2px 8px rgba(0,0,0,.06) }
.panel h3 { margin-bottom:8px; color:#333; font-size:14px }
.chart { width:100%; height:280px }
</style>