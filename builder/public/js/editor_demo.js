// Opens the published page in a sandboxed copy of the Builder editor, from any
// link to #editor-demo. The editor loads in a same-origin iframe that cannot reach
// the server (see builder/editor_demo.py), and this script only choreographs it.
(() => {
  const demoURL = document.currentScript?.dataset.demoUrl;
  if (!demoURL) return;

  const SOURCE = "builder-editor-demo";
  const TRIGGER = 'a[href="#editor-demo"], [data-editor-demo]';
  const BLOCKS = '[class^="fb-"], [class*=" fb-"]';
  // long enough to read as the page turning into blocks, short enough to feel instant
  const MIN_BLUEPRINT_MS = 260;
  // a demo that never reports ready must not leave the page outlined, ignoring clicks
  const LOAD_TIMEOUT_MS = 15000;
  const root = document.documentElement;
  let frame, booted, opening, isOpen, trigger;

  // outlines ripple out from the click over the page's blocks, as the editor draws them
  document.head.insertAdjacentHTML(
    "beforeend",
    `<style>
      @keyframes editor-demo-outline { from { outline-color: transparent } }
      @keyframes editor-demo-waiting { 50% { outline-color: rgb(59 130 246 / 0.15) } }
      [data-editor-demo-opening] :is(${BLOCKS}) {
        outline: 1px solid rgb(59 130 246 / 0.7); outline-offset: -1px;
        animation: editor-demo-outline 0.2s ease-out calc(var(--ripple) * 1ms) backwards;
      }
      /* on a slow connection the editor takes a moment, so the click keeps a pulse */
      [data-editor-demo-opening] [data-editor-demo-clicked] {
        outline-width: 2px;
        animation: editor-demo-waiting 1.2s ease-in-out 0.5s infinite;
      }
    </style>`,
  );

  // the theme the page is showing, from a manual toggle or the system setting
  const isDark = () => {
    const scheme = getComputedStyle(root).colorScheme;
    return (
      scheme === "dark" ||
      (scheme.includes("dark") &&
        matchMedia("(prefers-color-scheme: dark)").matches)
    );
  };
  const supported = () =>
    matchMedia("(min-width: 1024px) and (pointer: fine)").matches;
  const send = (message) =>
    frame.contentWindow.postMessage(
      { source: SOURCE, ...message },
      location.origin,
    );

  function preload() {
    if (frame || !supported()) return;
    frame = Object.assign(document.createElement("iframe"), {
      src: demoURL,
      title: "Builder editor demo",
      inert: true,
      sandbox:
        "allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox",
      allow: "clipboard-read; clipboard-write",
      style:
        "position:fixed;inset:0;width:100%;height:100%;border:0;z-index:2147483647;opacity:0;pointer-events:none",
    });
    document.body.append(frame);
  }

  function open(link) {
    // the editor itself explains that it needs a larger screen
    if (!supported()) return location.assign(demoURL);
    preload();
    trigger = link;
    const { left, top, width, height } = link.getBoundingClientRect();
    opening = {
      prepare: {
        type: "prepare",
        scrollY,
        target: { left, top, width, height },
        dark: isDark(),
      },
      startedAt: performance.now(),
      timeout: setTimeout(giveUp, LOAD_TIMEOUT_MS),
    };
    showBlueprint(left + width / 2, top + height / 2);
    link.animate?.({ transform: ["scale(1)", "scale(0.96)", "scale(1)"] }, 260);
    if (booted) send(opening.prepare);
  }

  function showBlueprint(x, y) {
    for (const block of document.querySelectorAll(BLOCKS)) {
      const rect = block.getBoundingClientRect();
      const distance = Math.hypot(
        rect.x + rect.width / 2 - x,
        rect.y + rect.height / 2 - y,
      );
      block.style.setProperty("--ripple", Math.min(240, distance * 0.35));
    }
    trigger.closest(BLOCKS)?.setAttribute("data-editor-demo-clicked", "");
    root.setAttribute("data-editor-demo-opening", "");
  }

  function hideBlueprint() {
    root.removeAttribute("data-editor-demo-opening");
    document
      .querySelector("[data-editor-demo-clicked]")
      ?.removeAttribute("data-editor-demo-clicked");
  }

  function reveal() {
    clearTimeout(opening.timeout);
    const delay = Math.max(
      0,
      MIN_BLUEPRINT_MS - (performance.now() - opening.startedAt),
    );
    opening = null;
    isOpen = true;
    setTimeout(() => {
      frame.inert = false;
      frame.style.pointerEvents = "auto";
      frame.style.transition = "opacity 90ms ease-out";
      frame.style.opacity = "1";
      root.style.overflow = "hidden";
      // Back closes the demo instead of leaving the page
      history.pushState({ editorDemo: true }, "");
      frame.focus();
      setTimeout(() => send({ type: "play" }), 90);
      setTimeout(hideBlueprint, 400);
    }, delay);
  }

  // on a slow connection the editor may still be loading: hand the visitor over to it
  // as an ordinary page, where the browser shows the wait, rather than drop their click
  function giveUp() {
    opening = null;
    hideBlueprint();
    location.assign(demoURL);
  }

  function close(scrollY) {
    isOpen = false;
    root.style.overflow = "";
    window.scrollTo({ top: scrollY, behavior: "instant" });
    Object.assign(frame.style, {
      transition: "opacity 160ms ease-in",
      opacity: "0",
      pointerEvents: "none",
    });
    frame.inert = true;
    trigger?.focus({ preventScroll: true });
    if (history.state?.editorDemo) history.back();
  }

  window.addEventListener("message", ({ source, origin, data }) => {
    if (!frame || source !== frame.contentWindow || origin !== location.origin)
      return;
    if (data?.source !== SOURCE) return;
    if (data.type === "booted") {
      booted = true;
      if (opening) send(opening.prepare);
    }
    if (data.type === "ready" && opening) reveal();
    if (data.type === "exit" && isOpen) close(Number(data.scrollY) || 0);
  });
  window.addEventListener("popstate", () => isOpen && send({ type: "close" }));

  document.addEventListener("click", (event) => {
    const link = event.target.closest?.(TRIGGER);
    if (!link) return;
    event.preventDefault();
    if (!opening && !isOpen) open(link);
  });
  // warm the editor up on intent, so it is usually ready by the click
  for (const type of ["pointerover", "focusin"]) {
    document.addEventListener(
      type,
      (event) => event.target.closest?.(TRIGGER) && preload(),
    );
  }

  // the editor takes a few seconds to boot, far more than a hover buys, so start it as
  // soon as the page is loaded and someone is really here: crawlers never move or scroll
  let visitorIsHere;
  function warmUp() {
    visitorIsHere = true;
    if (document.readyState !== "complete" || navigator.connection?.saveData)
      return;
    const idle = window.requestIdleCallback || ((run) => setTimeout(run, 500));
    idle(preload, { timeout: 2000 });
  }
  for (const type of ["pointermove", "scroll", "keydown"]) {
    addEventListener(type, warmUp, { once: true, passive: true });
  }
  addEventListener("load", () => visitorIsHere && warmUp());
})();
