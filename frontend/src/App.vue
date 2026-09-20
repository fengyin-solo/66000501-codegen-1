<template>
  <div class="app-container">
    <header class="app-header">
      <h1>📐 数值优化算法逐帧可视化教学平台</h1>
      <p class="subtitle">梯度下降 · 牛顿法 · 共轭梯度 · 模拟退火 | 2D等高线 + 3D曲面</p>
    </header>
    <main class="app-main">
      <div class="mode-bar">
        <el-radio-group :model-value="store.mode" @change="store.setMode($event as 'single' | 'batch')">
          <el-radio-button value="single">🎯 单组试算</el-radio-button>
          <el-radio-button value="batch">🧪 批量试算</el-radio-button>
        </el-radio-group>
      </div>
      <template v-if="store.mode === 'single'">
        <ControlPanel />
        <div class="vis-grid" v-if="store.result">
          <div class="vis-item"><ContourPlot /></div>
          <div class="vis-item"><Surface3D /></div>
        </div>
        <ConvergenceChart v-if="store.result" />
      </template>
      <BatchPanel v-else />
    </main>
  </div>
</template>

<script setup lang="ts">
import ControlPanel from './components/ControlPanel.vue'
import ContourPlot from './components/ContourPlot.vue'
import Surface3D from './components/Surface3D.vue'
import ConvergenceChart from './components/ConvergenceChart.vue'
import BatchPanel from './components/BatchPanel.vue'
import { useOptimizationStore } from './store/optimization'
const store = useOptimizationStore()
</script>

<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f6fa}
.app-container{min-height:100vh}
.app-header{background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);color:#fff;padding:20px 40px}
.app-header h1{font-size:1.6rem}
.subtitle{opacity:.8;margin-top:4px;font-size:.85rem}
.app-main{padding:16px 40px}
.mode-bar{margin-bottom:16px}
.vis-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
</style>
