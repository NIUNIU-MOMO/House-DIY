import type { RouteLocationRaw } from 'vue-router'

import { api, type FloorPlan, type Project } from '@/api/client'

export type ProjectStep = 'upload' | 'parse' | 'review' | 'design' | 'preview'

export const PROJECT_STEPS: Array<{ key: ProjectStep; label: string; route: string }> = [
  { key: 'upload', label: '1 上传', route: 'floorplan-upload' },
  { key: 'parse', label: '2 解析', route: 'floorplan-parse' },
  { key: 'review', label: '3 校对', route: 'floorplan-editor' },
  { key: 'design', label: '4 设计', route: 'design-studio' },
  { key: 'preview', label: '5 预览', route: 'delivery-overview' },
]

const STATUS_TO_STEP: Record<string, ProjectStep> = {
  draft: 'upload',
  parsing: 'parse',
  review: 'review',
  designing: 'design',
  delivered: 'preview',
}

const PREVIOUS_STEP: Partial<Record<ProjectStep, ProjectStep>> = {
  parse: 'upload',
  review: 'parse',
  design: 'review',
  preview: 'design',
}

/**
 * 项目状态映射到当前流程步骤
 */
export function statusToStep(status: string): ProjectStep {
  return STATUS_TO_STEP[status] ?? 'upload'
}

/**
 * 流程步骤对应的路由 name
 */
export function stepToRouteName(step: ProjectStep): string {
  return PROJECT_STEPS.find((item) => item.key === step)?.route ?? 'floorplan-upload'
}

/**
 * 根据项目状态解析入口路由（同步，不含 draft 细判）
 */
export function resolveRouteForStatus(status: string): RouteLocationRaw {
  const step = statusToStep(status)
  return { name: stepToRouteName(step) }
}

/**
 * 步骤在流程中的序号（0-based）
 */
export function stepIndex(step: ProjectStep): number {
  return PROJECT_STEPS.findIndex((item) => item.key === step)
}

/**
 * 根据项目状态与户型数据，计算已完成（可自由切换）的最大步骤序号
 */
export async function resolveMaxCompletedStepIndex(projectId: number, project?: Project): Promise<number> {
  const detail = project ?? (await api.getProject(projectId))
  let max = stepIndex(statusToStep(detail.status))

  if (detail.status === 'draft') {
    try {
      const floorplan = await api.getFloorplan(projectId)
      if (floorplan.rooms?.length) {
        max = Math.max(max, stepIndex('review'))
      } else if (floorplan.source_url || floorplan.source_image) {
        max = Math.max(max, stepIndex('parse'))
      }
    } catch {
      max = Math.max(max, stepIndex('upload'))
    }
  }

  return max
}

/**
 * 步骤是否已完成（可在流程条中自由切换）
 */
export function isStepReachable(step: ProjectStep, maxCompletedIndex: number): boolean {
  return stepIndex(step) <= maxCompletedIndex
}

/**
 * 上一步骤（用于返回按钮）
 */
export function previousStep(step: ProjectStep): ProjectStep | null {
  return PREVIOUS_STEP[step] ?? null
}

function draftEntryRoute(projectId: number, floorplan: FloorPlan | null): RouteLocationRaw {
  if (floorplan?.rooms?.length) {
    return { name: 'floorplan-editor', params: { id: projectId } }
  }
  if (floorplan?.source_url || floorplan?.source_image) {
    return { name: 'floorplan-parse', params: { id: projectId } }
  }
  return { name: 'floorplan-upload', params: { id: projectId } }
}

/**
 * 点击项目卡片时，跳转到当前进度对应页面
 */
export async function resolveProjectEntry(projectId: number, project?: Project): Promise<RouteLocationRaw> {
  const detail = project ?? (await api.getProject(projectId))

  if (detail.status === 'draft') {
    try {
      const floorplan = await api.getFloorplan(projectId)
      return draftEntryRoute(projectId, floorplan)
    } catch {
      return { name: 'floorplan-upload', params: { id: projectId } }
    }
  }

  const route = resolveRouteForStatus(detail.status)
  if (typeof route === 'object' && 'name' in route && route.name) {
    return { ...route, params: { id: projectId } }
  }
  return { name: stepToRouteName(statusToStep(detail.status)), params: { id: projectId } }
}
