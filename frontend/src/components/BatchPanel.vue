<template>
  <div class="batch-layout">
    <section class="editor-card">
      <div class="card-head">
        <h3>📋 参数组合（{{ rows.length }} 组）</h3>
        <div class="head-actions">
          <el-button size="small" @click="addRow">➕ 新增一组</el-button>
          <el-button size="small" @click="fillExamples">✨ 示例三组</el-button>
        </div>
      </div>

      <el-table :data="rows" size="small" border stripe style="width:100%" max-height="340">
        <el-table-column type="index" label="#" width="42" align="center" />
        <el-table-column label="测试函数" width="170">
          <template #default="{ row }">
            <el-select v-model="row.functionId" size="small">
              <el-option v-for="f in TEST_FUNCTIONS" :key="f.id" :label="f.name" :value="f.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="算法" width="135">
          <template #default="{ row }">
            <el-select v-model="row.algorithm" size="small">
              <el-option v-for="a in ALGORITHMS" :key="a.id" :label="a.name" :value="a.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="初始X" width="105">
          <template #default="{ row }">
            <el-input-number v-model="row.x0" :min="-10" :max="10" :step="0.5" size="small" controls-position="right" style="width:95px" />
          </template>
        </el-table-column>
        <el-table-column label="初始Y" width="105">
          <template #default="{ row }">
            <el-input-number v-model="row.y0" :min="-10" :max="10" :step="0.5" size="small" controls-position="right" style="width:95px" />
          </template>
        </el-table-column>
        <el-table-column label="学习率" width="115">
          <template #default="{ row }">
            <el-input-number v-model="row.learningRate" :min="0.001" :max="1" :step="0.01" :precision="3" size="small" controls-position="right" style="width:105px" />
          </template>
        </el-table-column>
        <el-table-column label="迭代" width="100">
          <template #default="{ row }">
            <el-input-number v-model="row.iterations" :min="10" :max="500" :step="10" size="small" controls-position="right" style="width:90px" />
          </template>
        </el-table-column>
        <el-table-column label="动量" width="95" v-if="hasAlgo('gradient_descent')">
          <template #default="{ row }">
            <el-input-number v-if="row.algorithm==='gradient_descent'" v-model="row.momentum" :min="0" :max="0.99" :step="0.1" :precision="1" size="small" controls-position="right" style="width:80px" />
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="温度" width="100" v-if="hasAlgo('simulated_annealing')">
          <template #default="{ row }">
            <el-input-number v-if="row.algorithm==='simulated_annealing'" v-model="row.temperature" :min="1" :max="1000" :step="10" size="small" controls-position="right" style="width:85px" />
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="冷却系数" width="105" v-if="hasAlgo('simulated_annealing')">
          <template #default="{ row }">
            <el-input-number v-if="row.algorithm==='simulated_annealing'" v-model="row.coolingRate" :min="0.01" :max="0.99" :step="0.01" :precision="2" size="small" controls-position="right" style="width:90px" />
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right" align="center">
          <template #default="{ $index, row }">
            <el-button link type="primary" size="small" @click="copyRow(row)">复制</el-button>
            <el-button link type="danger" size="small" @click="rows.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="submit-bar">
        <el-button type="primary" :loading="batch.submitting" :disabled="!rows.length" @click="submitBatch">
          🧮 批量试算（{{ rows.length }} 组）
        </el-button>
        <span v-if="dedupHint" class="dedup-hint">⚠️ {{ dedupHint }}</span>
      </div>
    </section>

    <section class="result-card" v-if="batch.current">
      <div class="card-head">
        <h3>
          📊 试算结果
          <span class="batch-id">批次 {{ batch.current.id }}</span>
          <el-tag v-if="batch.current.status==='running'" type="warning" size="small" effect="plain">执行中</el-tag>
          <el-tag v-else type="success" size="small" effect="plain">已完成</el-tag>
          <el-tag v-if="lastSubmitExisted" type="info" size="small" effect="plain">相同批次已存在，直接展示原结果</el-tag>
        </h3>
        <div class="head-actions">
          <el-button size="small" :loading="refreshing" @click="batch.refresh(batch.current.id)">🔄 刷新进度</el-button>
        </div>
      </div>

      <el-progress v-if="batch.current.status==='running'" :percentage="progressPct" :stroke-width="10" :format="() => `${doneCount}/${batch.current!.items.length}`" style="margin:6px 0 12px" />
      <div v-else class="summary-line">
        共 {{ batch.current.summary.total }} 组 ·
        成功 <b>{{ batch.current.summary.succeeded }}</b> ·
        失败 <b :class="{ 'err-text': batch.current.summary.failed }">{{ batch.current.summary.failed }}</b> ·
        收敛 <b>{{ batch.current.summary.converged }}</b>
      </div>

      <el-table :data="batch.current.items" size="small" border stripe style="width:100%">
        <el-table-column prop="index" label="#" width="46" align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="参数" min-width="220">
          <template #default="{ row }">{{ describeParams(row.params) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status==='pending'" type="info" size="small">等待中</el-tag>
            <el-tag v-else-if="row.status==='running'" type="warning" size="small">计算中…</el-tag>
            <el-tag v-else-if="row.status==='success'" type="success" size="small">完成</el-tag>
            <el-tag v-else type="danger" size="small">失败</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最终点 (x, y)" width="180">
          <template #default="{ row }">
            <span v-if="row.finalPoint">({{ fmt(row.finalPoint[0]) }}, {{ fmt(row.finalPoint[1]) }})</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="最终取值 f" width="130" align="right">
          <template #default="{ row }">
            <span v-if="row.finalValue !== undefined">{{ fmt(row.finalValue) }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="迭代步数" width="90" align="center">
          <template #default="{ row }">{{ row.iterations ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="收敛" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status==='success'" :type="row.converged ? 'success' : 'info'" size="small">
              {{ row.converged ? '✓ 收敛' : '未收敛' }}
            </el-tag>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="收敛情况 / 失败原因" min-width="280">
          <template #default="{ row }">
            <span v-if="row.status==='failed'" class="err-text">⚠ {{ row.error }}</span>
            <span v-else-if="row.convergenceReason">{{ row.convergenceReason }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="history-card" v-if="batch.orderedBatches.length">
      <div class="card-head"><h3>🗂 历史批次（{{ batch.orderedBatches.length }}）</h3></div>
      <el-table :data="batch.orderedBatches" size="small" border style="width:100%">
        <el-table-column label="批次" min-width="120">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="batch.select(row.id)">
              {{ row.id }}<span v-if="batch.currentId===row.id"> ✓</span>
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="170">
          <template #default="{ row }">{{ new Date(row.createdAt * 1000).toLocaleString('zh-CN', { hour12: false }) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status==='running' ? 'warning' : 'success'" size="small">
              {{ row.status==='running' ? '执行中' : '完成' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="成功/失败" width="100" align="center">
          <template #default="{ row }">{{ row.summary.succeeded }}/{{ row.summary.failed }}</template>
        </el-table-column>
        <el-table-column label="收敛数" width="80" align="center" prop="summary.converged" />
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="batch.remove(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useBatchStore } from '../store/batch'
import { TEST_FUNCTIONS, ALGORITHMS } from '../types'
import type { OptimizationParams } from '../types'

const batch = useBatchStore()

interface EditableRow {
  algorithm: string
  functionId: string
  x0: number
  y0: number
  learningRate: number
  iterations: number
  momentum: number
  temperature: number
  coolingRate: number
  [key: string]: string | number
}

function makeRow(overrides: Partial<EditableRow> = {}): EditableRow {
  const row: EditableRow = {
    algorithm: 'gradient_descent', functionId: 'rosenbrock',
    x0: -1.5, y0: 2.5, learningRate: 0.01, iterations: 100,
    momentum: 0.9, temperature: 100, coolingRate: 0.95
  }
  return Object.assign(row, overrides)
}

const rows = ref<EditableRow[]>([
  makeRow({ x0: -1.5, y0: 2.5 }),
  makeRow({ x0: 0.5, y0: 0.5, learningRate: 0.02 }),
])
const lastSubmitExisted = ref(false)
const refreshing = ref(false)

function addRow() { rows.value.push(makeRow()) }
function copyRow(row: EditableRow) { rows.value.push(makeRow({ ...row })) }
function fillExamples() {
  rows.value = [
    makeRow({ x0: -1.5, y0: 2.5, learningRate: 0.01 }),
    makeRow({ x0: 0.0, y0: 0.0, learningRate: 0.05 }),
    makeRow({ algorithm: 'simulated_annealing', x0: -2, y0: 2, temperature: 200, coolingRate: 0.97 }),
  ]
}

function hasAlgo(id: string) { return rows.value.some(r => r.algorithm === id) }

function signature(r: EditableRow) {
  return JSON.stringify([
    r.algorithm, r.functionId, r.x0, r.y0, r.learningRate, r.iterations,
    r.momentum, r.temperature, r.coolingRate
  ])
}

const dedupHint = computed(() => {
  const seen = new Set<string>()
  for (const r of rows.value) {
    const s = signature(r)
    if (seen.has(s)) return '存在完全相同的重复行，提交时会自动折叠为一组'
    seen.add(s)
  }
  return ''
})

const doneCount = computed(() =>
  batch.current ? batch.current.items.filter(i => i.status === 'success' || i.status === 'failed').length : 0
)
const progressPct = computed(() => {
  if (!batch.current) return 0
  return Math.round(doneCount.value / batch.current.items.length * 100)
})

async function submitBatch() {
  // 前端折叠同一批内的完全重复组合（服务端按内容指纹做最终去重）
  const seen = new Set<string>()
  const combos: OptimizationParams[] = []
  for (const r of rows.value) {
    const s = signature(r)
    if (seen.has(s)) continue
    seen.add(s)
    combos.push({ ...r } as unknown as OptimizationParams)
  }
  const data = await batch.submit(combos)
  if (data) {
    lastSubmitExisted.value = !!data.existed
    ElMessage[data.existed ? 'info' : 'success'](
      data.existed ? '该批组合之前已提交过，直接展示已有结果' : `批量任务已提交（${combos.length} 组）`
    )
  }
}

const fnName = (id: string) => TEST_FUNCTIONS.find(f => f.id === id)?.name || id
const algoName = (id: string) => ALGORITHMS.find(a => a.id === id)?.name || id

function describeParams(p: OptimizationParams) {
  const base = `${fnName(p.functionId)} / ${algoName(p.algorithm)} · (${p.x0}, ${p.y0}) · lr=${p.learningRate} · n=${p.iterations}`
  if (p.algorithm === 'gradient_descent') return `${base} · m=${p.momentum ?? 0.9}`
  if (p.algorithm === 'simulated_annealing') return `${base} · T=${p.temperature ?? 100} · c=${p.coolingRate ?? 0.95}`
  return base
}

function fmt(v: number) {
  if (!isFinite(v)) return String(v)
  return Math.abs(v) >= 1e5 || (v !== 0 && Math.abs(v) < 1e-4) ? v.toExponential(3) : v.toFixed(4)
}
</script>

<style scoped>
.batch-layout { display:flex; flex-direction:column; gap:16px }
.editor-card, .result-card, .history-card { background:#fff; border-radius:8px; padding:16px 20px; box-shadow:0 2px 8px rgba(0,0,0,.06) }
.card-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; flex-wrap:wrap; gap:8px }
.card-head h3 { font-size:14px; color:#333; display:flex; align-items:center; gap:8px }
.head-actions { display:flex; gap:8px }
.batch-id { font-family:monospace; font-weight:normal; color:#909399; font-size:12px }
.submit-bar { margin-top:12px; display:flex; align-items:center; gap:12px }
.dedup-hint { font-size:12px; color:#e6a23c }
.summary-line { font-size:13px; color:#555; margin-bottom:10px }
.muted { color:#c0c4cc }
.err-text { color:#f56c6c }
</style>
