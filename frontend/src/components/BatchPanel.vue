<template>
  <div class="batch-card">
    <div class="batch-header">
      <h3>🧪 批量试算</h3>
      <div class="batch-actions">
        <el-button size="small" @click="addRow">➕ 添加一组（取当前单组参数）</el-button>
        <el-button size="small" @click="copyLast" :disabled="!store.batchDraft.length">📋 复制末行</el-button>
        <el-button size="small" type="danger" plain @click="store.batchDraft = []" :disabled="!store.batchDraft.length">清空待算</el-button>
        <el-button type="primary" @click="submit" :loading="store.batchLoading" :disabled="!store.batchDraft.length">
          🚀 批量试算（{{ store.batchDraft.length }} 组）
        </el-button>
      </div>
    </div>

    <el-table :data="store.batchDraft" size="small" class="draft-table">
      <el-table-column type="index" label="#" width="45" />
      <el-table-column label="测试函数" min-width="150">
        <template #default="{ row }">
          <el-select v-model="row.functionId" size="small">
            <el-option v-for="f in TEST_FUNCTIONS" :key="f.id" :label="f.name" :value="f.id" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="算法" min-width="120">
        <template #default="{ row }">
          <el-select v-model="row.algorithm" size="small">
            <el-option v-for="a in ALGORITHMS" :key="a.id" :label="a.name" :value="a.id" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="初始X" min-width="95">
        <template #default="{ row }">
          <el-input-number v-model="row.x0" :min="-10" :max="10" :step="0.5" size="small" :controls="false" />
        </template>
      </el-table-column>
      <el-table-column label="初始Y" min-width="95">
        <template #default="{ row }">
          <el-input-number v-model="row.y0" :min="-10" :max="10" :step="0.5" size="small" :controls="false" />
        </template>
      </el-table-column>
      <el-table-column label="学习率" min-width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.learningRate" :min="0.001" :max="1" :step="0.01" :precision="3" size="small" :controls="false" />
        </template>
      </el-table-column>
      <el-table-column label="迭代" min-width="90">
        <template #default="{ row }">
          <el-input-number v-model="row.iterations" :min="10" :max="500" :step="10" size="small" :controls="false" />
        </template>
      </el-table-column>
      <el-table-column label="动量" min-width="90">
        <template #default="{ row }">
          <el-input-number v-model="row.momentum" :min="0" :max="0.99" :step="0.1" :precision="2" size="small" :controls="false" />
        </template>
      </el-table-column>
      <el-table-column label="温度" min-width="90">
        <template #default="{ row }">
          <el-input-number v-model="row.temperature" :min="1" :max="1000" :step="10" size="small" :controls="false" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70" fixed="right">
        <template #default="{ $index }">
          <el-button size="small" type="danger" text @click="store.batchDraft.splice($index, 1)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>点击「添加一组」把参数组合加入批量列表，可一次提交多组</template>
    </el-table>

    <el-alert v-if="store.batchMeta" class="batch-meta" type="info" :closable="false" show-icon>
      <template #title>
        最近一批：提交 {{ store.batchMeta.total }} 组（去重 {{ store.batchMeta.deduplicated }} 组）·
        成功 {{ store.batchMeta.succeeded }} · 失败 {{ store.batchMeta.failed }} ·
        {{ formatTime(store.batchMeta.submittedAt) }}
      </template>
      重复提交相同组合只保留一次结果；结果已保存在本地，刷新页面不会丢失。
    </el-alert>

    <div class="result-header" v-if="store.batchResults.length">
      <h3>📊 试算结果（{{ store.batchResults.length }} 组）</h3>
      <el-button size="small" type="danger" text @click="confirmClear">清除全部结果</el-button>
    </div>
    <el-table v-if="store.batchResults.length" :data="store.batchResults" size="small" :row-class-name="rowClass">
      <el-table-column type="index" label="#" width="45" />
      <el-table-column label="测试函数" min-width="140">
        <template #default="{ row }">{{ functionName(row.params.functionId) }}</template>
      </el-table-column>
      <el-table-column label="算法" min-width="100">
        <template #default="{ row }">{{ algorithmName(row.params.algorithm) }}</template>
      </el-table-column>
      <el-table-column label="初始点" min-width="110">
        <template #default="{ row }">({{ row.params.x0 }}, {{ row.params.y0 }})</template>
      </el-table-column>
      <el-table-column label="学习率" width="80">
        <template #default="{ row }">{{ row.params.learningRate }}</template>
      </el-table-column>
      <el-table-column label="迭代" width="60">
        <template #default="{ row }">{{ row.params.iterations }}</template>
      </el-table-column>
      <el-table-column label="最终点" min-width="130">
        <template #default="{ row }">{{ fmtPoint(row.finalPoint) }}</template>
      </el-table-column>
      <el-table-column label="最终值" min-width="110">
        <template #default="{ row }">{{ fmtNum(row.finalValue) }}</template>
      </el-table-column>
      <el-table-column label="收敛" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'ok'" :type="row.converged ? 'success' : 'warning'" size="small">
            {{ row.converged ? '已收敛' : '未收敛' }}
          </el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="状态 / 失败原因" min-width="180">
        <template #default="{ row }">
          <span v-if="row.status === 'ok'" class="ok-text">✅ 成功</span>
          <span v-else class="error-text">❌ {{ row.error }}</span>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="暂无批量试算结果，提交后将在此并排展示每组的最终取值与收敛情况" />
  </div>
</template>

<script setup lang="ts">
import { ElMessageBox } from 'element-plus'
import { useOptimizationStore } from '../store/optimization'
import { TEST_FUNCTIONS, ALGORITHMS } from '../types'
import type { BatchItemResult } from '../types'

const store = useOptimizationStore()

function addRow() {
  store.batchDraft.push({ ...store.form })
}
function copyLast() {
  const last = store.batchDraft[store.batchDraft.length - 1]
  if (last) store.batchDraft.push({ ...last })
}
function submit() {
  store.runBatch(store.batchDraft.map(r => ({ ...r })))
}

function functionName(id: string) {
  return TEST_FUNCTIONS.find(f => f.id === id)?.name ?? id
}
function algorithmName(id: string) {
  return ALGORITHMS.find(a => a.id === id)?.name ?? id
}
function fmtNum(v?: number) {
  if (v === undefined || v === null || Number.isNaN(v)) return '—'
  const a = Math.abs(v)
  if (a >= 1e6 || (a > 0 && a < 1e-4)) return v.toExponential(3)
  return String(Number(v.toFixed(6)))
}
function fmtPoint(p?: [number, number]) {
  return p ? `(${fmtNum(p[0])}, ${fmtNum(p[1])})` : '—'
}
function formatTime(t: number) {
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}
function rowClass({ row }: { row: BatchItemResult }) {
  return row.status === 'error' ? 'error-row' : ''
}
async function confirmClear() {
  try {
    await ElMessageBox.confirm('确定清除全部批量试算结果？此操作不可恢复。', '清除结果', { type: 'warning' })
    store.clearBatch()
  } catch { /* 用户取消 */ }
}
</script>

<style scoped>
.batch-card { background:#fff; border-radius:8px; padding:16px 20px; box-shadow:0 2px 8px rgba(0,0,0,.06) }
.batch-header { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:12px }
.batch-header h3, .result-header h3 { color:#333; font-size:14px }
.batch-actions { display:flex; gap:8px; flex-wrap:wrap }
.draft-table { margin-bottom:12px }
.batch-meta { margin-bottom:12px }
.result-header { display:flex; justify-content:space-between; align-items:center; margin:8px 0 }
.ok-text { color:#67c23a }
.error-text { color:#f56c6c }
:deep(.error-row) { background:#fef0f0 }
:deep(.el-input-number .el-input__inner) { text-align:left }
</style>
