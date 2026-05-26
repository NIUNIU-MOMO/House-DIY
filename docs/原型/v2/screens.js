/* global SCREENS, renderScreen */

const FLOORPLAN_IMG = '../../../server/tests/fixtures/floorplans/G-MKT-1.png';

const PARSE_STEPS = [
  '图像预处理与结构增强',
  'VLM 识别房间列表',
  'VLM 分批提取轮廓',
  'OpenCV 评估墙线质量',
  '生成草稿并质检',
];

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/"/g, '&quot;');
}

function appHeader(active) {
  return `
    <header class="ui-header">
      <a href="#" class="ui-logo" data-action="goto-screen" data-screen="home">House<span>DIY</span></a>
      <nav class="ui-tabs">
        <a href="#" class="${active === 'projects' ? 'active' : ''}" data-action="goto-screen" data-screen="home">项目</a>
        <a href="#">知识库</a>
        <a href="#" class="${active === 'settings' ? 'active' : ''}" data-action="goto-screen" data-screen="settings">系统监控</a>
      </nav>
      <div class="ui-header-right">
        <span class="status-led" title="服务正常"></span>
      </div>
    </header>`;
}

function renderStepBar(current, maxIndex) {
  const steps = [
    { key: 'upload', label: '1 上传' },
    { key: 'parse', label: '2 解析' },
    { key: 'annotate', label: '3 标注' },
    { key: 'design', label: '4 设计' },
    { key: 'preview', label: '5 预览' },
  ];
  const idx = steps.findIndex((s) => s.key === current);
  return `
    <nav class="v2-steps" aria-label="项目流程">
      ${steps
        .map((step, i) => {
          let cls = 'pending';
          if (i === idx) cls = 'active';
          else if (i < idx || i <= maxIndex) cls = 'done';
          const disabled = i > maxIndex && i !== idx ? 'disabled' : '';
          return `<button type="button" class="v2-step ${cls}" data-action="goto-step" data-step="${step.key}" ${disabled}>${step.label}</button>`;
        })
        .join('')}
    </nav>`;
}

function renderParseTaskList(progressStep) {
  return PARSE_STEPS.map((label, index) => {
    let cls = '';
    let icon = '○';
    if (index < progressStep) {
      cls = 'done';
      icon = '✓';
    } else if (index === progressStep) {
      cls = 'active';
      icon = '◐';
    }
    return `<li class="${cls}">${icon} ${label}</li>`;
  }).join('');
}

function renderFloorMock(selectedRoom) {
  const rooms = [
    { id: 'r1', name: '卫生间', area: '15.5', style: 'left:8%;top:12%;width:22%;height:28%' },
    { id: 'r2', name: '长廊', area: '28.5', style: 'left:32%;top:8%;width:18%;height:55%' },
    { id: 'r3', name: '客厅', area: '40.9', style: 'left:52%;top:10%;width:38%;height:45%' },
    { id: 'r4', name: '卧室A', area: '23.7', style: 'left:52%;top:58%;width:38%;height:32%' },
  ];
  return `
    <div class="floor-mock">
      <img src="${FLOORPLAN_IMG}" alt="户型原图" />
      ${rooms
        .map(
          (r) => `
        <div class="room-overlay ${selectedRoom === r.id ? 'selected' : ''}" style="${r.style}">
          <span class="label">${r.name}</span>
        </div>`,
        )
        .join('')}
    </div>`;
}

const SCREENS = {
  home: {
    id: '00',
    title: '项目列表',
    render(state) {
      return `
        ${appHeader('projects')}
        <div class="ui-page">
          <div class="page-head">
            <div>
              <h2>我的户型项目</h2>
              <p class="muted">点击进入 → 跳转到项目最高进度步骤</p>
            </div>
            <button type="button" class="btn primary" data-action="goto-screen" data-screen="upload">+ 新建项目</button>
          </div>
          <div class="project-grid">
            <article class="project-card" data-action="goto-max-step" data-max="design">
              <div class="thumb render"></div>
              <div class="card-body">
                <h3>示例 · 三室两厅</h3>
                <p class="muted">最高进度：4 设计 · 2 套方案</p>
                <div class="tags"><span>设计中</span></div>
              </div>
            </article>
            <article class="project-card" data-action="goto-max-step" data-max="annotate">
              <div class="thumb"></div>
              <div class="card-body">
                <h3>待标注项目</h3>
                <p class="muted">最高进度：3 标注</p>
                <div class="tags"><span>解析完成</span></div>
              </div>
            </article>
          </div>
        </div>`;
    },
  },

  upload: {
    id: '01',
    title: '1 上传户型图',
    render(state) {
      return `
        ${appHeader('projects')}
        <div class="ui-page narrow upload-page">
          ${renderStepBar('upload', state.maxStepIndex)}
          <h2>上传标准平面图</h2>
          <p class="muted">支持开发商户型图 PNG / PDF · 建议带尺寸标注</p>
          <div class="upload-zone ${state.fileName ? 'has-file' : ''}" data-action="mock-upload">
            <div class="upload-icon">↑</div>
            <p>${state.fileName ? `已选 ${esc(state.fileName)}` : '拖拽文件到此处，或点击选择'}</p>
            <p class="tiny muted">最大 20MB · 将调用 oMLX VLM 解析</p>
          </div>
          <div class="footer-actions">
            <button type="button" class="btn ghost" data-action="goto-screen" data-screen="home">取消</button>
            <button type="button" class="btn primary" data-action="goto-screen" data-screen="parse" ${state.fileName ? '' : 'disabled'}>
              上传并开始解析 →
            </button>
          </div>
        </div>`;
    },
  },

  parse: {
    id: '02',
    title: '2 户型图解析',
    render(state) {
      const pct = state.parseProgress;
      const stepIdx = pct >= 100 ? 4 : Math.min(4, Math.floor(pct / 25));
      return `
        ${appHeader('projects')}
        <div class="ui-page narrow center parse-page">
          ${renderStepBar('parse', state.maxStepIndex)}
          <div class="parse-toolbar">
            <button type="button" class="btn ghost sm cancel-btn" data-action="cancel-parse">取消解析</button>
          </div>
          <div class="loader-card">
            <div class="spinner"></div>
            <h2>正在解析户型…</h2>
            <p class="muted progress-text">${pct}%</p>
            <ul class="task-list">${renderParseTaskList(stepIdx)}</ul>
            <div class="log-panel-wrap">
              <p class="log-title">处理日志</p>
              <div class="log-panel" role="log">
                ${state.logs.map((l) => `<p class="log-line">${esc(l)}</p>`).join('')}
              </div>
            </div>
            ${pct >= 100 ? '<button type="button" class="btn primary" style="margin-top:1rem" data-action="goto-screen" data-screen="annotate">进入标注 →</button>' : ''}
          </div>
        </div>`;
    },
  },

  annotate: {
    id: '03',
    title: '3 标注',
    render(state) {
      const sel = state.selectedRoom || 'r1';
      return `
        ${appHeader('projects')}
        <div class="editor-head">
          ${renderStepBar('annotate', state.maxStepIndex)}
        </div>
        <div class="editor-shell">
          <div class="validation-banner">
            <strong>户型质检 · 未通过</strong>
            <ul>
              <li>长廊 (r2) 与客厅 (r3) 重叠 IoU=0.22</li>
              <li>卫生间 (r1) 面积偏差较大，请核对比例尺</li>
            </ul>
          </div>
          <div class="editor-layout">
            <aside class="editor-tools">
              <h4>工具</h4>
              <button type="button" class="tool active">选择</button>
              <button type="button" class="tool">标定比例尺</button>
              <button type="button" class="tool" disabled>墙线</button>
              <button type="button" class="tool" disabled>门洞</button>
              <button type="button" class="tool" disabled>窗户</button>
              <hr />
              <h4>比例尺</h4>
              <p class="tiny muted">未标定</p>
              <hr />
              <h4>显示</h4>
              <label class="underlay-toggle">
                <input type="checkbox" checked /> 显示原图底图
              </label>
              <p class="tiny muted">关闭后仅看 AI 标注轮廓与名称</p>
              <hr />
              <h4>房间列表</h4>
              <ul class="room-list">
                <li class="${sel === 'r1' ? 'active' : ''}" data-action="select-room" data-room="r1">卫生间 · 15.5㎡</li>
                <li class="${sel === 'r2' ? 'active' : ''}" data-action="select-room" data-room="r2">长廊 · 28.5㎡</li>
                <li class="${sel === 'r3' ? 'active' : ''}" data-action="select-room" data-room="r3">客厅 · 40.9㎡</li>
                <li class="${sel === 'r4' ? 'active' : ''}" data-action="select-room" data-room="r4">卧室A · 23.7㎡</li>
              </ul>
            </aside>
            <div class="canvas-area">
              <div class="canvas-toolbar">
                <button type="button" class="btn sm ghost" data-action="save-annotate">保存</button>
                <span class="muted">状态 · draft</span>
              </div>
              <div class="floor-canvas" data-action="open-zoom">
                ${renderFloorMock(sel)}
                <span class="anno">底图为原图 · 拖拽选中房间顶点可修正轮廓 · 改名称后保存或确认 · 点击画布查看大图</span>
              </div>
            </div>
            <aside class="editor-inspector">
              <h4>手动标注</h4>
              <div class="manual-room-panel">
                <label class="manual-room-field">
                  房间类型
                  <select class="input light">
                    <option>卧室</option>
                    <option>客厅</option>
                    <option>厨房</option>
                    <option>卫生间</option>
                  </select>
                </label>
                <button type="button" class="btn sm primary block" data-action="mark-dirty">+ 新增房间</button>
                <p class="tiny muted">选择类型后，在画布上点击中心位置放置默认矩形，再拖拽顶点微调</p>
              </div>
              <hr />
              <h4>选中：${sel === 'r1' ? '卫生间' : sel === 'r2' ? '长廊' : sel === 'r3' ? '客厅' : '卧室A'}</h4>
              <div class="form-row">
                <label>名称</label>
                <input class="input light" value="${sel === 'r1' ? '卫生间' : sel === 'r2' ? '长廊' : sel === 'r3' ? '客厅' : '卧室A'}" data-action="mark-dirty" />
              </div>
              <div class="form-row">
                <label>面积</label>
                <input class="input light" value="${sel === 'r1' ? '15.5' : sel === 'r2' ? '28.5' : sel === 'r3' ? '40.9' : '23.7'}" readonly /> ㎡
              </div>
              <div class="form-row">
                <label>连通</label>
                <span class="muted">${sel}</span>
              </div>
              <button type="button" class="btn sm ghost block danger-btn" data-action="mark-dirty">删除房间</button>
              <div class="inspector-actions">
                <button type="button" class="btn primary block" disabled>确认户型，进入设计 →</button>
                <p class="warn-text">存在严重质检问题，请修正房间边界或重新解析后再确认</p>
              </div>
            </aside>
          </div>
        </div>`;
    },
  },

  design: {
    id: '04',
    title: '4 设计',
    render(state) {
      return `
        ${appHeader('projects')}
        <div class="design-workspace">
          <aside class="scheme-sidebar">
            <h4>方案列表</h4>
            <button type="button" class="scheme-item active">方案 A</button>
            <button type="button" class="scheme-item">方案 B</button>
            <button type="button" class="btn sm ghost block" style="margin-top:0.5rem">+ 新建方案</button>
          </aside>
          <div class="design-content">
            ${renderStepBar('design', state.maxStepIndex)}
            <h2>描述你的理想之家</h2>
            <div class="spec-banner">方案 A · 现代简约 · 4 个房间</div>
            <textarea class="input light area" rows="5">现代简约、暖白墙面、原木家具、大量自然光</textarea>
            <div class="chips">
              <button type="button" class="chip">现代简约</button>
              <button type="button" class="chip">北欧</button>
              <button type="button" class="chip">新中式</button>
            </div>
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem">
              <button type="button" class="btn primary">生成 2D</button>
              <button type="button" class="btn">保存方案</button>
              <button type="button" class="btn ghost" data-action="goto-screen" data-screen="preview">生成 3D 漫游</button>
            </div>
            <p class="muted" style="font-size:0.85rem">选中房间后微调；未选则应用于全部</p>
            <div class="room-thumbs">
              <div class="room-thumb">客厅</div>
              <div class="room-thumb selected">主卧</div>
              <div class="room-thumb">厨房</div>
              <div class="room-thumb">卫生间</div>
            </div>
            <div style="display:flex;gap:0.5rem;margin-top:0.5rem">
              <input class="input light" style="flex:1" value="主卧改成深色木地板" data-action="mark-dirty" />
              <button type="button" class="btn sm primary" data-action="mark-dirty">应用</button>
            </div>
          </div>
        </div>`;
    },
  },

  preview: {
    id: '05',
    title: '5 预览',
    render(state) {
      return `
        ${appHeader('projects')}
        <div class="ui-page">
          ${renderStepBar('preview', state.maxStepIndex)}
          <div class="page-head">
            <div>
              <h2>示例 · 三室两厅 · 方案预览</h2>
              <p class="muted">现代简约 · 方案 A</p>
            </div>
            <div class="btn-group">
              <select class="input" style="width:auto">
                <option>方案 A</option>
                <option>方案 B</option>
              </select>
              <button type="button" class="btn primary">进入 3D 漫游</button>
            </div>
          </div>
          <div class="delivery-grid">
            <section class="panel">
              <h4>房间覆盖</h4>
              <ul class="check-list">
                <li>✓ 客厅 · 1 张效果图</li>
                <li>✓ 主卧 · 1 张效果图</li>
                <li>✓ 厨房 · 1 张效果图</li>
                <li>✓ 卫生间 · 1 张效果图</li>
              </ul>
            </section>
            <section class="panel">
              <h4>3D 场景</h4>
              <p>就绪 · 4 房间 · 3 个门洞 Portal</p>
            </section>
          </div>
          <h3 style="font-family:var(--serif);margin-bottom:0.75rem">2D 效果图</h3>
          <div class="render-grid">
            ${['客厅', '主卧', '厨房', '卫生间'].map(
              (r) => `
              <article class="render-card">
                <div class="img"></div>
                <div class="cap">${r}</div>
              </article>`,
            ).join('')}
          </div>
        </div>`;
    },
  },

  settings: {
    id: '06',
    title: '系统监控与设置',
    render(state) {
      return `
        ${appHeader('settings')}
        <div class="ui-page">
          <div class="page-head">
            <div>
              <h2>系统监控</h2>
              <p class="muted">本地服务状态与模型配置</p>
            </div>
          </div>
          <div class="service-grid">
            <article class="service-card">
              <h3><span class="status-dot ok"></span>API</h3>
              <p class="muted">运行中 · :8080</p>
            </article>
            <article class="service-card">
              <h3><span class="status-dot ok"></span>ComfyUI</h3>
              <p class="muted">运行中 · :8188</p>
            </article>
            <article class="service-card">
              <h3><span class="status-dot off"></span>oMLX</h3>
              <p class="muted">离线 · :8000</p>
            </article>
            <article class="service-card">
              <h3><span class="status-dot ok"></span>Redis</h3>
              <p class="muted">运行中</p>
            </article>
          </div>
          <section class="storage-section">
            <h3>输出根目录</h3>
            <p class="muted">存放整体设计流程生成的全部文件（原图、标注、方案 2D/3D）</p>
            <div class="settings-path">
              <input class="input" value="${esc(state.outputRoot)}" />
              <button type="button" class="btn ghost">浏览…</button>
            </div>
            <p class="tiny muted">状态：可写 ✓</p>
            <div class="tree-preview">${esc(`{output_root}/
└── {project_id}/
    ├── source.png
    ├── floorplan.json
    └── schemes/
        └── {scheme_id}/
            ├── design_spec.json
            ├── renders/
            └── scene/`)}</div>
            <button type="button" class="btn primary" style="margin-top:1rem">保存配置</button>
          </section>
        </div>`;
    },
  },
};

function renderScreen(key, state) {
  const screen = SCREENS[key];
  if (!screen) return '<p>未知页面</p>';
  return screen.render(state);
}
