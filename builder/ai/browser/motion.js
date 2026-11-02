(() => {
  const key = '__bobMotion';
  window[key]?.dispose();
  const controller = new AbortController(), animations = new Set();
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  const cancel = () => { for (const animation of animations) animation.cancel(); animations.clear(); };
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      observer.unobserve(entry.target);
      if (preference.matches) continue;
      const animation = entry.target.animate([{ opacity: .3, transform: 'translateY(12px)' }, { opacity: 1, transform: 'none' }], { duration: 350, easing: 'ease-out' });
      animations.add(animation);
      animation.finished.catch(() => {}).finally(() => animations.delete(animation));
    }
  });
  document.querySelectorAll('[data-bob-reveal]').forEach(element => observer.observe(element));
  const dispose = () => { observer.disconnect(); cancel(); controller.abort(); if (window[key]?.dispose === dispose) delete window[key]; };
  preference.addEventListener('change', () => { if (preference.matches) cancel(); }, { signal: controller.signal });
  addEventListener('pagehide', dispose, { signal: controller.signal, once: true });
  window[key] = { dispose };
})();
