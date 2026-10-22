(() => {
  const sidebar = document.getElementById('sidebar');
  const menu = document.getElementById('menu-toggle');
  menu?.addEventListener('click', () => {
    const opened = sidebar.classList.toggle('is-open');
    menu.setAttribute('aria-expanded', String(opened));
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      sidebar?.classList.remove('is-open');
      menu?.setAttribute('aria-expanded', 'false');
    }
  });
  const links = [...document.querySelectorAll('.toc-link')];
  links.forEach(link => link.addEventListener('click', () => {
    sidebar?.classList.remove('is-open');
    menu?.setAttribute('aria-expanded', 'false');
  }));
  const targets = links.map(link => document.getElementById(decodeURIComponent(link.hash.slice(1)))).filter(Boolean);
  let scheduled = false;
  const update = () => {
    scheduled = false;
    const cutoff = innerWidth <= 580 ? 145 : 125;
    let active = targets[0]?.id;
    for (const target of targets) {
      if (target.getBoundingClientRect().top <= cutoff) active = target.id;
    }
    for (const link of links) {
      const selected = link.hash === `#${active}`;
      link.classList.toggle('active', selected);
      if (selected) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
  };
  window.addEventListener('scroll', () => {
    if (!scheduled) { scheduled = true; requestAnimationFrame(update); }
  }, {passive: true});
  window.addEventListener('resize', update);
  window.addEventListener('load', update);
  update();
  const code = document.getElementById('code-toggle');
  code?.addEventListener('click', () => {
    const disclosures = [...document.querySelectorAll('.code-disclosure')];
    const open = !disclosures.every(item => item.open);
    disclosures.forEach(item => { item.open = open; });
    code.textContent = open ? 'Приховати весь код' : 'Показати весь код';
    code.setAttribute('aria-pressed', String(open));
  });
})();
