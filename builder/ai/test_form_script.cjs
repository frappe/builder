// Runs the actual generated script against a local DOM. Fetch never leaves this process.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { createRequire } = require('node:module');
const path = require('node:path');
const frontendRequire = createRequire(path.join(__dirname, '../../frontend/package.json'));
const { JSDOM } = frontendRequire('jsdom');

async function main() {
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  const dom = new JSDOM(input.html, { runScripts: 'outside-only', url: 'https://fixture.invalid' });
  const { window } = dom;
  const calls = [];
  window.csrf_token = input.csrf;
  window.fetch = async (url, request) => {
    calls.push({ url, headers: request.headers, body: JSON.parse(request.body) });
    return { ok: !input.fail, json: async () => input.response || { message: { name: 'fixture' } } };
  };
  window.eval(input.script);
  await new Promise(resolve => window.document.addEventListener('DOMContentLoaded', resolve, { once: true }));
  if (input.loadTwice) window.eval(input.script);
  const form = window.document.querySelector('form');
  if (input.action === 'click') window.document.querySelector('button, input[type=submit]').click();
  else if (input.action !== 'none') form.requestSubmit();
  await new Promise(resolve => setImmediate(resolve));
  if (input.retry) {
    form.requestSubmit();
    await new Promise(resolve => setImmediate(resolve));
  }
  assert.equal(calls.length, input.expectedCalls);
  if (input.expected) assert.deepEqual(calls[0].body.data, input.expected);
  if (input.csrf && calls.length) assert.equal(calls[0].headers['X-Frappe-CSRF-Token'], input.csrf);
  if (input.status) assert.match(window.document.querySelector('[role=status]').textContent, new RegExp(input.status));
  if (input.preserve) {
    const control = window.document.querySelector(input.preserve.selector);
    assert.equal(control[input.preserve.property], input.preserve.value);
  }
  dom.window.close();
}
main().catch(error => { console.error(error); process.exitCode = 1; });
