(function () {
  const STEP_ORDER = ['upload', 'parse', 'annotate', 'design', 'preview'];
  const STEP_INDEX = Object.fromEntries(STEP_ORDER.map((k, i) => [k, i]));

  const state = {
    screen: 'parse',
    maxStepIndex: 4,
    fileName: '',
    parseProgress: 62,
    dirty: false,
    selectedRoom: 'r1',
    logs: [
      '14:02:01 [INFO] raster ready 2048x1536',
      '14:02:15 [INFO] VLM step1 scale=1:100',
      '14:02:28 [INFO] rooms detected: 4',
      '14:02:40 [INFO] batch 2/4 rooms: 主卧, 次卧',
      '14:02:55 [WARN] validation: r2/r3 overlap IoU=0.22',
    ],
    outputRoot: '/Users/me/House-DIY-Output',
  };

  const viewport = document.getElementById('appViewport');
  const titleEl = document.getElementById('screenTitle');
  const idEl = document.getElementById('screenId');
  const navList = document.getElementById('screenList');

  function render() {
    const screen = SCREENS[state.screen];
    viewport.innerHTML = renderScreen(state.screen, state);
    titleEl.textContent = screen ? screen.title : state.screen;
    idEl.textContent = screen ? screen.id : '--';
    bindEvents();
    updateNav();
  }

  function updateNav() {
    navList.querySelectorAll('[data-nav]').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.nav === state.screen);
    });
  }

  function buildNav() {
    navList.innerHTML = Object.entries(SCREENS)
      .map(
        ([key, s]) =>
          `<button type="button" class="screen-nav-item" data-nav="${key}">${s.id} ${s.title}</button>`,
      )
      .join('');
    navList.querySelectorAll('[data-nav]').forEach((btn) => {
      btn.addEventListener('click', () => {
        tryNavigate(() => {
          state.screen = btn.dataset.nav;
          render();
        });
      });
    });
  }

  function tryNavigate(fn) {
    if (state.dirty && state.screen === 'annotate') {
      showUnsavedModal(fn);
      return;
    }
    fn();
  }

  function showUnsavedModal(onDiscard) {
    const backdrop = document.createElement('div');
    backdrop.className = 'v2-modal-backdrop';
    backdrop.innerHTML = `
      <div class="v2-modal">
        <h3>有未保存的变更</h3>
        <p class="muted">切换步骤前请先保存标注，或放弃变更。</p>
        <div class="actions">
          <button type="button" class="btn ghost" data-m="cancel">取消</button>
          <button type="button" class="btn ghost" data-m="discard">放弃并离开</button>
          <button type="button" class="btn primary" data-m="save">保存并继续</button>
        </div>
      </div>`;
    document.body.appendChild(backdrop);
    backdrop.querySelector('[data-m="cancel"]').onclick = () => backdrop.remove();
    backdrop.querySelector('[data-m="discard"]').onclick = () => {
      state.dirty = false;
      backdrop.remove();
      onDiscard();
    };
    backdrop.querySelector('[data-m="save"]').onclick = () => {
      state.dirty = false;
      backdrop.remove();
      onDiscard();
    };
  }

  function showZoomModal() {
    const backdrop = document.createElement('div');
    backdrop.className = 'v2-modal-backdrop';
    backdrop.innerHTML = `
      <div class="image-preview-dialog" role="dialog">
        <header class="image-preview-head">
          <div>
            <h3 style="font-size:0.95rem;margin:0">原图 + 标注</h3>
            <div class="preview-layer-toggles">
              <label><input type="checkbox" checked /> 原图</label>
              <label><input type="checkbox" checked /> 标注</label>
            </div>
          </div>
          <button type="button" class="icon-btn-close" data-close>×</button>
        </header>
        <div class="image-preview-body">
          <div class="floor-mock" style="max-width:900px">
            <img src="../../../server/tests/fixtures/floorplans/G-MKT-1.png" alt="户型大图" />
            <div class="room-overlay selected" style="left:8%;top:12%;width:22%;height:28%"><span class="label">卫生间</span></div>
            <div class="room-overlay" style="left:32%;top:8%;width:18%;height:55%"><span class="label">长廊</span></div>
            <div class="room-overlay" style="left:52%;top:10%;width:38%;height:45%"><span class="label">客厅</span></div>
          </div>
        </div>
        <footer class="image-preview-foot">原图底图与 AI 标注轮廓叠加显示，与标注页一致</footer>
      </div>`;
    document.body.appendChild(backdrop);
    backdrop.querySelector('[data-close]').onclick = () => backdrop.remove();
    backdrop.onclick = (e) => {
      if (e.target === backdrop) backdrop.remove();
    };
  }

  function bindEvents() {
    viewport.querySelectorAll('[data-action="goto-screen"]').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        const target = el.dataset.screen;
        tryNavigate(() => {
          if (target === 'parse' && state.fileName) {
            state.parseProgress = 62;
          }
          state.screen = target;
          render();
        });
      });
    });

    viewport.querySelectorAll('[data-action="goto-step"]').forEach((el) => {
      if (el.disabled) return;
      el.addEventListener('click', () => {
        tryNavigate(() => {
          state.screen = el.dataset.step;
          render();
        });
      });
    });

    viewport.querySelectorAll('[data-action="goto-max-step"]').forEach((el) => {
      el.addEventListener('click', () => {
        state.dirty = false;
        state.screen = el.dataset.max || 'design';
        render();
      });
    });

    viewport.querySelectorAll('[data-action="mock-upload"]').forEach((el) => {
      el.addEventListener('click', () => {
        state.fileName = 'developer-plan.pdf';
        render();
      });
    });

    viewport.querySelectorAll('[data-action="mark-dirty"]').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        state.dirty = true;
      });
    });

    viewport.querySelectorAll('[data-action="save-annotate"]').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        state.dirty = false;
        state.maxStepIndex = Math.max(state.maxStepIndex, STEP_INDEX.annotate);
      });
    });

    viewport.querySelectorAll('[data-action="select-room"]').forEach((el) => {
      el.addEventListener('click', () => {
        state.selectedRoom = el.dataset.room;
        render();
      });
    });

    viewport.querySelectorAll('[data-action="open-zoom"]').forEach((el) => {
      el.addEventListener('click', (e) => {
        if (e.target.closest('[data-action="mark-dirty"]')) return;
        showZoomModal();
      });
    });

    viewport.querySelectorAll('[data-action="cancel-parse"]').forEach((el) => {
      el.addEventListener('click', () => {
        state.parseProgress = 0;
        state.screen = 'upload';
        render();
      });
    });
  }

  const keys = Object.keys(SCREENS);
  document.getElementById('prevBtn').addEventListener('click', () => {
    const i = keys.indexOf(state.screen);
    if (i > 0) {
      state.screen = keys[i - 1];
      render();
    }
  });

  document.getElementById('nextBtn').addEventListener('click', () => {
    const i = keys.indexOf(state.screen);
    if (i < keys.length - 1) {
      state.screen = keys[i + 1];
      render();
    }
  });

  buildNav();
  render();
})();
