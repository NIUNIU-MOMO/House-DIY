/* global SCREENS */

function appHeader(active) {
  const items = [
    ['项目', 'projects'],
    ['设计', 'design'],
    ['知识库', 'knowledge'],
    ['设置', 'settings'],
  ];
  return `
    <header class="ui-header">
      <div class="ui-logo">House<span>DIY</span></div>
      <nav class="ui-tabs">
        ${items.map(([label, key]) => `
          <a href="#" class="${active === key ? 'active' : ''}">${label}</a>
        `).join('')}
      </nav>
      <div class="ui-header-right">
        <span class="badge offline">本地离线</span>
        <button type="button" class="icon-btn" title="服务状态">●</button>
      </div>
    </header>`;
}

const SCREENS = [
  {
    id: '01',
    title: '项目列表',
    flow: '入口',
    html: `
      ${appHeader('projects')}
      <div class="ui-page">
        <div class="page-head">
          <div>
            <h2>我的户型项目</h2>
            <p class="muted">全部数据保存在本机 · 已同步 Obsidian Vault</p>
          </div>
          <button type="button" class="btn primary">+ 新建项目</button>
        </div>
        <div class="filter-row">
          <input type="search" placeholder="搜索项目名…" class="input" />
          <select class="input select"><option>全部状态</option><option>设计中</option><option>已完成</option></select>
        </div>
        <div class="project-grid">
          <article class="project-card featured">
            <div class="thumb floorplan"></div>
            <div class="card-body">
              <h3>望京三期 · 89㎡ 三居室</h3>
              <p class="muted">3 室 2 厅 · 上次编辑 2 小时前</p>
              <div class="tags"><span>已校对</span><span>方案 v2</span></div>
              <div class="card-actions">
                <button class="btn sm">继续设计</button>
                <button class="btn sm ghost">3D 漫游</button>
              </div>
            </div>
          </article>
          <article class="project-card">
            <div class="thumb render"></div>
            <div class="card-body">
              <h3>草稿 · 两居室</h3>
              <p class="muted">待校对户型</p>
              <div class="tags"><span class="warn">解析中</span></div>
            </div>
          </article>
          <article class="project-card add">
            <span>+</span>
            <p>新建项目</p>
          </article>
        </div>
      </div>
    `,
  },
  {
    id: '02',
    title: '新建项目 · 上传户型',
    flow: '上传',
    html: `
      ${appHeader('projects')}
      <div class="ui-page narrow">
        <div class="steps">
          <span class="done">1 上传</span><span class="active">2 解析</span><span>3 校对</span><span>4 设计</span>
        </div>
        <h2>上传标准平面图</h2>
        <p class="muted">支持开发商户型图 PNG / PDF · 建议带尺寸标注</p>
        <div class="upload-zone">
          <div class="upload-icon">↑</div>
          <p>拖拽文件到此处，或点击选择</p>
          <p class="tiny muted">最大 20MB · 将调用 oMLX VLM 解析</p>
        </div>
        <div class="form-row">
          <label>项目名称</label>
          <input class="input" value="望京三期 89㎡" />
        </div>
        <div class="form-row">
          <label>预估总面积（㎡，可选）</label>
          <input class="input" placeholder="89" />
        </div>
        <div class="preview-strip">
          <div class="mini-floor"></div>
          <span>示例：已选 sample_floorplan.png</span>
        </div>
        <div class="footer-actions">
          <button class="btn ghost">取消</button>
          <button class="btn primary">开始解析 →</button>
        </div>
      </div>
    `,
  },
  {
    id: '03',
    title: '户型 AI 解析中',
    flow: '上传',
    html: `
      ${appHeader('projects')}
      <div class="ui-page narrow center">
        <div class="steps">
          <span class="done">1 上传</span><span class="active">2 解析</span><span>3 校对</span><span>4 设计</span>
        </div>
        <div class="loader-card">
          <div class="spinner"></div>
          <h2>正在解析户型…</h2>
          <ul class="task-list">
            <li class="done">✓ 图像预处理与矫正</li>
            <li class="done">✓ oMLX VLM 识别房间与门窗</li>
            <li class="active">◐ OpenCV 提取墙线矢量</li>
            <li>○ 生成 FloorPlanModel 草稿</li>
          </ul>
          <div class="progress-bar"><div style="width:68%"></div></div>
          <p class="tiny muted">预计剩余 ~40 秒 · GPU: oMLX VLM</p>
        </div>
      </div>
    `,
  },
  {
    id: '04',
    title: '户型 2D 校对编辑器',
    flow: '校对',
    html: `
      ${appHeader('projects')}
      <div class="editor-layout">
        <aside class="editor-tools">
          <h4>工具</h4>
          <button class="tool active">选择</button>
          <button class="tool">墙线</button>
          <button class="tool">门洞</button>
          <button class="tool">窗户</button>
          <button class="tool">房间标签</button>
          <hr/>
          <h4>比例尺</h4>
          <p class="tiny muted">已标定 1px = 0.012m</p>
          <button class="btn sm ghost">重新标定</button>
          <hr/>
          <h4>房间列表</h4>
          <ul class="room-list">
            <li class="active">客厅 28㎡</li>
            <li>主卧 14㎡</li>
            <li>次卧 10㎡</li>
            <li>厨房 6㎡</li>
            <li>卫生间 4㎡</li>
          </ul>
        </aside>
        <div class="canvas-area">
          <div class="canvas-toolbar">
            <button class="btn sm ghost">撤销</button>
            <button class="btn sm ghost">重做</button>
            <span class="muted">缩放 120%</span>
          </div>
          <div class="floor-canvas">
            <svg viewBox="0 0 400 300" class="floor-svg">
              <rect width="400" height="300" fill="#f8f4ee"/>
              <path d="M40,40 L360,40 L360,260 L40,260 Z" fill="none" stroke="#2c4a3e" stroke-width="4"/>
              <path d="M200,40 L200,180" stroke="#2c4a3e" stroke-width="3"/>
              <path d="M40,180 L360,180" stroke="#2c4a3e" stroke-width="3"/>
              <rect x="190" y="170" width="20" height="12" fill="#c4a574"/>
              <text x="100" y="120" class="room-label">客厅</text>
              <text x="270" y="100" class="room-label">主卧</text>
            </svg>
            <span class="anno">拖拽顶点校正墙线 · 点击门洞切换连通房间</span>
          </div>
        </div>
        <aside class="editor-inspector">
          <h4>选中：客厅</h4>
          <div class="form-row"><label>面积</label><input class="input" value="28.2" /> ㎡</div>
          <div class="form-row"><label>连通</label><span>主卧、玄关</span></div>
          <button class="btn primary block">确认户型，进入设计 →</button>
        </aside>
      </div>
    `,
  },
  {
    id: '05',
    title: '设计描述 · RAG 参考',
    flow: '设计',
    html: `
      ${appHeader('design')}
      <div class="design-layout">
        <section class="design-main">
          <div class="steps inline">
            <span class="done">户型已确认</span><span class="active">描述需求</span><span>生成</span>
          </div>
          <h2>描述你的理想之家</h2>
          <textarea class="input area" rows="6" placeholder="例如：现代简约、暖白墙面、客厅要有落地窗采光感、主卧偏安静深色系、厨房白色橱柜…">现代简约风格，整体暖白与浅橡木。客厅明亮通透，沙发靠墙；主卧安静，深灰床头；厨房白色橱柜配石英石台面。预算感中等，适合三口之家。</textarea>
          <div class="chips">
            <span>现代简约</span><span>北欧</span><span>新中式</span><span>轻奢</span><span>奶油风</span>
          </div>
          <div class="option-row">
            <label><input type="checkbox" checked /> 参考历史案例 (RAG)</label>
            <label><input type="checkbox" checked /> 生成后写入 Obsidian</label>
          </div>
          <button class="btn primary lg">生成全屋方案 →</button>
        </section>
        <aside class="rag-panel">
          <h4>📚 相似案例（Obsidian RAG）</h4>
          <article class="rag-card">
            <strong>案例 · 89㎡ 三居简约</strong>
            <p class="tiny">客厅南向采光、浅橡木地板…</p>
            <span class="score">相似度 0.87</span>
          </article>
          <article class="rag-card">
            <strong>参考 · 杂志剪页 #12</strong>
            <p class="tiny">奶油风客厅，弧形沙发…</p>
            <span class="score">0.72</span>
          </article>
          <a href="#" class="link">查看全部知识库 →</a>
          <hr/>
          <h4>将使用</h4>
          <ul class="tiny muted">
            <li>oMLX → DesignSpec</li>
            <li>ComfyUI → 5 房间效果图</li>
            <li>Scene Builder → 全屋 3D</li>
          </ul>
        </aside>
      </div>
    `,
  },
  {
    id: '06',
    title: '方案生成进度',
    flow: '生成',
    html: `
      ${appHeader('design')}
      <div class="ui-page">
        <h2>正在生成全屋方案</h2>
        <p class="muted">任务队列串行 GPU · 请勿关闭本机 oMLX / ComfyUI</p>
                <div class="pipeline">
          <div class="pipe-step done">
            <span class="icon">✓</span>
            <div><strong>DesignSpec</strong><p class="tiny">5 房间 · 已写入 Specs/</p></div>
          </div>
          <div class="pipe-step active">
            <span class="icon">◐</span>
            <div><strong>2D 效果图</strong><p class="tiny">ComfyUI · 客厅 2/3</p>
              <div class="mini-progress"><div style="width:45%"></div></div>
            </div>
          </div>
          <div class="pipe-step">
            <span class="icon">○</span>
            <div><strong>3D 场景构建</strong><p class="tiny">等待 ComfyUI 完成</p></div>
          </div>
          <div class="pipe-step">
            <span class="icon">○</span>
            <div><strong>Obsidian 案例</strong><p class="tiny">摘要 + 索引</p></div>
          </div>
        </div>
        <div class="live-preview">
          <div class="render-slot done"><span>客厅</span></div>
          <div class="render-slot active"><span>主卧…</span></div>
          <div class="render-slot"></div>
          <div class="render-slot"></div>
          <div class="render-slot"></div>
        </div>
        <button class="btn ghost">后台运行</button>
      </div>
    `,
  },
  {
    id: '07',
    title: '方案微调',
    flow: '微调',
    html: `
      ${appHeader('design')}
      <div class="refine-layout">
        <section class="refine-context">
          <div class="page-head" style="margin-bottom:1rem;">
            <div>
              <h2>方案微调</h2>
              <p class="muted">望京三期 · 方案 v2 · DesignSpec 已锁定户型几何</p>
            </div>
            <span class="badge offline">POST /design/refine</span>
          </div>
          <div class="spec-snapshot">
            <h4>当前方案摘要</h4>
            <p class="tiny muted">globalStyle</p>
            <p><strong>现代简约</strong> · 暖白墙面 · 浅橡木地面</p>
            <ul class="room-spec-list">
              <li class="active"><span>客厅</span><em>L 型沙发 · 南向采光</em></li>
              <li><span>主卧</span><em>深灰床头 · 安静色系</em></li>
              <li><span>厨房</span><em>白色橱柜 · 石英石台面</em></li>
              <li><span>次卧</span><em>书桌靠窗</em></li>
            </ul>
            <button class="btn sm ghost block">查看完整 DesignSpec JSON</button>
          </div>
          <div class="refine-history">
            <h4>本轮对话</h4>
            <div class="chat-bubble user">主卧床头改成深灰色软包，窗帘换亚麻米色</div>
            <div class="chat-bubble ai tiny">将更新 master_bedroom 材质与家具字段…</div>
          </div>
        </section>
        <section class="refine-input">
          <div class="steps inline">
            <span class="done">已生成</span><span class="active">自然语言微调</span><span>增量渲染</span>
          </div>
          <h3>描述你想调整的内容</h3>
          <p class="muted tiny">LLM 在现有 DesignSpec 上生成 patch，不修改 FloorPlanModel</p>
          <textarea class="input area" rows="5" placeholder="例如：客厅沙发换更大浅灰布艺；厨房把手改哑光黑…">客厅茶几换圆形小茶几，主卧增加床头暖光壁灯，整体再偏暖一点。</textarea>
          <div class="chips">
            <span>换家具</span><span>改配色</span><span>调灯光</span><span>换材质</span><span>单房间重做</span>
          </div>
          <div class="scope-box">
            <h4>增量更新范围</h4>
            <label><input type="checkbox" checked /> DesignSpec（LLM patch）</label>
            <label><input type="checkbox" checked /> 受影响房间 2D（ComfyUI）</label>
            <label><input type="checkbox" checked /> 受影响房间 3D（Scene Builder）</label>
            <label><input type="checkbox" /> 更新 Obsidian 案例备注</label>
          </div>
          <div class="footer-actions" style="justify-content:flex-start;">
            <button class="btn primary">解析并预览变更 →</button>
            <button class="btn ghost">清空输入</button>
          </div>
        </section>
        <aside class="refine-preview">
          <h4>变更预览（待确认）</h4>
          <ul class="diff-list">
            <li><span class="diff-tag mod">修改</span> 客厅 · coffee_table → 圆形茶几</li>
            <li><span class="diff-tag mod">修改</span> 主卧 · 新增壁灯 lighting.bedside</li>
            <li><span class="diff-tag mod">修改</span> globalStyle · palette 略向暖色</li>
            <li><span class="diff-tag regen">重渲染</span> 客厅 2D · 主卧 2D + 3D</li>
          </ul>
          <p class="tiny muted">ComfyUI 串行 2 房间 · 约 8 分钟</p>
          <button class="btn primary block">应用微调并重新生成</button>
          <button class="btn ghost block">放弃，保持原方案</button>
          <hr/>
          <p class="tiny muted">不移动墙体 · 不挡门洞 · RAG 仅风格参考</p>
        </aside>
      </div>
    `,
  },
  {
    id: '08',
    title: '方案交付总览',
    flow: '交付',
    html: `
      ${appHeader('design')}
      <div class="ui-page">
        <div class="page-head">
          <div>
            <h2>望京三期 · 方案 v2</h2>
            <p class="muted">现代简约 · 生成于今天 14:32 · 已同步 Obsidian</p>
          </div>
          <div class="btn-group">
            <button class="btn ghost">微调方案</button>
            <button class="btn ghost">重新生成</button>
            <button class="btn primary">进入 3D 漫游</button>
          </div>
        </div>
        <div class="delivery-hero">
          <div class="hero-3d">
            <div class="fake-3d">
              <span class="room-badge">客厅</span>
              <p>WASD 漫游 · 门口切换房间</p>
            </div>
            <button class="btn primary">▶ 打开全屋 3D</button>
          </div>
          <div class="hero-meta">
            <h4>房间覆盖</h4>
            <ul class="check-list">
              <li>✓ 客厅 · 3 张效果图</li>
              <li>✓ 主卧 · 2 张</li>
              <li>✓ 厨房 · 2 张</li>
              <li>✓ 次卧 · 2 张</li>
              <li>✓ 卫生间 · 1 张</li>
            </ul>
            <a href="#" class="link">在 Obsidian 中打开案例笔记</a>
          </div>
        </div>
        <h3>2D 效果图速览</h3>
        <div class="render-grid sm">
          <div class="render-thumb"><span>客厅 A</span></div>
          <div class="render-thumb"><span>客厅 B</span></div>
          <div class="render-thumb"><span>主卧</span></div>
          <div class="render-thumb"><span>次卧</span></div>
          <div class="render-thumb"><span>厨房</span></div>
        </div>
      </div>
    `,
  },
  {
    id: '09',
    title: '2D 效果图画廊',
    flow: '交付',
    html: `
      ${appHeader('design')}
      <div class="ui-page">
        <div class="gallery-layout">
          <aside class="room-nav">
            <button class="active">客厅</button>
            <button>主卧</button>
            <button>次卧</button>
            <button>厨房</button>
            <button>卫生间</button>
          </aside>
          <section class="gallery-main">
            <div class="big-render"></div>
            <div class="thumb-row">
              <div class="t active"></div><div class="t"></div><div class="t"></div>
            </div>
            <div class="meta-bar">
              <span>ComfyUI · living_modern_v1</span>
              <button class="btn sm ghost">仅重生成此房间</button>
              <button class="btn sm ghost">下载</button>
            </div>
            <details class="prompt-details">
              <summary>查看 Prompt / DesignSpec 片段</summary>
              <pre>modern living room, warm white walls, oak floor, floor-to-ceiling window...</pre>
            </details>
          </section>
        </div>
      </div>
    `,
  },
  {
    id: '10',
    title: '3D 全屋漫游',
    flow: '交付',
    html: `
      <div class="viewer-full">
        <div class="viewer-3d">
          <div class="sky"></div>
          <div class="grid-floor"></div>
          <div class="fake-room">
            <div class="wall w1"></div><div class="wall w2"></div>
            <div class="furniture sofa"></div>
            <div class="portal">→ 主卧</div>
          </div>
          <div class="viewer-hud">
            <span>客厅</span>
            <span class="muted">Fps 60</span>
            <span>1/5 房间</span>
          </div>
          <div class="viewer-controls">
            <kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> 移动
            <span>鼠标 视角</span>
          </div>
        </div>
        <aside class="viewer-sidebar">
          <button class="btn sm ghost">← 返回总览</button>
          <h4>房间切换</h4>
          <ul class="room-jump">
            <li class="active">客厅</li><li>主卧</li><li>次卧</li><li>厨房</li><li>卫</li>
          </ul>
          <h4>显示</h4>
          <label><input type="checkbox" checked /> 家具</label>
          <label><input type="checkbox" checked /> 材质</label>
          <label><input type="checkbox" /> 线框模式</label>
          <button class="btn sm block">截图</button>
        </aside>
      </div>
    `,
  },
  {
    id: '11',
    title: '设计知识库',
    flow: '知识库',
    html: `
      ${appHeader('knowledge')}
      <div class="ui-page">
        <div class="page-head">
          <div>
            <h2>设计知识库</h2>
            <p class="muted">Obsidian Vault · ~/House-DIY-Vault · 向量索引 128 条</p>
          </div>
          <button class="btn primary">+ 导入参考</button>
        </div>
        <div class="knowledge-tabs">
          <button class="active">全部</button>
          <button>设计案例</button>
          <button>外部参考</button>
          <button>Comfy 预设</button>
        </div>
        <div class="knowledge-list">
          <article class="know-item">
            <span class="type case">案例</span>
            <div>
              <strong>望京三期 · 方案 v2</strong>
              <p class="tiny">现代简约 · 5 室 · 2026-05-19 · ★★★★</p>
            </div>
            <button class="btn sm ghost">打开 Obsidian</button>
          </article>
          <article class="know-item">
            <span class="type ref">参考</span>
            <div>
              <strong>杂志剪页 · 奶油客厅</strong>
              <p class="tiny">import_image · tags: 奶油风, 客厅</p>
            </div>
            <button class="btn sm ghost">编辑</button>
          </article>
          <article class="know-item">
            <span class="type preset">预设</span>
            <div>
              <strong>comfy · living_modern_v1</strong>
              <p class="tiny">workflow JSON 链接</p>
            </div>
          </article>
        </div>
        <button class="btn ghost">重建向量索引</button>
      </div>
    `,
  },
  {
    id: '12',
    title: '导入外部参考',
    flow: '知识库',
    html: `
      ${appHeader('knowledge')}
      <div class="ui-page narrow">
        <h2>导入外部参考</h2>
        <p class="muted">将写入 Obsidian References/ 并由 oMLX VLM 生成摘要</p>
        <div class="upload-zone sm">
          <p>PDF / PNG / JPG</p>
        </div>
        <div class="form-row">
          <label>标题</label>
          <input class="input" placeholder="例如：北欧客厅参考" />
        </div>
        <div class="form-row">
          <label>标签</label>
          <input class="input" placeholder="北欧, 客厅, 浅色" />
        </div>
        <div class="preview-box">
          <p class="tiny muted">VLM 摘要预览：</p>
          <p>大面积浅色墙面，浅橡木地板，落地窗配亚麻窗帘…</p>
        </div>
        <div class="footer-actions">
          <button class="btn ghost">取消</button>
          <button class="btn primary">导入并索引</button>
        </div>
      </div>
    `,
  },
  {
    id: '13',
    title: '系统状态与设置',
    flow: '设置',
    html: `
      ${appHeader('settings')}
      <div class="ui-page">
        <h2>系统状态</h2>
        <div class="status-grid">
          <div class="status-card ok">
            <h4>oMLX</h4>
            <p>:8000 · house-llm, house-vlm pinned</p>
            <span class="pill">运行中</span>
          </div>
          <div class="status-card ok">
            <h4>ComfyUI</h4>
            <p>:8188 · 队列空闲</p>
            <span class="pill">运行中</span>
          </div>
          <div class="status-card ok">
            <h4>House-DIY API</h4>
            <p>:8080</p>
            <span class="pill">运行中</span>
          </div>
          <div class="status-card">
            <h4>Obsidian Vault</h4>
            <p>~/House-DIY-Vault</p>
            <span class="pill muted">128 indexed</span>
          </div>
        </div>
        <h3>路径配置</h3>
        <div class="form-row"><label>Vault 路径</label><input class="input" value="~/House-DIY-Vault" /></div>
        <div class="form-row"><label>oMLX Base URL</label><input class="input" value="http://127.0.0.1:8000/v1" /></div>
        <div class="form-row"><label>ComfyUI URL</label><input class="input" value="http://127.0.0.1:8188" /></div>
        <div class="form-row"><label>GPU 串行调度</label><input type="checkbox" checked /> 同一时刻仅一个重 GPU 任务</div>
        <button class="btn primary">保存配置</button>
      </div>
    `,
  },
];

// 清理占位标签
SCREENS.forEach((s) => {
  s.html = s.html
    .replace(/<\/?motion-not-needed>/g, '')
    .replace(/\|\}/g, '');
});
