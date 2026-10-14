(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const rtl = document.documentElement.dir === 'rtl';

  // Mobile menu
  const menuBtn = $('#menu-toggle'), nav = $('#site-nav');
  const setMenu = (open) => {
    nav.classList.toggle('is-open', open);
    menuBtn.setAttribute('aria-expanded', String(open));
  };
  menuBtn.addEventListener('click', () => setMenu(!nav.classList.contains('is-open')));
  document.addEventListener('click', (e) => { if (!e.target.closest('.hdr')) setMenu(false); });

  // Search bar above the bottom dock
  const search = $('#search-bar'), input = $('input', search);
  const setSearch = (open) => {
    search.classList.toggle('is-open', open);
    $$('[data-search-open]').forEach((b) => b.setAttribute('aria-expanded', String(open)));
    if (open) setTimeout(() => input.focus(), 150);
  };
  $$('[data-search-open]').forEach((b) =>
    b.addEventListener('click', () => setSearch(!search.classList.contains('is-open'))));
  $('[data-search-close]').addEventListener('click', () => setSearch(false));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { setSearch(false); setMenu(false); }
  });

  // Testimonial slider (swipe = native scroll-snap; buttons scroll the track)
  $$('[data-slider]').forEach((box) => {
    const track = $('[data-track]', box);
    const step = (dir) => track.scrollBy({ left: dir * (rtl ? -1 : 1) * track.clientWidth * 0.8, behavior: 'smooth' });
    $('[data-prev]', box).addEventListener('click', () => step(-1));
    $('[data-next]', box).addEventListener('click', () => step(1));
  });
})();