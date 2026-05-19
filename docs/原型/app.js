(function () {
  const listEl = document.getElementById('screenList');
  const viewport = document.getElementById('screenViewport');
  const screenIdEl = document.getElementById('screenId');
  const screenTitleEl = document.getElementById('screenTitle');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');

  let current = 0;

  function renderNav() {
    listEl.innerHTML = SCREENS.map((s, i) => `
      <button type="button" class="screen-link${i === current ? ' active' : ''}" data-index="${i}">
        <span class="num">${s.id}</span>
        <span class="label">${s.title}</span>
        <span class="flow">${s.flow}</span>
      </button>
    `).join('');

    listEl.querySelectorAll('.screen-link').forEach((btn) => {
      btn.addEventListener('click', () => goTo(Number(btn.dataset.index)));
    });
  }

  function goTo(index) {
    current = (index + SCREENS.length) % SCREENS.length;
    const screen = SCREENS[current];
    screenIdEl.textContent = screen.id;
    screenTitleEl.textContent = screen.title;
    viewport.innerHTML = screen.html;
    renderNav();
    viewport.scrollTop = 0;
  }

  prevBtn.addEventListener('click', () => goTo(current - 1));
  nextBtn.addEventListener('click', () => goTo(current + 1));

  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') goTo(current - 1);
    if (e.key === 'ArrowRight') goTo(current + 1);
  });

  const saved = sessionStorage.getItem('houseDiyProtoIndex');
  if (saved !== null) {
    sessionStorage.removeItem('houseDiyProtoIndex');
    goTo(Number(saved));
  } else {
    goTo(0);
  }
})();
