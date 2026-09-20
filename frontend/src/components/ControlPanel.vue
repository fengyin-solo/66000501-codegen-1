<template>
  <div class="control-card">
    <el-form :model="store.form" inline>
      <el-form-item label="测试函数">
        <el-select v-model="store.form.functionId" style="width:180px">
          <el-option v-for="f in TEST_FUNCTIONS" :key="f.id" :label="f.name" :value="f.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="算法">
        <el-select v-model="store.form.algorithm" style="width:150px">
          <el-option v-for="a in ALGORITHMS" :key="a.id" :label="a.name" :value="a.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="初始X">
        <el-input-number v-model="store.form.x0" :min="-10" :max="10" :step="0.5" size="small" />
      </el-form-item>
      <el-form-item label="初始Y">
        <el-input-number v-model="store.form.y0" :min="-10" :max="10" :step="0.5" size="small" />
      </el-form-item>
      <el-form-item label="学习率">
        <el-input-number v-model="store.form.learningRate" :min="0.001" :max="1" :step="0.01" :precision="3" size="small" />
      </el-form-item>
      <el-form-item label="迭代">
        <el-input-number v-model="store.form.iterations" :min="10" :max="500" :step="10" size="small" />
      </el-form-item>
      <el-form-item label="动量" v-if="store.form.algorithm==='gradient_descent'">
        <el-input-number v-model="store.form.momentum" :min="0" :max="0.99" :step="0.1" :precision="1" size="small" />
      </el-form-item>
      <el-form-item label="温度" v-if="store.form.algorithm==='simulated_annealing'">
        <el-input-number v-model="store.form.temperature" :min="1" :max="1000" :step="10" size="small" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="run" :loading="store.loading">🚀 开始优化</el-button>
      </el-form-item>
    </el-form>

    <div class="animation-bar" v-if="store.result">
      <div class="anim-controls">
        <el-button size="small" @click="store.playAnimation" :disabled="store.isPlaying">▶ 播放</el-button>
        <el-button size="small" @click="store.pauseAnimation" :disabled="!store.isPlaying">⏸ 暂停</el-button>
        <el-button size="small" @click="store.resetAnimation">⏹ 重置</el-button>
      </div>
      <el-slider v-model="animStep" :min="0" :max="maxStep" @input="onSlider" style="flex:1;margin:0 20px" />
      <span class="step-text">步 {{ animStep }}/{{ maxStep }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useOptimizationStore } from '../store/optimization'
import { TEST_FUNCTIONS, ALGORITHMS } from '../types'
const store = useOptimizationStore()

// 直接读写 store：切到批量模式再切回时，滑块仍停留在原动画进度
const animStep = computed({
  get: () => store.animationStep,
  set: (v: number) => store.setStep(v)
})
const maxStep = computed(() => Math.max(0, (store.result?.path.length || 1) - 1))

function run() { store.runOptimization({ ...store.form } as any) }
function onSlider() { store.pauseAnimation() }
</script>

<style scoped>
.control-card { background:#fff; border-radius:8px; padding:16px 20px; box-shadow:0 2px 8px rgba(0,0,0,.06); margin-bottom:16px }
.animation-bar { display:flex; align-items:center; margin-top:12px; padding-top:12px; border-top:1px solid #eee }
.anim-controls { display:flex; gap:6px }
.step-text { font-size:13px; color:#666; white-space:nowrap }
</style>
