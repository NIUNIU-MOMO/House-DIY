import { onBeforeUnmount, ref, watch } from 'vue'

import type { Task } from '@/types/task'

export interface PipelineUpdate {
  type: 'pipeline_update'
  event: string
  pipeline_step: string
  room_index?: number
  room_total?: number
  task: Task
}

export function useTaskWebSocket(
  projectId: () => number,
  onUpdate: (task: Task) => void,
  onPipeline?: (payload: Omit<PipelineUpdate, 'type' | 'task'>) => void,
) {
  const connected = ref(false)
  let socket: WebSocket | null = null

  function connect(id: number) {
    if (socket) {
      socket.close()
    }
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    socket = new WebSocket(`${protocol}://${window.location.host}/api/v1/projects/${id}/ws`)

    socket.onopen = () => {
      connected.value = true
    }

    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data as string)
      if (payload.type === 'task_update' && payload.task) {
        onUpdate(payload.task)
      }
      if (payload.type === 'pipeline_update' && payload.task) {
        const pipeline = payload as PipelineUpdate
        onUpdate(pipeline.task)
        onPipeline?.({
          event: pipeline.event,
          pipeline_step: pipeline.pipeline_step,
          room_index: pipeline.room_index,
          room_total: pipeline.room_total,
        })
      }
    }

    socket.onclose = () => {
      connected.value = false
    }
  }

  watch(projectId, (id: number) => connect(id), { immediate: true })

  onBeforeUnmount(() => {
    socket?.close()
  })

  return { connected }
}
