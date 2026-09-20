import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { OptimizationParams, OptimizationResult, BatchItemResult, BatchRunMeta, BatchRunResponse } from '@/types'

const MODE_STORAGE_KEY = 'opt-mode-v1'
const BATCH_STORAGE_KEY = 'opt-batch-results-v1'

type RunMode = 'single' | 'batch'

function loadMode(): RunMode {
  return localStorage.getItem(MODE_STORAGE_KEY) === 'batch' ? 'batch' : 'single'
}

function loadBatchSnapshot(): { meta: BatchRunMeta | null; results: BatchItemResult[] } {
  try {
    const raw = localStorage.getItem(BATCH_STORAGE_KEY)
    if (!raw) return { meta: null, results: [] }
    const parsed = JSON.parse(raw)
    if (!parsed || !Array.isArray(parsed.results)) return { meta: null, results: [] }
    return { meta: parsed.meta ?? null, results: parsed.results }
  } catch {
    return { meta: null, results: [] }
  }
}

function errorMessage(e: unknown, fallback: string): string {
  const detail = (e as any)?.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

export const useOptimizationStore = defineStore('optimization', () => {
  const mode = ref<RunMode>(loadMode())
  const loading = ref(false)
  const result = ref<OptimizationResult | null>(null)
  const animationStep = ref(0)
  const isPlaying = ref(false)
  let playTimer: ReturnType<typeof setInterval> | null = null

  // 单组表单提升到 store：切到批量再切回时参数不丢失
  const form = reactive({
    algorithm: 'gradient_descent', functionId: 'rosenbrock',
    x0: -1.5, y0: 2.5, learningRate: 0.01, iterations: 100,
    momentum: 0.9, temperature: 100, coolingRate: 0.95
  })

  function setMode(m: RunMode) {
    // 切去批量模式时暂停动画但保留进度，切回单组时从原进度继续
    if (m === 'batch') stopAnimation()
    mode.value = m
    localStorage.setItem(MODE_STORAGE_KEY, m)
  }

  async function runOptimization(params: OptimizationParams) {
    loading.value = true
    stopAnimation()
    try {
      const { data } = await axios.post('/api/optimize', params)
      result.value = data
      animationStep.value = 0
    } catch (e) {
      ElMessage.error(errorMessage(e, '优化运行失败，请检查参数'))
    } finally { loading.value = false }
  }

  const currentPath = () => {
    if (!result.value) return []
    return result.value.path.slice(0, animationStep.value + 1)
  }

  function playAnimation() {
    if (!result.value) return
    isPlaying.value = true
    playTimer = setInterval(() => {
      if (animationStep.value < (result.value?.path.length || 0) - 1) {
        animationStep.value++
      } else {
        stopAnimation()
      }
    }, 80)
  }

  function pauseAnimation() { stopAnimation() }
  function stopAnimation() {
    isPlaying.value = false
    if (playTimer) { clearInterval(playTimer); playTimer = null }
  }

  function resetAnimation() { stopAnimation(); animationStep.value = 0 }
  function setStep(step: number) { animationStep.value = step }

  // ===== 批量试算 =====
  // 批量状态与单组完全隔离：跑批量不会触碰 result / animationStep
  const snapshot = loadBatchSnapshot()
  const batchLoading = ref(false)
  const batchDraft = ref<OptimizationParams[]>([])
  const batchResults = ref<BatchItemResult[]>(snapshot.results)
  const batchMeta = ref<BatchRunMeta | null>(snapshot.meta)

  function persistBatch() {
    localStorage.setItem(BATCH_STORAGE_KEY, JSON.stringify({
      meta: batchMeta.value,
      results: batchResults.value
    }))
  }

  async function runBatch(items: OptimizationParams[]) {
    if (!items.length) return
    batchLoading.value = true
    try {
      const { data } = await axios.post<BatchRunResponse>('/api/optimize/batch', { items })
      // 按参数指纹合并：重复提交同一批组合只保留一次结果
      const merged = new Map(batchResults.value.map(r => [r.key, r]))
      for (const r of data.results) merged.set(r.key, r)
      batchResults.value = [...merged.values()]
      batchMeta.value = {
        submittedAt: Date.now(),
        total: data.total,
        deduplicated: data.deduplicated,
        succeeded: data.succeeded,
        failed: data.failed
      }
      persistBatch()
      ElMessage.success(`批量试算完成：成功 ${data.succeeded} 组，失败 ${data.failed} 组，去重 ${data.deduplicated} 组`)
    } catch (e) {
      ElMessage.error(errorMessage(e, '批量试算失败，请稍后重试'))
    } finally { batchLoading.value = false }
  }

  function clearBatch() {
    batchResults.value = []
    batchMeta.value = null
    persistBatch()
  }

  return {
    mode, setMode, form,
    loading, result, animationStep, isPlaying, currentPath,
    runOptimization, playAnimation, pauseAnimation, stopAnimation, resetAnimation, setStep,
    batchLoading, batchDraft, batchResults, batchMeta, runBatch, clearBatch
  }
})
