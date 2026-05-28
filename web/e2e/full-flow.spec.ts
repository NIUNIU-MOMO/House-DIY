import { test, expect } from '@playwright/test'

import {
  installCoreMocks,
  installEditorMocks,
  installGenerateMocks,
  installParseMocks,
  PROJECT_ID,
  mockProject,
} from './fixtures'

test.describe('原型主流程 smoke（mock API）', () => {
  test('01 首页 — 项目列表与服务状态', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto('/')
    await expect(page.getByRole('heading', { name: '我的户型项目' })).toBeVisible()
    await expect(page.getByText('E2E 样本')).toBeVisible()
    await expect(page.getByRole('link', { name: '系统服务状态' })).toBeVisible()
  })

  test('02 上传 — 页面与步骤条', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/upload`)
    await expect(page.getByRole('heading', { name: '上传标准平面图' })).toBeVisible()
    await expect(page.getByText('1 上传')).toBeVisible()
  })

  test('03 解析 — 解析进度页', async ({ page }) => {
    await installParseMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/parse?taskId=10`)
    await expect(page.getByRole('heading', { name: /解析/ })).toBeVisible()
  })

  test('04 标注 — 编辑器与确认按钮', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/editor`)
    await expect(page.getByText('3 标注')).toBeVisible()
    await expect(page.getByTestId('inspector-validation')).toBeVisible()
    await expect(page.getByText('户型质检 · 通过')).toBeVisible()
    await expect(page.getByTestId('confirm-floorplan-btn')).toBeVisible()
    await expect(page.getByTestId('add-room-btn')).toHaveCount(0)
  })

  test('04b 标注 — 质检 error 时禁止确认', async ({ page }) => {
    await installEditorMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/editor`)
    await expect(page.getByText('户型质检 · 未通过')).toBeVisible()
    await expect(page.getByTestId('confirm-floorplan-btn')).toBeDisabled()
    await expect(page.getByText('存在严重质检问题')).toBeVisible()
  })

  test('04d 标注 — 沿墙描边新增房间', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/editor`)
    await page.getByTestId('fullscreen-annotate-btn').click()
    const overlay = page.getByTestId('annotate-fullscreen-overlay')
    await page.keyboard.press('Escape')
    await expect(overlay.getByTestId('trace-room-btn')).toBeVisible()
    const roomCountBefore = await page.locator('.room-list li').count()
    await overlay.getByTestId('trace-room-btn').click()
    const svg = overlay.locator('.floor-svg')
    const box = await svg.boundingBox()
    if (!box) {
      throw new Error('floor svg not found')
    }
    const clicks = [
      { x: box.x + box.width * 0.2, y: box.y + box.height * 0.2 },
      { x: box.x + box.width * 0.5, y: box.y + box.height * 0.2 },
      { x: box.x + box.width * 0.5, y: box.y + box.height * 0.5 },
    ]
    for (const point of clicks) {
      await page.mouse.click(point.x, point.y)
    }
    await overlay.getByTestId('trace-finish-btn').click()
    await expect(page.locator('.room-list li')).toHaveCount(roomCountBefore + 1)
  })

  test('04e 标注 — 双击边线插入顶点', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/editor`)
    await page.getByTestId('fullscreen-annotate-btn').click()
    const overlay = page.getByTestId('annotate-fullscreen-overlay')
    await page.keyboard.press('Escape')
    await overlay.locator('.room-hit').first().click()
    await overlay.getByTestId('edge-handle-0').dblclick()
    await expect(page.locator('.vertex-handle')).toHaveCount(5)
  })

  test('04c 标注 — 全屏标注入口', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/editor`)
    await expect(page.getByTestId('fullscreen-annotate-btn')).toBeVisible()
    await page.getByTestId('fullscreen-annotate-btn').click()
    const overlay = page.getByTestId('annotate-fullscreen-overlay')
    await expect(overlay).toBeVisible()
    await expect(overlay.getByRole('heading', { name: '手动标注', level: 3 })).toBeVisible()
    await expect(overlay.getByText(/在户型图上点击房间中心位置以放置/)).toBeVisible()
    await expect(overlay.getByRole('button', { name: '标准矩形模式' })).toHaveClass(/is-active/)
    await expect(overlay.getByTestId('tool-scale')).toBeVisible()
  })

  test('05 设计 — Studio 与方案', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/studio`)
    await expect(page.getByRole('heading', { name: '描述你的理想之家' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '方案列表' })).toBeVisible()
    await expect(page.getByRole('button', { name: '生成 2D' })).toBeVisible()
  })

  test('06 生成 — 四步进度', async ({ page }) => {
    await installGenerateMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/generate?taskId=10`)
    await expect(page.getByRole('heading', { name: '正在生成全屋方案' })).toBeVisible()
    await expect(page.getByText('DesignSpec')).toBeVisible()
  })

  test('08 方案预览', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/delivery`)
    await expect(page.getByText('方案预览')).toBeVisible()
    await expect(page.getByText(mockProject.name)).toBeVisible()
  })

  test('09 2D 画廊', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/gallery`)
    await expect(page.getByRole('heading', { name: '2D 效果图画廊' })).toBeVisible()
    await expect(page.getByText('ComfyUI · flux_interior_t2i')).toBeVisible()
  })

  test('10 3D 漫游', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/scene`)
    await expect(page.getByText(/3D 漫游/)).toBeVisible()
  })

  test('07 方案微调', async ({ page }) => {
    await installCoreMocks(page)
    await page.route(`**/api/v1/projects/${PROJECT_ID}/design/refine`, (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          json: {
            instruction: '更暖色调',
            diff: [{ tag: 'style', text: '墙面改为暖白' }],
            patch: {},
            affected_room_ids: ['r1'],
          },
        })
      }
      return route.continue()
    })
    await page.goto(`/projects/${PROJECT_ID}/refine`)
    await expect(page.getByRole('heading', { name: '方案微调' })).toBeVisible()
  })

  test('11 知识库列表', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto('/knowledge')
    await expect(page.getByRole('heading', { name: '设计知识库' })).toBeVisible()
    await expect(page.getByText('北欧客厅案例')).toBeVisible()
  })

  test('12 导入参考', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto('/knowledge/import')
    await expect(page.getByRole('heading', { name: '导入外部参考' })).toBeVisible()
  })

  test('13 系统监控', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto('/settings')
    await expect(page.getByRole('link', { name: 'oMLX' })).toBeVisible()
    await expect(page.getByRole('button', { name: '日志' }).first()).toBeVisible()
    await expect(page.getByRole('heading', { name: 'oMLX 模型 Alias' })).toBeVisible()
    await expect(page.getByLabel('VLM（默认）')).toHaveValue('house-vlm-pro')
    await expect(page.getByRole('heading', { name: '项目输出目录' })).toBeVisible()
    await expect(page.getByText('Redis')).toBeVisible()
    await expect(page.getByRole('button', { name: '重启 ComfyUI' })).toBeVisible()
    await expect(page.getByRole('button', { name: '重启 oMLX' })).toHaveCount(0)
  })
})
