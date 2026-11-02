(() => {
  const visible = el => {
    if (!el.getClientRects().length || getComputedStyle(el).visibility === 'hidden') return false;
    if (el.checkVisibility && !el.checkVisibility({ visibilityProperty: true })) return false;
    for (let parent = el.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS' && !parent.open && !parent.querySelector(':scope > summary')?.contains(el)) return false;
    }
    return true;
  };
  const name = el => (el.id ? '#' + el.id : el.tagName.toLowerCase()) + ' ' + (el.textContent || '').trim().slice(0, 65);
  const issues = [];
  const add = (code, element, detail, severity = 'error') => { if (issues.length < 120) issues.push({ code, target: name(element), detail, severity }); };
  const links = [...document.querySelectorAll('a[href]')];
  const focusable = [...document.querySelectorAll('a[href],button,input,textarea,select,[tabindex]')].filter(visible);
  const rgb = value => (value.match(/[\d.]+/g) || []).map(Number);
  const lum = color => color.slice(0, 3).map(c => c / 255).map(c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4).reduce((n, c, i) => n + c * [.2126, .7152, .0722][i], 0);
  let contrastUnchecked = 0;
  for (const el of document.querySelectorAll('body *')) {
    if (!visible(el)) continue;
    const rect = el.getBoundingClientRect(), css = getComputedStyle(el);
    if (rect.right > innerWidth + 2 && css.position !== 'fixed' && css.overflowX !== 'hidden') add('horizontal-overflow', el, `${Math.round(rect.right - innerWidth)}px beyond viewport`, 'warning');
    if (el.tagName === 'IMG') {
      if (!el.complete || !el.naturalWidth) add('broken-image', el, el.getAttribute('src') || 'Missing source');
      if (!el.hasAttribute('alt')) add('missing-alt', el, 'Add meaningful alt text or an empty alt for decorative imagery');
    }
    if (['INPUT','TEXTAREA','SELECT'].includes(el.tagName) && !['hidden','submit','button','reset'].includes(el.type) && !el.labels?.length && !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby')) add('missing-label', el, 'The field has no accessible label');
    if (el.tagName === 'BUTTON' && !(el.textContent.trim() || el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.querySelector('img[alt]:not([alt=""])'))) add('unnamed-button', el, 'Give the button an accessible name');
    if (!Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    let bg = [255, 255, 255], unverified = false;
    for (let parent = el; parent; parent = parent.parentElement) {
      const style = getComputedStyle(parent), color = rgb(style.backgroundColor);
      if (style.backgroundImage !== 'none' || Number(style.opacity) < 1 || style.mixBlendMode !== 'normal') { unverified = true; break; }
      if (color.length === 3 || color[3] === 1) { bg = color; break; }
      if (color[3] > 0) { unverified = true; break; }
    }
    const fg = rgb(css.color);
    if (unverified || fg.length < 3 || (fg.length > 3 && fg[3] !== 1) || !css.color.startsWith('rgb')) { contrastUnchecked++; continue; }
    const [l1, l2] = [lum(fg), lum(bg)].sort((a,b) => b-a);
    const ratio = (l1 + .05) / (l2 + .05);
    const large = parseFloat(css.fontSize) >= 24 || (parseFloat(css.fontSize) >= 18.66 && parseInt(css.fontWeight) >= 700);
    if (ratio < (large ? 3 : 4.5)) add('text-contrast', el, `${ratio.toFixed(2)}:1 contrast`);
  }
  for (const el of focusable) {
    const box = el.getBoundingClientRect();
    if (el.tabIndex > 0) add('focus-order', el, 'Positive tabindex changes reading order', 'warning');
    if (box.width < 24 || box.height < 24) add('small-target', el, 'Target is smaller than 24 CSS pixels', 'warning');
  }
  for (const el of links) {
    const href = el.getAttribute('href');
    if (href === '#' || (href.startsWith('#') && !document.getElementById(href.slice(1)))) add('missing-link-target', el, href);
  }
  for (const el of document.querySelectorAll('video')) if (!el.poster && !el.controls) add('media-fallback', el, 'Video has neither a poster nor controls', 'warning');
  if (!document.documentElement.lang) add('missing-language', document.documentElement, 'Set the document language');
  if (!document.title.trim()) add('missing-title', document.documentElement, 'Set a useful page title');
  if (!document.querySelector('h1')) add('missing-main-heading', document.body, 'No main heading', 'warning');
  const animations = document.getAnimations().filter(a => a.playState === 'running' && Number(a.effect?.getTiming().duration) > 100);
  if (matchMedia('(prefers-reduced-motion: reduce)').matches && animations.length) add('reduced-motion', document.body, `${animations.length} long animations still running`, 'warning');
  return { viewport: { width: innerWidth, height: innerHeight }, documentHeight: document.documentElement.scrollHeight, issues, contrastUnchecked, focusTargets: focusable.length, fontsReady: document.fonts.status === 'loaded', reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches, runtimeErrors: (window.__bobErrors || []).slice(0, 10), checks: ['overflow','images','labels','headings','links','simple-background contrast','focus order','target size','media fallback','reduced motion'], manualChecks: ['photo/gradient contrast','screen-reader reading order','form delivery','custom interaction correctness','font glyph coverage'] };
})()
