/* global Store, SCREENS, renderScreen */

function appHeader(state, active) {
  const items = [
    ['项目', 'projects', '01'],
    ['设计', 'design', '08'],
    ['知识库', 'knowledge', '11'],
    ['设置', 'settings', '13'],
  ];
  const svc = state.services;
  return `
    <header class="ui-header">
      <div class="ui-logo" data-action="nav" data-screen="01">House<span>DIY</span></div>
      <nav class="ui-tabs">
        ${items.map(([label, key, screen]) => `
          <a href="#" data-action="nav" data-screen="${screen}" class="${active === key ? 'active' : ''}">${label}</a>
        `).join('')}
      </nav>
      <div class="ui-header-right">
        <span class="badge offline">本地离线</span>
        <button type="button" class="icon-btn ${svc.omlx ? 'svc-ok' : 'svc-off'}" data-action="nav" data-screen="13" title="oMLX ${svc.omlx ? '运行中' : '离线'}">●</button>
      </div>
    </header>`;
}

function statusBadge(status) {
  const map = {
    designing: '',
    delivered: '',
    parsing: 'warn',
    review: 'warn',
    draft: 'warn',
  };
  const cls = map[status] || '';
  return cls;
}

function render01(state) {
  const q = state.searchQuery.toLowerCase();
  const filtered = state.projects.filter((p) => {
    if (state.statusFilter !== 'all' && p.status !== state.statusFilter) return false;
    if (q && !p.name.toLowerCase().includes(q)) return false;
    return true;
  });

  return `
    ${appHeader(state, 'projects')}
    <div class="ui-page">
      <div class="page-head">
        <div>
          <h2>我的户型项目</h2>
          <p class="muted">全部数据保存在本机 · 已同步 Obsidian Vault</p>
        </div>
        <button type="button" class="btn primary" data-action="new-project">+ 新建项目</button>
      </div>
      <div class="filter-row">
        <input type="search" placeholder="搜索项目名…" class="input" data-bind="search" value="${esc(state.searchQuery)}" />
        <select class="input select" data-bind="status-filter">
          <option value="all" ${state.statusFilter === 'all' ? 'selected' : ''}>全部状态</option>
          <option value="designing" ${state.statusFilter === 'designing' ? 'selected' : ''}>设计中</option>
          <option value="delivered" ${state.statusFilter === 'delivered' ? 'selected' : ''}>已完成</option>
          <option value="parsing" ${state.statusFilter === 'parsing' ? 'selected' : ''}>解析中</option>
        </select>
      </div>
      <div class="project-grid">
        ${filtered.map((p, i) => `
          <article class="project-card ${i === 0 ? 'featured' : ''}" data-action="open-project" data-id="${p.id}">
            <div class="thumb ${p.status === 'designing' || p.status === 'delivered' ? 'render' : 'floorplan'}"></div>
            <div class="card-body">
              <h3>${esc(p.name)}</h3>
              <p class="muted">${esc(p.meta)} · 上次编辑 ${Store.formatRelative(p.updatedAt)}</p>
              <div class="tags">${p.tags.map((t) => `<span class="${t === '解析中' ? 'warn' : ''}">${esc(t)}</span>`).join('')}</div>
              ${p.status === 'designing' || p.status === 'delivered' ? `
                <div class="card-actions">
                  <button type="button" class="btn sm" data-action="open-project" data-id="${p.id}">继续设计</button>
                  <button type="button" class="btn sm ghost" data-action="nav" data-screen="10">3D 漫游</button>
                </div>
              ` : ''}
            </div>
          </article>
        `).join('')}
        <article class="project-card add" data-action="new-project">
          <span>+</span>
          <p>新建项目</p>
        </article>
      </div>
    </div>`;
}

function render02(state) {
  const d = state.uploadDraft;
  return `
    ${appHeader(state, 'projects')}
    <div class="ui-page narrow">
      <div class="steps">
        <span class="done">1 上传</span><span class="active">2 解析</span><span>3 校对</span><span>4 设计</span>
      </div>
      <h2>上传标准平面图</h2>
      <p class="muted">支持开发商户型图 PNG / PDF · 建议带尺寸标注</p>
      <div class="upload-zone ${d.fileName ? 'has-file' : ''}" data-action="pick-file">
        <div class="upload-icon">↑</div>
        <p>${d.fileName ? '已选 ' + esc(d.fileName) : '拖拽文件到此处，或点击选择'}</p>
        <p class="tiny muted">最大 20MB · 将调用 oMLX VLM 解析</p>
      </div>
      <div class="form-row">
        <label>项目名称</label>
        <input class="input" data-bind="upload-name" value="${esc(d.name)}" />
      </div>
      <div class="form-row">
        <label>预估总面积（㎡，可选）</label>
        <input class="input" data-bind="upload-area" placeholder="89" value="${esc(d.area)}" />
      </div>
      ${d.fileName ? `<div class="preview-strip"><div class="mini-floor"></div><span>已选 ${esc(d.fileName)}</span></div>` : ''}
      <div class="footer-actions">
        <button type="button" class="btn ghost" data-action="nav" data-screen="01">取消</button>
        <button type="button" class="btn primary" data-action="start-parse" ${!d.fileName ? 'disabled' : ''}>开始解析 →</button>
      </div>
    </div>`;
}

function render03(state) {
  const labels = ['图像预处理与矫正', 'oMLX VLM 识别房间与门窗', 'OpenCV 提取墙线矢量', '生成 FloorPlanModel 草稿'];
  const prog = Math.round(state.parse.progress);
  return `
    ${appHeader(state, 'projects')}
    <div class="ui-page narrow center">
      <div class="steps">
        <span class="done">1 上传</span><span class="active">2 解析</span><span>3 校对</span><span>4 设计</span>
      </div>
      <div class="loader-card">
        <div class="spinner"></div>
        <h2>正在解析户型…</h2>
        <ul class="task-list">
          ${labels.map((label, i) => {
            let cls = '';
            if (i < state.parse.step) cls = 'done';
            else if (i === state.parse.step) cls = 'active';
            const icon = cls === 'done' ? '✓' : cls === 'active' ? '◐' : '○';
            return `<li class="${cls}">${icon} ${label}</li>`;
          }).join('')}
        </ul>
        <div class="progress-bar"><div style="width:${prog}%"></div></div>
        <p class="tiny muted">预计剩余 ~${Math.max(5, Math.round((100 - prog) / 3))} 秒 · GPU: oMLX VLM</p>
      </div>
    </div>`;
}

function render04(state) {
  const p = Store.currentProject();
  const rooms = p?.rooms || Store.ROOMS;
  const sel = p?.selectedRoomId || 'living';
  const room = rooms.find((r) => r.id === sel) || rooms[0];
  return `
    ${appHeader(state, 'projects')}
    <div class="editor-layout">
      <aside class="editor-tools">
        <h4>工具</h4>
        <button type="button" class="tool active" data-action="tool-select">选择</button>
        <button type="button" class="tool" data-action="toast" data-msg="墙线工具：拖拽顶点校正">墙线</button>
        <button type="button" class="tool" data-action="toast" data-msg="门洞工具：点击切换连通房间">门洞</button>
        <button type="button" class="tool" data-action="toast" data-msg="窗户工具">窗户</button>
        <button type="button" class="tool" data-action="toast" data-msg="房间标签工具">房间标签</button>
        <hr/>
        <h4>比例尺</h4>
        <p class="tiny muted">已标定 1px = 0.012m</p>
        <button type="button" class="btn sm ghost" data-action="toast" data-msg="重新标定比例尺">重新标定</button>
        <hr/>
        <h4>房间列表</h4>
        <ul class="room-list">
          ${rooms.map((r) => `
            <li class="${r.id === sel ? 'active' : ''}" data-action="select-room" data-room="${r.id}">${esc(r.name)} ${r.area}㎡</li>
          `).join('')}
        </ul>
      </aside>
      <div class="canvas-area">
        <div class="canvas-toolbar">
          <button type="button" class="btn sm ghost" data-action="toast" data-msg="已撤销">撤销</button>
          <button type="button" class="btn sm ghost" data-action="toast" data-msg="已重做">重做</button>
          <span class="muted">缩放 120%</span>
        </div>
        <div class="floor-canvas">
          <svg viewBox="0 0 400 300" class="floor-svg">
            <rect width="400" height="300" fill="#f8f4ee"/>
            <path d="M40,40 L360,40 L360,260 L40,260 Z" fill="none" stroke="#2c4a3e" stroke-width="4"/>
            <path d="M200,40 L200,180" stroke="#2c4a3e" stroke-width="3"/>
            <path d="M40,180 L360,180" stroke="#2c4a3e" stroke-width="3"/>
            <rect x="190" y="170" width="20" height="12" fill="#c4a574"/>
            <text x="100" y="120" class="room-label">${room?.id === 'living' ? '客厅' : esc(room?.name || '')}</text>
            <text x="270" y="100" class="room-label">主卧</text>
          </svg>
          <span class="anno">拖拽顶点校正墙线 · 点击门洞切换连通房间</span>
        </div>
      </div>
      <aside class="editor-inspector">
        <h4>选中：${esc(room?.name || '')}</h4>
        <div class="form-row"><label>面积</label><input class="input" value="${room?.area || ''}" readonly /> ㎡</div>
        <div class="form-row"><label>连通</label><span>${esc(room?.connects || '')}</span></div>
        <button type="button" class="btn primary block" data-action="confirm-floorplan">确认户型，进入设计 →</button>
      </aside>
    </div>`;
}

function render05(state) {
  return `
    ${appHeader(state, 'design')}
    <div class="design-layout">
      <section class="design-main">
        <div class="steps inline">
          <span class="done">户型已确认</span><span class="active">描述需求</span><span>生成</span>
        </div>
        <h2>描述你的理想之家</h2>
        <textarea class="input area" rows="6" data-bind="design-brief" placeholder="例如：现代简约、暖白墙面…">${esc(state.designBrief)}</textarea>
        <div class="chips">
          ${['现代简约', '北欧', '新中式', '轻奢', '奶油风'].map((c) => `
            <span data-action="style-chip" data-chip="${c}">${c}</span>
          `).join('')}
        </div>
        <div class="option-row">
          <label><input type="checkbox" checked disabled /> 参考历史案例 (RAG)</label>
          <label><input type="checkbox" checked disabled /> 生成后写入 Obsidian</label>
        </div>
        <button type="button" class="btn primary lg" data-action="start-generation">生成全屋方案 →</button>
      </section>
      <aside class="rag-panel">
        <h4>📚 相似案例（Obsidian RAG）</h4>
        ${Store.RAG_CASES.map((c) => `
          <article class="rag-card" data-action="toast" data-msg="打开案例：${esc(c.title)}">
            <strong>${esc(c.title)}</strong>
            <p class="tiny">${esc(c.desc)}</p>
            <span class="score">相似度 ${c.score}</span>
          </article>
        `).join('')}
        <a href="#" class="link" data-action="nav" data-screen="11">查看全部知识库 →</a>
        <hr/>
        <h4>将使用</h4>
        <ul class="tiny muted">
          <li>oMLX → DesignSpec</li>
          <li>ComfyUI → 5 房间效果图</li>
          <li>Scene Builder → 全屋 3D</li>
        </ul>
      </aside>
    </div>`;
}

function render06(state) {
  const pl = state.pipeline;
  const pipeSteps = [
    { key: 'designSpec', title: 'DesignSpec', desc: '5 房间 · 已写入 Specs/' },
    { key: 'render2d', title: '2D 效果图', desc: 'ComfyUI · 客厅 2/3' },
    { key: 'scene3d', title: '3D 场景构建', desc: 'Scene Builder' },
    { key: 'obsidian', title: 'Obsidian 案例', desc: '摘要 + 索引' },
  ];
  const slotLabels = ['客厅', '主卧', '次卧', '厨房', '卫生间'];
  return `
    ${appHeader(state, 'design')}
    <div class="ui-page">
      <h2>正在生成全屋方案</h2>
      <p class="muted">任务队列串行 GPU · 请勿关闭本机 oMLX / ComfyUI</p>
      <div class="pipeline">
        ${pipeSteps.map((s) => {
          const st = pl.stepStatus[s.key];
          const icon = st === 'done' ? '✓' : st === 'active' ? '◐' : '○';
          return `
            <div class="pipe-step ${st}">
              <span class="icon">${icon}</span>
              <div><strong>${s.title}</strong><p class="tiny">${s.desc}</p>
                ${st === 'active' && s.key === 'render2d' ? `<div class="mini-progress"><div style="width:${Math.round(pl.progress)}%"></div></div>` : ''}
              </div>
            </div>`;
        }).join('')}
      </div>
      <div class="live-preview">
        ${pl.renderSlots.map((st, i) => `
          <div class="render-slot ${st}"><span>${slotLabels[i]}${st === 'active' ? '…' : ''}</span></div>
        `).join('')}
      </div>
      <button type="button" class="btn ghost" data-action="toast" data-msg="任务已在后台运行">后台运行</button>
    </div>`;
}

function render07(state) {
  const p = Store.currentProject();
  const rooms = p?.rooms || Store.ROOMS;
  return `
    ${appHeader(state, 'design')}
    <div class="refine-layout">
      <section class="refine-context">
        <div class="page-head" style="margin-bottom:1rem;">
          <div>
            <h2>方案微调</h2>
            <p class="muted">${esc(p?.name || '')} · 方案 v${p?.specVersion || 1} · DesignSpec 已锁定户型几何</p>
          </div>
          <span class="badge offline">POST /design/refine</span>
        </div>
        <div class="spec-snapshot">
          <h4>当前方案摘要</h4>
          <p class="tiny muted">globalStyle</p>
          <p><strong>现代简约</strong> · 暖白墙面 · 浅橡木地面</p>
          <ul class="room-spec-list">
            ${rooms.slice(0, 4).map((r, i) => `
              <li class="${i === 0 ? 'active' : ''}"><span>${esc(r.name)}</span><em>${i === 0 ? 'L 型沙发 · 南向采光' : i === 1 ? '深灰床头 · 安静色系' : i === 2 ? '白色橱柜 · 石英石台面' : '书桌靠窗'}</em></li>
            `).join('')}
          </ul>
          <button type="button" class="btn sm ghost block" data-action="toast" data-msg="DesignSpec JSON 已复制到剪贴板（模拟）">查看完整 DesignSpec JSON</button>
        </div>
        <div class="refine-history">
          <h4>本轮对话</h4>
          ${(p?.refineHistory || []).map((m) => `
            <div class="chat-bubble ${m.role} ${m.role === 'ai' ? 'tiny' : ''}">${esc(m.text)}</div>
          `).join('')}
        </div>
      </section>
      <section class="refine-input">
        <div class="steps inline">
          <span class="done">已生成</span><span class="active">自然语言微调</span><span>增量渲染</span>
        </div>
        <h3>描述你想调整的内容</h3>
        <p class="muted tiny">LLM 在现有 DesignSpec 上生成 patch，不修改 FloorPlanModel</p>
        <textarea class="input area" rows="5" data-bind="refine-input" placeholder="例如：客厅沙发换更大浅灰布艺…">${esc(state.refineInput)}</textarea>
        <div class="chips">
          ${['换家具', '改配色', '调灯光', '换材质', '单房间重做'].map((c) => `
            <span data-action="append-refine" data-text="${c}">${c}</span>
          `).join('')}
        </div>
        <div class="scope-box">
          <h4>增量更新范围</h4>
          <label><input type="checkbox" checked disabled /> DesignSpec（LLM patch）</label>
          <label><input type="checkbox" checked disabled /> 受影响房间 2D（ComfyUI）</label>
          <label><input type="checkbox" checked disabled /> 受影响房间 3D（Scene Builder）</label>
          <label><input type="checkbox" /> 更新 Obsidian 案例备注</label>
        </div>
        <div class="footer-actions" style="justify-content:flex-start;">
          <button type="button" class="btn primary" data-action="preview-refine">解析并预览变更 →</button>
          <button type="button" class="btn ghost" data-action="clear-refine">清空输入</button>
        </div>
      </section>
      <aside class="refine-preview">
        <h4>变更预览（待确认）</h4>
        <ul class="diff-list">
          ${(p?.refineDiff || []).map((d) => `
            <li><span class="diff-tag ${d.tag}">${d.tag === 'mod' ? '修改' : '重渲染'}</span> ${esc(d.text)}</li>
          `).join('')}
        </ul>
        <p class="tiny muted">ComfyUI 串行 2 房间 · 约 8 分钟</p>
        <button type="button" class="btn primary block" data-action="apply-refine">应用微调并重新生成</button>
        <button type="button" class="btn ghost block" data-action="nav" data-screen="08">放弃，保持原方案</button>
        <hr/>
        <p class="tiny muted">不移动墙体 · 不挡门洞 · RAG 仅风格参考</p>
      </aside>
    </div>`;
}

function render08(state) {
  const p = Store.currentProject();
  return `
    ${appHeader(state, 'design')}
    <div class="ui-page">
      <div class="page-head">
        <div>
          <h2>${esc(p?.name || '项目')} · 方案 v${p?.specVersion || 1}</h2>
          <p class="muted">现代简约 · 生成于今天 · 已同步 Obsidian</p>
        </div>
        <div class="btn-group">
          <button type="button" class="btn ghost" data-action="nav" data-screen="07">微调方案</button>
          <button type="button" class="btn ghost" data-action="nav" data-screen="05">重新生成</button>
          <button type="button" class="btn primary" data-action="nav" data-screen="10">进入 3D 漫游</button>
        </div>
      </div>
      <div class="delivery-hero">
        <div class="hero-3d">
          <div class="fake-3d" data-action="nav" data-screen="10">
            <span class="room-badge">客厅</span>
            <p>WASD 漫游 · 门口切换房间</p>
          </div>
          <button type="button" class="btn primary" data-action="nav" data-screen="10">▶ 打开全屋 3D</button>
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
          <a href="#" class="link" data-action="toast" data-msg="已在 Obsidian 打开案例笔记">在 Obsidian 中打开案例笔记</a>
        </div>
      </div>
      <h3>2D 效果图速览</h3>
      <div class="render-grid sm">
        ${['客厅 A', '客厅 B', '主卧', '次卧', '厨房'].map((label) => `
          <div class="render-thumb" data-action="nav" data-screen="09"><span>${label}</span></div>
        `).join('')}
      </div>
    </div>`;
}

function render09(state) {
  const p = Store.currentProject();
  const roomIds = ['living', 'master', 'second', 'kitchen', 'bath'];
  const roomNames = { living: '客厅', master: '主卧', second: '次卧', kitchen: '厨房', bath: '卫生间' };
  const renders = p?.renders?.[state.galleryRoom] || [{ label: '预览', prompt: 'interior render' }];
  const current = renders[state.galleryIndex] || renders[0];
  return `
    ${appHeader(state, 'design')}
    <div class="ui-page">
      <div class="gallery-layout">
        <aside class="room-nav">
          ${roomIds.map((id) => `
            <button type="button" class="${state.galleryRoom === id ? 'active' : ''}" data-action="gallery-room" data-room="${id}">${roomNames[id]}</button>
          `).join('')}
        </aside>
        <section class="gallery-main">
          <div class="big-render"><span class="render-label">${esc(current.label)}</span></div>
          <div class="thumb-row">
            ${renders.map((r, i) => `
              <div class="t ${i === state.galleryIndex ? 'active' : ''}" data-action="gallery-thumb" data-index="${i}"></div>
            `).join('')}
          </div>
          <div class="meta-bar">
            <span>ComfyUI · living_modern_v1</span>
            <button type="button" class="btn sm ghost" data-action="toast" data-msg="已入队重生成此房间">仅重生成此房间</button>
            <button type="button" class="btn sm ghost" data-action="toast" data-msg="已下载 PNG">下载</button>
          </div>
          <details class="prompt-details" open>
            <summary>查看 Prompt / DesignSpec 片段</summary>
            <pre>${esc(current.prompt)}</pre>
          </details>
        </section>
      </div>
    </div>`;
}

function render10(state) {
  const roomIds = ['living', 'master', 'second', 'kitchen', 'bath'];
  const roomNames = { living: '客厅', master: '主卧', second: '次卧', kitchen: '厨房', bath: '卫生间' };
  const idx = roomIds.indexOf(state.viewer3dRoom);
  const pos = state.viewer3dPos;
  const nextRoom = roomIds[(idx + 1) % roomIds.length];
  return `
    <div class="viewer-full">
      <div class="viewer-3d" tabindex="0" data-action="viewer-focus">
        <div class="sky"></div>
        <div class="grid-floor"></div>
        <div class="fake-room">
          <div class="wall w1"></div><div class="wall w2"></div>
          <div class="furniture sofa" style="left:${pos.x}%;top:${pos.y}%"></div>
          <div class="portal" data-action="viewer-next-room">→ ${roomNames[nextRoom]}</div>
        </div>
        <div class="viewer-hud">
          <span>${roomNames[state.viewer3dRoom]}</span>
          <span class="muted">Fps 60</span>
          <span>${idx + 1}/5 房间</span>
        </div>
        <div class="viewer-controls">
          <kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> 移动
          <span>鼠标 视角</span>
        </div>
      </div>
      <aside class="viewer-sidebar">
        <button type="button" class="btn sm ghost" data-action="nav" data-screen="08">← 返回总览</button>
        <h4>房间切换</h4>
        <ul class="room-jump">
          ${roomIds.map((id) => `
            <li class="${state.viewer3dRoom === id ? 'active' : ''}" data-action="viewer-room" data-room="${id}">${roomNames[id]}</li>
          `).join('')}
        </ul>
        <h4>显示</h4>
        <label><input type="checkbox" checked /> 家具</label>
        <label><input type="checkbox" checked /> 材质</label>
        <label><input type="checkbox" /> 线框模式</label>
        <button type="button" class="btn sm block" data-action="toast" data-msg="截图已保存">截图</button>
      </aside>
    </div>`;
}

function render11(state) {
  const tabs = [
    ['all', '全部'],
    ['case', '设计案例'],
    ['ref', '外部参考'],
    ['preset', 'Comfy 预设'],
  ];
  const typeLabel = { case: '案例', ref: '参考', preset: '预设' };
  const filtered = state.knowledge.filter((k) =>
    state.knowledgeTab === 'all' || k.type === state.knowledgeTab
  );
  return `
    ${appHeader(state, 'knowledge')}
    <div class="ui-page">
      <div class="page-head">
        <div>
          <h2>设计知识库</h2>
          <p class="muted">Obsidian Vault · ~/House-DIY-Vault · 向量索引 ${128 + state.knowledge.length} 条</p>
        </div>
        <button type="button" class="btn primary" data-action="nav" data-screen="12">+ 导入参考</button>
      </div>
      <div class="knowledge-tabs">
        ${tabs.map(([key, label]) => `
          <button type="button" class="${state.knowledgeTab === key ? 'active' : ''}" data-action="knowledge-tab" data-tab="${key}">${label}</button>
        `).join('')}
      </div>
      <div class="knowledge-list">
        ${filtered.map((k) => `
          <article class="know-item">
            <span class="type ${k.type}">${typeLabel[k.type]}</span>
            <div>
              <strong>${esc(k.title)}</strong>
              <p class="tiny">${esc(k.meta)}</p>
            </div>
            <button type="button" class="btn sm ghost" data-action="toast" data-msg="打开：${esc(k.title)}">${k.type === 'ref' ? '编辑' : '打开 Obsidian'}</button>
          </article>
        `).join('')}
      </div>
      <button type="button" class="btn ghost" data-action="rebuild-index">重建向量索引</button>
    </div>`;
}

function render12(state) {
  const d = state.importDraft;
  return `
    ${appHeader(state, 'knowledge')}
    <div class="ui-page narrow">
      <h2>导入外部参考</h2>
      <p class="muted">将写入 Obsidian References/ 并由 oMLX VLM 生成摘要</p>
      <div class="upload-zone sm" data-action="toast" data-msg="已选择参考图片（模拟）">
        <p>PDF / PNG / JPG · 点击选择</p>
      </div>
      <div class="form-row">
        <label>标题</label>
        <input class="input" data-bind="import-title" placeholder="例如：北欧客厅参考" value="${esc(d.title)}" />
      </div>
      <div class="form-row">
        <label>标签</label>
        <input class="input" data-bind="import-tags" placeholder="北欧, 客厅, 浅色" value="${esc(d.tags)}" />
      </div>
      <div class="preview-box">
        <p class="tiny muted">VLM 摘要预览：</p>
        <p>${d.summary || '输入标题后自动生成摘要…'}</p>
      </div>
      <div class="footer-actions">
        <button type="button" class="btn ghost" data-action="nav" data-screen="11">取消</button>
        <button type="button" class="btn primary" data-action="import-ref">导入并索引</button>
      </div>
    </div>`;
}

function render13(state) {
  const s = state.settings;
  const svc = state.services;
  return `
    ${appHeader(state, 'settings')}
    <div class="ui-page">
      <h2>系统状态</h2>
      <div class="status-grid">
        <div class="status-card ${svc.omlx ? 'ok' : ''}">
          <h4>oMLX</h4>
          <p>:8000 · house-llm, house-vlm</p>
          <span class="pill">${svc.omlx ? '运行中' : '离线'}</span>
        </div>
        <div class="status-card ${svc.comfy ? 'ok' : ''}">
          <h4>ComfyUI</h4>
          <p>:8188 · 队列空闲</p>
          <span class="pill">${svc.comfy ? '运行中' : '离线'}</span>
        </div>
        <div class="status-card ${svc.api ? 'ok' : ''}">
          <h4>House-DIY API</h4>
          <p>:8080</p>
          <span class="pill ${svc.api ? '' : 'muted'}">${svc.api ? '运行中' : '未启动'}</span>
        </div>
        <div class="status-card ok">
          <h4>Obsidian Vault</h4>
          <p>${esc(s.vaultPath)}</p>
          <span class="pill muted">128 indexed</span>
        </div>
      </div>
      <h3>路径配置</h3>
      <div class="form-row"><label>Vault 路径</label><input class="input" data-bind="setting-vault" value="${esc(s.vaultPath)}" /></div>
      <div class="form-row"><label>oMLX Base URL</label><input class="input" data-bind="setting-omlx" value="${esc(s.omlxUrl)}" /></div>
      <div class="form-row"><label>ComfyUI URL</label><input class="input" data-bind="setting-comfy" value="${esc(s.comfyUrl)}" /></div>
      <div class="form-row"><label>GPU 串行调度</label><input type="checkbox" checked disabled /> 同一时刻仅一个重 GPU 任务</div>
      <div class="footer-actions">
        <button type="button" class="btn primary" data-action="save-settings">保存配置</button>
        <button type="button" class="btn ghost" data-action="reset-demo">重置演示数据</button>
      </div>
    </div>`;
}

function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const SCREEN_RENDERERS = {
  '01': render01,
  '02': render02,
  '03': render03,
  '04': render04,
  '05': render05,
  '06': render06,
  '07': render07,
  '08': render08,
  '09': render09,
  '10': render10,
  '11': render11,
  '12': render12,
  '13': render13,
};

const SCREENS = [
  { id: '01', title: '项目列表', flow: '入口' },
  { id: '02', title: '新建项目 · 上传户型', flow: '上传' },
  { id: '03', title: '户型 AI 解析中', flow: '上传' },
  { id: '04', title: '户型 2D 校对编辑器', flow: '校对' },
  { id: '05', title: '设计描述 · RAG 参考', flow: '设计' },
  { id: '06', title: '方案生成进度', flow: '生成' },
  { id: '07', title: '方案微调', flow: '微调' },
  { id: '08', title: '方案交付总览', flow: '交付' },
  { id: '09', title: '2D 效果图画廊', flow: '交付' },
  { id: '10', title: '3D 全屋漫游', flow: '交付' },
  { id: '11', title: '设计知识库', flow: '知识库' },
  { id: '12', title: '导入外部参考', flow: '知识库' },
  { id: '13', title: '系统状态与设置', flow: '设置' },
];

function renderScreen(screenId, state) {
  const fn = SCREEN_RENDERERS[screenId];
  return fn ? fn(state || Store.getState()) : '';
}

// 兼容 overview：动态 html
SCREENS.forEach((s) => {
  Object.defineProperty(s, 'html', {
    get() { return renderScreen(s.id, Store.getState()); },
    enumerable: true,
  });
});
