<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-row">
        <div>
          <h1>📐 数值优化算法逐帧可视化教学平台</h1>
          <p class="subtitle">梯度下降 · 牛顿法 · 共轭梯度 · 模拟退火 | 2D等高线 + 3D曲面</p>
        </div>
        <el-radio-group v-model="mode" size="large" @change="onModeChange">
          <el-radio-button label="single">🎯 单组试算</el-radio-button>
          <el-radio-button label="batch">🧮 批量试算</el-radio-button>
        </el-radio-group>
      </div>
    </header>
    <main class="app-main">
      <!-- 单组与批量视图同时挂载、仅切换显隐：模式切换不会冲掉单组结果与动画进度 -->
      <div v-show="mode==='single'" class="pane-single">
        <ControlPanel />
        <div class="vis-grid" v-if="store.result">
          <div class="vis-item"><ContourPlot /></div>
          <div class="vis-item"><Surface3D /></div>
        </div>
        <ConvergenceChart v-if="store.result" />
      </div>
      <div v-show="mode==='batch'" class="pane-batch">
        <BatchPanel />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import ControlPanel from './components/ControlPanel.vue'
import ContourPlot from './components/ContourPlot.vue'
import Surface3D from './components/Surface3D.vue'
import ConvergenceChart from './components/ConvergenceChart.vue'
import BatchPanel from './components/BatchPanel.vue'
import { useOptimizationStore } from './store/optimization'
import { useBatchStore } from './store/batch'

const store = useOptimizationStore()
const batch = useBatchStore()
const mode = batch.mode

function onModeChange(m: string) { batch.setMode(m as 'single' | 'batch') }

onMounted(async () => {
  batch.startPolling()
  // 刷新后：本地快照已在 store 构造时载入，默认打开最新一批并与服务端对账
  if (batch.orderedBatches.length) {
    if (!batch.currentId) batch.select(batch.orderedBatches[0].id)
    await Promise.all(batch.orderedBatches.map(b => batch.refresh(b.id)))
  }
})
onUnmounted(() => batch.stopPolling())
</script>

<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f6fa}
.app-container{min-height:100vh}
.app-header{background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);color:#fff;padding:20px 40px}
.header-row{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap}
.app-header h1{font-size:1.6rem}
.subtitle{opacity:.8;margin-top:4px;font-size:.85rem}
.app-main{padding:16px 40px}
.vis-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
</style>
