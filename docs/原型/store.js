/* global Store */
(function () {
  const STORAGE_KEY = 'houseDiyProtoState';

  const ROOMS = [
    { id: 'living', name: '客厅', area: 28.2, connects: '主卧、玄关' },
    { id: 'master', name: '主卧', area: 14, connects: '客厅' },
    { id: 'second', name: '次卧', area: 10, connects: '客厅' },
    { id: 'kitchen', name: '厨房', area: 6, connects: '客厅' },
    { id: 'bath', name: '卫生间', area: 4, connects: '玄关' },
  ];

  const RAG_CASES = [
    { title: '案例 · 89㎡ 三居简约', desc: '客厅南向采光、浅橡木地板…', score: 0.87 },
    { title: '参考 · 杂志剪页 #12', desc: '奶油风客厅，弧形沙发…', score: 0.72 },
    { title: '案例 · 两居北欧', desc: '白色墙面 + 浅灰沙发…', score: 0.65 },
  ];

  const KNOWLEDGE = [
    { id: 'k1', type: 'case', title: '望京三期 · 方案 v2', meta: '现代简约 · 5 室 · 2026-05-19 · ★★★★' },
    { id: 'k2', type: 'ref', title: '杂志剪页 · 奶油客厅', meta: 'import_image · tags: 奶油风, 客厅' },
    { id: 'k3', type: 'preset', title: 'comfy · living_modern_v1', meta: 'workflow JSON 链接' },
  ];

  const RENDERS = {
    living: [
      { id: 'lr1', label: '客厅 A', prompt: 'modern living room, warm white walls, oak floor, interior style' },
      { id: 'lr2', label: '客厅 B', prompt: 'living room evening light, interior, cozy sofa' },
    ],
    master: [{ id: 'mb1', label: '主卧', prompt: 'master bedroom, dark grey headboard, interior' }],
    second: [{ id: 'sr1', label: '次卧', prompt: 'secondary bedroom, desk by window, interior' }],
    kitchen: [{ id: 'kt1', label: '厨房', prompt: 'white kitchen cabinets, quartz countertop, interior' }],
    bath: [{ id: 'bt1', label: '卫生间', prompt: 'modern bathroom, clean tiles, interior' }],
  };

  function defaultState() {
    return {
      screen: '01',
      projects: [
        {
          id: 'p1',
          name: '望京三期 · 89㎡ 三居室',
          meta: '3 室 2 厅 · 89㎡',
          status: 'designing',
          statusLabel: '设计中',
          tags: ['已校对', '方案 v2'],
          updatedAt: Date.now() - 2 * 3600000,
          brief: '现代简约风格，整体暖白与浅橡木。客厅明亮通透，沙发靠墙；主卧安静，深灰床头；厨房白色橱柜配石英石台面。',
          specVersion: 2,
          rooms: JSON.parse(JSON.stringify(ROOMS)),
          selectedRoomId: 'living',
          renders: JSON.parse(JSON.stringify(RENDERS)),
          refineHistory: [
            { role: 'user', text: '主卧床头改成深灰色软包，窗帘换亚麻米色' },
            { role: 'ai', text: '将更新 master_bedroom 材质与家具字段…' },
          ],
          refineDiff: [
            { tag: 'mod', text: '客厅 · coffee_table → 圆形茶几' },
            { tag: 'mod', text: '主卧 · 新增壁灯 lighting.bedside' },
            { tag: 'mod', text: 'globalStyle · palette 略向暖色' },
            { tag: 'regen', text: '客厅 2D · 主卧 2D + 3D' },
          ],
        },
        {
          id: 'p2',
          name: '草稿 · 两居室',
          meta: '待校对户型',
          status: 'parsing',
          statusLabel: '解析中',
          tags: ['解析中'],
          updatedAt: Date.now() - 86400000,
          brief: '',
          specVersion: 0,
          rooms: [],
          selectedRoomId: 'living',
          renders: {},
          refineHistory: [],
          refineDiff: [],
        },
      ],
      currentProjectId: 'p1',
      uploadDraft: { name: '望京三期 89㎡', area: '89', fileName: '' },
      parse: { running: false, progress: 0, step: 0 },
      pipeline: {
        running: false,
        progress: 0,
        steps: ['designSpec', 'render2d', 'scene3d', 'obsidian'],
        stepStatus: { designSpec: 'done', render2d: 'pending', scene3d: 'pending', obsidian: 'pending' },
        renderSlots: ['pending', 'pending', 'pending', 'pending', 'pending'],
      },
      designBrief: '现代简约风格，整体暖白与浅橡木。客厅明亮通透，沙发靠墙；主卧安静，深灰床头；厨房白色橱柜配石英石台面。预算感中等，适合三口之家。',
      refineInput: '客厅茶几换圆形小茶几，主卧增加床头暖光壁灯，整体再偏暖一点。',
      galleryRoom: 'living',
      galleryIndex: 0,
      viewer3dRoom: 'living',
      viewer3dPos: { x: 50, y: 50 },
      knowledge: JSON.parse(JSON.stringify(KNOWLEDGE)),
      knowledgeTab: 'all',
      importDraft: { title: '', tags: '', summary: '' },
      settings: {
        vaultPath: '~/House-DIY-Vault',
        omlxUrl: 'http://127.0.0.1:8000/v1',
        comfyUrl: 'http://127.0.0.1:8188',
        serialGpu: true,
      },
      services: { omlx: true, comfy: true, api: false },
      toast: null,
      searchQuery: '',
      statusFilter: 'all',
    };
  }

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return { ...defaultState(), ...JSON.parse(raw) };
    } catch (_) { /* ignore */ }
    return defaultState();
  }

  let state = load();
  const listeners = [];

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (_) { /* ignore */ }
  }

  function notify() {
    persist();
    listeners.forEach((fn) => fn(state));
  }

  function getProject(id) {
    return state.projects.find((p) => p.id === id);
  }

  function currentProject() {
    return getProject(state.currentProjectId);
  }

  function formatRelative(ts) {
    const diff = Date.now() - ts;
    if (diff < 3600000) return `${Math.max(1, Math.floor(diff / 60000))} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
    return `${Math.floor(diff / 86400000)} 天前`;
  }

  Store = {
    getState: () => state,
    subscribe(fn) {
      listeners.push(fn);
      return () => listeners.splice(listeners.indexOf(fn), 1);
    },
    setScreen(id) {
      state.screen = id;
      notify();
    },
    showToast(message, type) {
      state.toast = { message, type: type || 'info', at: Date.now() };
      notify();
      setTimeout(() => {
        if (state.toast && state.toast.message === message) {
          state.toast = null;
          notify();
        }
      }, 2800);
    },
    setSearch(q) {
      state.searchQuery = q;
      notify();
    },
    setStatusFilter(f) {
      state.statusFilter = f;
      notify();
    },
    selectProject(id) {
      state.currentProjectId = id;
      const p = getProject(id);
      if (p.status === 'draft') state.screen = '02';
      else if (p.status === 'parsing') state.screen = '03';
      else if (p.status === 'review') state.screen = '04';
      else if (p.status === 'designing') state.screen = '08';
      else state.screen = '01';
      notify();
    },
    startNewProject() {
      state.uploadDraft = { name: '新建项目', area: '', fileName: '' };
      state.screen = '02';
      notify();
    },
    updateUploadDraft(field, value) {
      state.uploadDraft[field] = value;
      notify();
    },
    simulateFilePick() {
      state.uploadDraft.fileName = 'sample_floorplan.png';
      Store.showToast('已选择 sample_floorplan.png');
      notify();
    },
    startParse() {
      const name = state.uploadDraft.name.trim() || '未命名项目';
      const id = 'p' + Date.now();
      state.projects.unshift({
        id,
        name,
        meta: state.uploadDraft.area ? `${state.uploadDraft.area}㎡` : '待校对',
        status: 'parsing',
        statusLabel: '解析中',
        tags: ['解析中'],
        updatedAt: Date.now(),
        brief: '',
        specVersion: 0,
        rooms: [],
        selectedRoomId: 'living',
        renders: {},
        refineHistory: [],
        refineDiff: [],
      });
      state.currentProjectId = id;
      state.parse = { running: true, progress: 0, step: 0 };
      state.screen = '03';
      notify();
    },
    tickParse() {
      if (!state.parse.running) return false;
      state.parse.progress = Math.min(100, state.parse.progress + 8 + Math.random() * 6);
      state.parse.step = Math.min(3, Math.floor(state.parse.progress / 25));
      if (state.parse.progress >= 100) {
        state.parse.running = false;
        const p = currentProject();
        if (p) {
          p.status = 'review';
          p.statusLabel = '待校对';
          p.tags = ['待校对'];
          p.rooms = JSON.parse(JSON.stringify(ROOMS));
          p.updatedAt = Date.now();
        }
        state.screen = '04';
      }
      notify();
      return state.parse.running;
    },
    confirmFloorplan() {
      const p = currentProject();
      if (!p) return;
      p.status = 'designing';
      p.statusLabel = '设计中';
      p.tags = ['已校对'];
      p.updatedAt = Date.now();
      state.designBrief = p.brief || state.designBrief;
      state.screen = '05';
      Store.showToast('户型已确认，进入设计描述');
      notify();
    },
    selectEditorRoom(roomId) {
      const p = currentProject();
      if (p) p.selectedRoomId = roomId;
      notify();
    },
    setDesignBrief(text) {
      state.designBrief = text;
      notify();
    },
    appendStyleChip(chip) {
      if (!state.designBrief.includes(chip)) {
        state.designBrief = (state.designBrief.trim() + '，' + chip).replace(/^，/, '');
        notify();
      }
    },
    startGeneration() {
      const p = currentProject();
      if (p) {
        p.brief = state.designBrief;
        p.specVersion += 1;
        p.tags = ['已校对', `方案 v${p.specVersion}`];
      }
      state.pipeline = {
        running: true,
        progress: 0,
        steps: ['designSpec', 'render2d', 'scene3d', 'obsidian'],
        stepStatus: { designSpec: 'active', render2d: 'pending', scene3d: 'pending', obsidian: 'pending' },
        renderSlots: ['pending', 'pending', 'pending', 'pending', 'pending'],
      };
      state.screen = '06';
      notify();
    },
    tickPipeline() {
      if (!state.pipeline.running) return false;
      state.pipeline.progress = Math.min(100, state.pipeline.progress + 5 + Math.random() * 4);
      const p = state.pipeline.progress;
      if (p > 15) state.pipeline.stepStatus.designSpec = 'done';
      if (p > 20) state.pipeline.stepStatus.render2d = 'active';
      if (p > 55) {
        state.pipeline.stepStatus.render2d = 'done';
        state.pipeline.stepStatus.scene3d = 'active';
      }
      if (p > 75) {
        state.pipeline.stepStatus.scene3d = 'done';
        state.pipeline.stepStatus.obsidian = 'active';
      }
      const slotDone = Math.floor(p / 20);
      state.pipeline.renderSlots = state.pipeline.renderSlots.map((_, i) =>
        i < slotDone ? 'done' : i === slotDone ? 'active' : 'pending'
      );
      if (p >= 100) {
        state.pipeline.running = false;
        state.pipeline.stepStatus.obsidian = 'done';
        const proj = currentProject();
        if (proj) {
          proj.renders = JSON.parse(JSON.stringify(RENDERS));
          proj.status = 'delivered';
          proj.statusLabel = '已完成';
          proj.updatedAt = Date.now();
        }
        state.screen = '08';
        Store.showToast('全屋方案生成完成');
      }
      notify();
      return state.pipeline.running;
    },
    setRefineInput(text) {
      state.refineInput = text;
      notify();
    },
    previewRefine() {
      Store.showToast('已解析微调意图，请确认右侧预览');
      notify();
    },
    applyRefine() {
      const p = currentProject();
      if (p) {
        p.refineHistory.push({ role: 'user', text: state.refineInput });
        p.refineHistory.push({ role: 'ai', text: '已应用 patch 并入队增量渲染…' });
        p.updatedAt = Date.now();
      }
      state.refineInput = '';
      Store.showToast('微调已应用，正在增量渲染');
      Store.startGeneration();
    },
    setGalleryRoom(roomId) {
      state.galleryRoom = roomId;
      state.galleryIndex = 0;
      notify();
    },
    setGalleryIndex(i) {
      state.galleryIndex = i;
      notify();
    },
    setViewer3dRoom(roomId) {
      state.viewer3dRoom = roomId;
      notify();
    },
    moveViewer3d(dx, dy) {
      state.viewer3dPos.x = Math.max(10, Math.min(90, state.viewer3dPos.x + dx));
      state.viewer3dPos.y = Math.max(10, Math.min(90, state.viewer3dPos.y + dy));
      notify();
    },
    setKnowledgeTab(tab) {
      state.knowledgeTab = tab;
      notify();
    },
    updateImportDraft(field, value) {
      state.importDraft[field] = value;
      if (field === 'title' && value.length > 2) {
        state.importDraft.summary = '大面积浅色墙面，浅橡木地板，落地窗配亚麻窗帘…';
      }
      notify();
    },
    importReference() {
      const { title, tags } = state.importDraft;
      if (!title.trim()) {
        Store.showToast('请填写标题', 'warn');
        return;
      }
      state.knowledge.unshift({
        id: 'k' + Date.now(),
        type: 'ref',
        title: title.trim(),
        meta: `import_image · tags: ${tags || '参考'}`,
      });
      state.importDraft = { title: '', tags: '', summary: '' };
      Store.showToast('已导入并写入向量索引');
      state.screen = '11';
      notify();
    },
    saveSettings() {
      Store.showToast('配置已保存（模拟）');
      notify();
    },
    rebuildIndex() {
      Store.showToast('向量索引重建完成 · 131 条');
      notify();
    },
    resetDemo() {
      state = defaultState();
      localStorage.removeItem(STORAGE_KEY);
      notify();
      Store.showToast('已重置演示数据');
    },
    formatRelative,
    currentProject,
    getProject,
    ROOMS,
    RAG_CASES,
  };
})();
