import type { RouteLocationRaw } from 'vue-router'

import { api, type Project } from '@/api/client'

export type ProjectStep = 'upload' | 'parse' | 'annotate' | 'design' | 'preview'

export const PROJECT_STEPS: Array<{ key: ProjectStep; label: string; route: string }> = [
  { key: 'upload', label: '1 上传', route: 'floorplan-upload' },
  { key: 'parse', label: '2 解析', route: 'floorplan-parse' },
  { key: 'annotate', label: '3 标注', route: 'floorplan-editor' },
  { key: 'design', label: '4 设计', route: 'design-studio' },
  { key: 'preview', label: '5 预览', route: 'delivery-overview' },
]

const PREVIOUS_STEP: Partial<Record<ProjectStep, ProjectStep>> = {
  parse: 'upload',
  annotate: 'parse',
  design: 'annotate',
  preview: 'design',
}

/**
 * 将 API max_step 转为流程步骤
 */
export function maxStepToProjectStep(maxStep: string): ProjectStep {
  const found = PROJECT_STEPS.find((item) => item.key === maxStep)
  return found?.key ?? 'upload'
}

/**
 * 流程步骤对应的路由 name
 */
export function stepToRouteName(step: ProjectStep): string {
  return PROJECT_STEPS.find((item) => item.key === step)?.route ?? 'floorplan-upload'
}

/**
 * 步骤在流程中的序号（0-based）
 */
export function stepIndex(step: ProjectStep): number {
  return PROJECT_STEPS.findIndex((item) => item.key === step)
}

/**
 * 流程条可切换的最大步骤序号（含已确认标注时可进设计）
 */
export function resolveReachableStepIndex(project: Project): number {
  let max = stepIndex(maxStepToProjectStep(project.max_step ?? 'upload'))
  if (project.annotation_confirmed_at) {
    max = Math.max(max, stepIndex('design'))
  }
  return max
}

/**
 * 根据 max_step 计算已完成（可自由切换）的最大步骤序号
 */
export async function resolveMaxCompletedStepIndex(projectId: number, project?: Project): Promise<number> {
  const detail = project ?? (await api.getProject(projectId))
  return resolveReachableStepIndex(detail)
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

/**
 * 点击项目卡片时，跳转到 max_step 对应页面
 */
export async function resolveProjectEntry(projectId: number, project?: Project): Promise<RouteLocationRaw> {
  const detail = project ?? (await api.getProject(projectId))
  const step = maxStepToProjectStep(detail.max_step ?? 'upload')
  return { name: stepToRouteName(step), params: { id: projectId } }
}
