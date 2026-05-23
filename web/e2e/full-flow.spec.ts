import { test, expect } from '@playwright/test'

import {
  installCoreMocks,
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
    await expect(page.getByText('oMLX')).toBeVisible()
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

  test('04 校对 — 编辑器与确认按钮', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/editor`)
    await expect(page.getByText('3 校对')).toBeVisible()
    await expect(page.getByRole('button', { name: /确认户型/ })).toBeVisible()
  })

  test('05 设计 — Studio 与 RAG', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/studio`)
    await expect(page.getByRole('heading', { name: '描述你的理想之家' })).toBeVisible()
    await expect(page.getByText('北欧客厅案例')).toBeVisible()
  })

  test('06 生成 — 四步进度', async ({ page }) => {
    await installGenerateMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/generate?taskId=10`)
    await expect(page.getByRole('heading', { name: '正在生成全屋方案' })).toBeVisible()
    await expect(page.getByText('DesignSpec')).toBeVisible()
  })

  test('08 交付总览', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto(`/projects/${PROJECT_ID}/delivery`)
    await expect(page.getByText('交付总览')).toBeVisible()
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

  test('13 系统设置', async ({ page }) => {
    await installCoreMocks(page)
    await page.goto('/settings')
    await expect(page.getByRole('heading', { name: '系统状态与设置' })).toBeVisible()
    await expect(page.getByText('omlx')).toBeVisible()
  })
})
