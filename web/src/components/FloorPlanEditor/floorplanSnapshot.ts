import { toRaw } from 'vue'

import type { FloorPlanData } from '@/types/floorplan'

/**
 * 深拷贝 floorplan，用于全屏模式进入/取消快照
 */
export function cloneFloorplanSnapshot(data: FloorPlanData): FloorPlanData {
  return structuredClone(toRaw(data))
}

/**
 * 比较两份 floorplan 是否一致（用于检测全屏内是否有改动）
 */
export function floorplansEqual(a: FloorPlanData, b: FloorPlanData): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}
