export interface Task {
  id: number
  project_id: number
  type: string
  status: 'pending' | 'running' | 'done' | 'failed'
  progress: number
  step: number
  step_label: string
  error: string | null
}

export const PARSE_STEP_LABELS = [
  '图像预处理与矫正',
  'oMLX VLM 识别房间与门窗',
  'OpenCV 提取墙线矢量',
  '生成 FloorPlanModel 草稿',
]
