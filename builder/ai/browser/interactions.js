(async step => {
  const matches = document.querySelectorAll(step.selector);
  if (matches.length !== 1) return { passed: false, detail: `Expected one target, found ${matches.length}` };
  const element = matches[0];
  const visible = () => {
    if (!element.getClientRects().length || getComputedStyle(element).visibility === 'hidden') return false;
    if (element.checkVisibility && !element.checkVisibility({ visibilityProperty: true })) return false;
    for (let parent = element.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS' && !parent.open && !parent.querySelector(':scope > summary')?.contains(element)) return false;
    }
    return true;
  };
  if (step.action === 'assert') {
    let actual;
    if (step.state === 'visible') actual = visible();
    else if (step.state === 'hidden') actual = !visible();
    else if (step.state === 'focused') actual = document.activeElement === element;
    else if (step.state === 'checked') actual = Boolean(element.checked);
    else if (step.state === 'text') actual = element.textContent.trim();
    else if (step.state === 'value') actual = element.value;
    else actual = element.getAttribute(step.attribute);
    const expected = ['text', 'value', 'attribute'].includes(step.state) ? step.value : true;
    return { passed: actual === expected, actual: String(actual).slice(0, 300), expected };
  }
  if (!visible()) return { passed: false, detail: 'Target is not visible' };
  element.scrollIntoView({ block: 'center' });
  element.focus();
  if (step.action === 'click') {
    if ((element.form && element.type === 'submit') || (element.closest('a[href]') && !element.closest('a[href]').getAttribute('href').startsWith('#'))) {
      return { passed: false, detail: 'Submissions and navigation require a separate live delivery test' };
    }
    if (element.disabled) return { passed: false, detail: 'Target is disabled' };
    element.click();
  } else if (step.action === 'fill') {
    if (!element.matches('input:not([type=file]):not([type=password]),textarea,select')) return { passed: false, detail: 'Target is not a supported input' };
    element.value = step.value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
  }
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  return { passed: true };
})
