export interface Task {
  id: number
  project_id: number
  type: string
  status: 'pending' | 'running' | 'done' | 'failed' | 'cancelled'
  progress: number
  step: number
  step_label: string
  error: string | null
  logs?: string[]
}

export const PARSE_STEP_LABELS = [
  '图像预处理与结构增强',
  'VLM 识别房间列表',
  'VLM 分批提取轮廓',
  'OpenCV 评估墙线质量',
  '生成草稿并质检',
]
