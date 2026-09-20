import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import axios from 'axios'
import type { BatchTask } from '@/types'

const BATCHES_KEY = 'opt-batch-snapshots-v1'
const MODE_KEY = 'opt-mode-v1'
const POLL_INTERVAL = 1000

function loadSnapshots(): Record<string, BatchTask> {
  try {
    return JSON.parse(localStorage.getItem(BATCHES_KEY) || '{}')
  } catch {
    return {}
  }
}

export const useBatchStore = defineStore('batch', () => {
  const batches = ref<Record<string, BatchTask>>(loadSnapshots())
  const currentId = ref<string | null>(null)
  const submitting = ref(false)
  const mode = ref<'single' | 'batch'>(
    localStorage.getItem(MODE_KEY) === 'batch' ? 'batch' : 'single'
  )
  let pollTimer: ReturnType<typeof setInterval> | null = null

  const orderedBatches = computed(() =>
    Object.values(batches.value).sort((a, b) => b.createdAt - a.createdAt)
  )
  const current = computed(() => (currentId.value ? batches.value[currentId.value] || null : null))
  const hasRunning = computed(() => orderedBatches.value.some(b => b.status === 'running'))

  function persist() {
    // 只缓存已完成批次与仍在运行批次的最新快照；刷新后再与服务端对账
    localStorage.setItem(BATCHES_KEY, JSON.stringify(batches.value))
  }

  function setMode(m: 'single' | 'batch') {
    mode.value = m
    localStorage.setItem(MODE_KEY, m)
  }

  function upsertBatch(batch: BatchTask) {
    batches.value[batch.id] = batch
    persist()
  }

  async function submit(combinations: object[]) {
    if (submitting.value) return null
    submitting.value = true
    try {
      const { data } = await axios.post<BatchTask>('/api/batches', { combinations })
      upsertBatch(data)
      currentId.value = data.id
      return data
    } finally {
      submitting.value = false
    }
  }

  async function refresh(id: string) {
    try {
      const { data } = await axios.get<BatchTask>(`/api/batches/${id}`)
      upsertBatch(data)
      return data
    } catch {
      // 服务端暂不可达时保留本地快照，不打断查看
      return null
    }
  }

  async function remove(id: string) {
    try {
      await axios.delete(`/api/batches/${id}`)
    } catch {
      // 即使服务端已不存在，也清理本地快照
    }
    delete batches.value[id]
    if (currentId.value === id) {
      currentId.value = orderedBatches.value[0]?.id || null
    }
    persist()
  }

  function select(id: string) { currentId.value = id }

  /** 启动轮询：刷新后从本地快照恢复的运行中任务也能继续跟踪完成情况 */
  function startPolling() {
    if (pollTimer) return
    pollTimer = setInterval(async () => {
      const running = orderedBatches.value.filter(b => b.status === 'running').map(b => b.id)
      await Promise.all(running.map(id => refresh(id)))
    }, POLL_INTERVAL)
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  }

  return {
    batches, orderedBatches, currentId, current, submitting, mode, hasRunning,
    setMode, submit, refresh, remove, select, startPolling, stopPolling, persist
  }
})
