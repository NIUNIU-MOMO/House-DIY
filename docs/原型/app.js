(function () {
  const listEl = document.getElementById('screenList');
  const viewport = document.getElementById('screenViewport');
  const screenIdEl = document.getElementById('screenId');
  const screenTitleEl = document.getElementById('screenTitle');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const servicePill = document.querySelector('.service-pill');

  let parseTimer = null;
  let pipelineTimer = null;
  let focusedInput = null;

  function screenIndex() {
    const id = Store.getState().screen;
    return SCREENS.findIndex((s) => s.id === id);
  }

  function renderNav() {
    const current = screenIndex();
    listEl.innerHTML = SCREENS.map((s, i) => `
      <button type="button" class="screen-link${i === current ? ' active' : ''}" data-index="${i}">
        <span class="num">${s.id}</span>
        <span class="label">${s.title}</span>
        <span class="flow">${s.flow}</span>
      </button>
    `).join('');

    listEl.querySelectorAll('.screen-link').forEach((btn) => {
      btn.addEventListener('click', () => goToIndex(Number(btn.dataset.index)));
    });
  }

  function updateServicePill(state) {
    if (!servicePill) return;
    const dots = servicePill.querySelectorAll('.dot');
    if (dots[0]) dots[0].className = 'dot ' + (state.services.omlx ? 'ok' : 'warn');
    if (dots[1]) dots[1].className = 'dot ' + (state.services.comfy ? 'ok' : 'warn');
    if (dots[2]) dots[2].className = 'dot ' + (state.services.api ? 'ok' : 'warn');
  }

  function renderToast(state) {
    let el = document.getElementById('protoToast');
    if (!state.toast) {
      if (el) el.remove();
      return;
    }
    if (!el) {
      el = document.createElement('div');
      el.id = 'protoToast';
      el.className = 'proto-toast';
      document.body.appendChild(el);
    }
    el.className = 'proto-toast ' + (state.toast.type || 'info');
    el.textContent = state.toast.message;
  }

  function renderApp() {
    const state = Store.getState();
    const screen = SCREENS.find((s) => s.id === state.screen) || SCREENS[0];
    screenIdEl.textContent = screen.id;
    screenTitleEl.textContent = screen.title;
    viewport.innerHTML = renderScreen(screen.id, state);
    renderNav();
    updateServicePill(state);
    renderToast(state);
    viewport.scrollTop = 0;
    manageTimers(state);
    restoreFocus();
  }

  function restoreFocus() {
    if (!focusedInput) return;
    const el = viewport.querySelector(`[data-bind="${focusedInput}"]`);
    if (el) {
      el.focus();
      if (el.setSelectionRange && el.value) {
        el.setSelectionRange(el.value.length, el.value.length);
      }
    }
  }

  function manageTimers(state) {
    if (state.screen === '03' && state.parse.running) {
      if (!parseTimer) {
        parseTimer = setInterval(() => {
          if (!Store.tickParse()) clearInterval(parseTimer);
          parseTimer = null;
        }, 400);
      }
    } else if (parseTimer) {
      clearInterval(parseTimer);
      parseTimer = null;
    }

    if (state.screen === '06' && state.pipeline.running) {
      if (!pipelineTimer) {
        pipelineTimer = setInterval(() => {
          if (!Store.tickPipeline()) clearInterval(pipelineTimer);
          pipelineTimer = null;
        }, 500);
      }
    } else if (pipelineTimer) {
      clearInterval(pipelineTimer);
      pipelineTimer = null;
    }
  }

  function goToIndex(index) {
    const s = SCREENS[(index + SCREENS.length) % SCREENS.length];
    Store.setScreen(s.id);
  }

  function handleAction(action, el, event) {
    switch (action) {
      case 'nav':
        event.preventDefault();
        Store.setScreen(el.dataset.screen);
        break;
      case 'new-project':
        Store.startNewProject();
        break;
      case 'open-project':
        Store.selectProject(el.dataset.id);
        break;
      case 'pick-file':
        Store.simulateFilePick();
        break;
      case 'start-parse':
        Store.startParse();
        break;
      case 'confirm-floorplan':
        Store.confirmFloorplan();
        break;
      case 'select-room':
        Store.selectEditorRoom(el.dataset.room);
        break;
      case 'start-generation':
        Store.startGeneration();
        break;
      case 'style-chip':
        Store.appendStyleChip(el.dataset.chip);
        break;
      case 'preview-refine':
        Store.previewRefine();
        break;
      case 'clear-refine':
        Store.setRefineInput('');
        break;
      case 'append-refine': {
        const t = el.dataset.text;
        const cur = Store.getState().refineInput;
        Store.setRefineInput(cur ? cur + '；' + t : t);
        break;
      }
      case 'apply-refine':
        Store.applyRefine();
        break;
      case 'gallery-room':
        Store.setGalleryRoom(el.dataset.room);
        break;
      case 'gallery-thumb':
        Store.setGalleryIndex(Number(el.dataset.index));
        break;
      case 'viewer-room':
        Store.setViewer3dRoom(el.dataset.room);
        break;
      case 'viewer-next-room': {
        const ids = ['living', 'master', 'second', 'kitchen', 'bath'];
        const i = ids.indexOf(Store.getState().viewer3dRoom);
        Store.setViewer3dRoom(ids[(i + 1) % ids.length]);
        break;
      }
      case 'viewer-focus':
        el.focus();
        break;
      case 'knowledge-tab':
        Store.setKnowledgeTab(el.dataset.tab);
        break;
      case 'import-ref':
        Store.importReference();
        break;
      case 'save-settings':
        Store.saveSettings();
        break;
      case 'rebuild-index':
        Store.rebuildIndex();
        break;
      case 'reset-demo':
        Store.resetDemo();
        break;
      case 'toast':
        Store.showToast(el.dataset.msg || '操作完成');
        break;
      default:
        break;
    }
  }

  function handleBind(el) {
    const bind = el.dataset.bind;
    const val = el.value;
    focusedInput = bind;
    switch (bind) {
      case 'search':
        Store.setSearch(val);
        break;
      case 'status-filter':
        Store.setStatusFilter(val);
        break;
      case 'upload-name':
        Store.updateUploadDraft('name', val);
        break;
      case 'upload-area':
        Store.updateUploadDraft('area', val);
        break;
      case 'design-brief':
        Store.setDesignBrief(val);
        break;
      case 'refine-input':
        Store.setRefineInput(val);
        break;
      case 'import-title':
        Store.updateImportDraft('title', val);
        break;
      case 'import-tags':
        Store.updateImportDraft('tags', val);
        break;
      case 'setting-vault':
        Store.getState().settings.vaultPath = val;
        break;
      case 'setting-omlx':
        Store.getState().settings.omlxUrl = val;
        break;
      case 'setting-comfy':
        Store.getState().settings.comfyUrl = val;
        break;
      default:
        break;
    }
  }

  viewport.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el || el.disabled) return;
    handleAction(el.dataset.action, el, e);
  });

  viewport.addEventListener('input', (e) => {
    const el = e.target.closest('[data-bind]');
    if (el) handleBind(el);
  });

  viewport.addEventListener('change', (e) => {
    const el = e.target.closest('[data-bind]');
    if (el) handleBind(el);
  });

  document.addEventListener('keydown', (e) => {
    const state = Store.getState();
    if (state.screen === '10' && ['w', 'a', 's', 'd', 'W', 'A', 'S', 'D'].includes(e.key)) {
      e.preventDefault();
      const map = { w: [0, -4], s: [0, 4], a: [-4, 0], d: [4, 0] };
      const k = e.key.toLowerCase();
      const [dx, dy] = map[k];
      Store.moveViewer3d(dx, dy);
      return;
    }
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'ArrowLeft') goToIndex(screenIndex() - 1);
    if (e.key === 'ArrowRight') goToIndex(screenIndex() + 1);
  });

  prevBtn.addEventListener('click', () => goToIndex(screenIndex() - 1));
  nextBtn.addEventListener('click', () => goToIndex(screenIndex() + 1));

  Store.subscribe(renderApp);

  const saved = sessionStorage.getItem('houseDiyProtoIndex');
  if (saved !== null) {
    sessionStorage.removeItem('houseDiyProtoIndex');
    goToIndex(Number(saved));
  } else {
    renderApp();
  }
})();
