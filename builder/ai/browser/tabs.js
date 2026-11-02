(() => {
  const key = '__bobTabs';
  window[key]?.dispose();
  const controller = new AbortController(), restore = [];
  document.querySelectorAll('[data-bob-tabs]').forEach(group => {
    const tabs = [...group.querySelectorAll('[role=tab]')];
    const panels = tabs.map(tab => document.getElementById(tab.getAttribute('aria-controls')));
    if (!tabs.length || panels.some(panel => !panel || !group.contains(panel))) return;
    const select = index => {
      tabs.forEach((tab, i) => { tab.setAttribute('aria-selected', String(i === index)); tab.tabIndex = i === index ? 0 : -1; panels[i].hidden = i !== index; });
    };
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => select(index), { signal: controller.signal });
      tab.addEventListener('keydown', event => {
        let next = index;
        const rtl = getComputedStyle(group).direction === 'rtl';
        const forward = group.querySelector('[role=tablist]')?.getAttribute('aria-orientation') === 'vertical' ? 'ArrowDown' : rtl ? 'ArrowLeft' : 'ArrowRight';
        const backward = forward === 'ArrowDown' ? 'ArrowUp' : rtl ? 'ArrowRight' : 'ArrowLeft';
        if (event.key === forward) next = (index + 1) % tabs.length;
        else if (event.key === backward) next = (index + tabs.length - 1) % tabs.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = tabs.length - 1;
        else return;
        event.preventDefault(); select(next); tabs[next].focus();
      }, { signal: controller.signal });
    });
    restore.push(() => { panels.forEach(panel => { panel.hidden = false; }); tabs.forEach(tab => { tab.removeAttribute('aria-selected'); tab.tabIndex = 0; }); });
    select(0);
  });
  const dispose = () => { controller.abort(); restore.forEach(fn => fn()); if (window[key]?.dispose === dispose) delete window[key]; };
  addEventListener('pagehide', dispose, { signal: controller.signal, once: true });
  window[key] = { dispose };
})();
