// Opens the published page in a sandboxed copy of the Builder editor, from any
// link to #editor-demo. The editor loads in a same-origin iframe that cannot reach
// the server (see builder/editor_demo.py), and this script only choreographs it.
(() => {
  const demoURL = document.currentScript?.dataset.demoUrl;
  if (!demoURL) return;

  const SOURCE = "builder-editor-demo";
  const TRIGGER = 'a[href="#editor-demo"], [data-editor-demo]';
  const BLUE = "59, 130, 246";
  const EASE_OUT = "cubic-bezier(0.16, 1, 0.3, 1)";
  // long enough to read as the page turning into blocks, short enough to feel instant
  const MIN_BLUEPRINT_MS = 260;
  const MAX_OUTLINES = 70;
  // a demo that never reports ready would otherwise leave the page pulsing and ignore clicks
  const LOAD_TIMEOUT_MS = 15000;

  let frame = null;
  let booted = false;
  let opening = null;
  let isOpen = false;
  let lastTrigger = null;
  let blueprint = null;

  const supported = () =>
    matchMedia("(min-width: 1024px) and (pointer: fine)").matches;
  const reduceMotion = () =>
    matchMedia("(prefers-reduced-motion: reduce)").matches;

  function preload() {
    if (frame || !supported()) return;
    frame = document.createElement("iframe");
    frame.src = demoURL;
    frame.title = "Builder editor demo";
    frame.inert = true;
    frame.setAttribute(
      "sandbox",
      "allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox",
    );
    frame.setAttribute("allow", "clipboard-read; clipboard-write");
    frame.style.cssText =
      "position:fixed;inset:0;width:100%;height:100%;border:0;margin:0;padding:0;" +
      "z-index:2147483647;opacity:0;pointer-events:none;background:transparent;color-scheme:light";
    document.body.appendChild(frame);
  }

  function send(message) {
    frame?.contentWindow?.postMessage(
      { source: SOURCE, ...message },
      location.origin,
    );
  }

  function open(trigger) {
    if (opening || isOpen) return;
    if (!supported())
      return notify("Open this page on a larger screen to try the editor.");
    preload();
    const { left, top, width, height } = trigger.getBoundingClientRect();
    const target = { left, top, width, height };
    opening = {
      scrollY: window.scrollY,
      target,
      startedAt: performance.now(),
      timeout: setTimeout(giveUp, LOAD_TIMEOUT_MS),
    };
    lastTrigger = trigger;
    press(trigger);
    blueprint = showBlueprint(
      { x: left + width / 2, y: top + height / 2 },
      trigger,
    );
    if (booted) send({ type: "prepare", scrollY: opening.scrollY, target });
  }

  function reveal() {
    clearTimeout(opening.timeout);
    const elapsed = performance.now() - opening.startedAt;
    opening = null;
    isOpen = true;
    setTimeout(
      () => {
        frame.inert = false;
        frame.style.pointerEvents = "auto";
        frame.style.transition = "opacity 90ms ease-out";
        frame.style.opacity = "1";
        document.documentElement.style.overflow = "hidden";
        // Back closes the demo instead of leaving the page
        history.pushState({ editorDemo: true }, "");
        frame.focus();
        setTimeout(() => send({ type: "play" }), reduceMotion() ? 0 : 90);
        setTimeout(() => blueprint?.remove(), 400);
      },
      Math.max(0, MIN_BLUEPRINT_MS - elapsed),
    );
  }

  // drop the frame too, so the next click loads a fresh one
  function giveUp() {
    opening = null;
    blueprint?.remove();
    frame?.remove();
    frame = null;
    booted = false;
    notify("The editor demo could not load. Try again in a moment.");
  }

  function close(scrollY) {
    isOpen = false;
    document.documentElement.style.overflow = "";
    window.scrollTo({ top: scrollY, behavior: "instant" });
    frame.style.transition = "opacity 160ms ease-in";
    frame.style.opacity = "0";
    frame.style.pointerEvents = "none";
    frame.inert = true;
    lastTrigger?.focus({ preventScroll: true });
    if (history.state?.editorDemo) history.back();
  }

  function press(trigger) {
    trigger.animate?.(
      [
        { transform: "scale(1)" },
        { transform: "scale(0.96)" },
        { transform: "scale(1)" },
      ],
      {
        duration: 260,
        easing: "ease-out",
      },
    );
  }

  // outlines ripple out from the click over the page's blocks, as the editor draws them
  function showBlueprint(origin, trigger) {
    const layer = document.createElement("div");
    layer.setAttribute("aria-hidden", "true");
    layer.style.cssText =
      "position:fixed;inset:0;pointer-events:none;z-index:2147483646;";
    const triggerBlock =
      trigger.closest('[class^="fb-"], [class*=" fb-"]') || trigger;
    for (const { element, rect, distance } of visibleBlocks(origin)) {
      const selected = element === triggerBlock;
      const outline = document.createElement("div");
      const delay = reduceMotion() ? 0 : Math.min(240, distance * 0.35);
      outline.style.cssText =
        `position:absolute;left:${rect.left}px;top:${rect.top}px;width:${rect.width}px;height:${rect.height}px;` +
        `border-radius:${getComputedStyle(element).borderRadius};` +
        `box-shadow:inset 0 0 0 ${selected ? 2 : 1}px rgba(${BLUE}, ${selected ? 1 : 0.7});` +
        `background:rgba(${BLUE}, ${selected ? 0.08 : 0.03});opacity:0;transform:scale(0.985);` +
        `transition:opacity 200ms ease-out ${delay}ms, transform 320ms ${EASE_OUT} ${delay}ms;`;
      layer.appendChild(outline);
    }
    document.body.appendChild(layer);
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        for (const outline of layer.children) {
          outline.style.opacity = "1";
          outline.style.transform = "none";
        }
      }),
    );
    // still loading: breathe, so the wait reads as progress
    setTimeout(() => {
      if (opening && layer.isConnected) {
        layer.animate([{ opacity: 1 }, { opacity: 0.45 }, { opacity: 1 }], {
          duration: 1100,
          iterations: Infinity,
          easing: "ease-in-out",
        });
      }
    }, 500);
    return layer;
  }

  function visibleBlocks(origin) {
    const viewport = window.innerWidth * window.innerHeight;
    return Array.from(
      document.querySelectorAll('[class^="fb-"], [class*=" fb-"]'),
    )
      .map((element) => ({ element, rect: element.getBoundingClientRect() }))
      .filter(({ rect }) => {
        const onScreen =
          rect.bottom > 0 &&
          rect.top < window.innerHeight &&
          rect.right > 0 &&
          rect.left < window.innerWidth;
        return (
          onScreen &&
          rect.width >= 24 &&
          rect.height >= 12 &&
          rect.width * rect.height < viewport * 0.6
        );
      })
      .map((block) => ({
        ...block,
        distance: Math.hypot(
          block.rect.left + block.rect.width / 2 - origin.x,
          block.rect.top + block.rect.height / 2 - origin.y,
        ),
      }))
      .sort((a, b) => a.distance - b.distance)
      .slice(0, MAX_OUTLINES);
  }

  function notify(text) {
    const note = document.createElement("div");
    note.textContent = text;
    note.setAttribute("role", "status");
    note.style.cssText =
      "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:2147483647;" +
      "padding:10px 16px;border-radius:999px;background:#171717;color:#fff;font:14px/1.4 system-ui,sans-serif;" +
      "box-shadow:0 8px 24px rgba(0,0,0,.2);max-width:calc(100vw - 32px);text-align:center;";
    document.body.appendChild(note);
    setTimeout(() => note.remove(), 2800);
  }

  window.addEventListener("message", (event) => {
    if (
      !frame ||
      event.source !== frame.contentWindow ||
      event.origin !== location.origin
    )
      return;
    const message = event.data || {};
    if (message.source !== SOURCE) return;
    if (message.type === "booted") {
      booted = true;
      if (opening)
        send({
          type: "prepare",
          scrollY: opening.scrollY,
          target: opening.target,
        });
    } else if (message.type === "ready" && opening) {
      reveal();
    } else if (message.type === "exit" && isOpen) {
      close(Number(message.scrollY) || 0);
    }
  });

  window.addEventListener("popstate", () => isOpen && send({ type: "close" }));

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest?.(TRIGGER);
    if (!trigger) return;
    event.preventDefault();
    open(trigger);
  });

  // warm the editor up on intent, so it is usually ready by the click
  for (const eventName of ["pointerover", "focusin"]) {
    document.addEventListener(
      eventName,
      (event) => event.target.closest?.(TRIGGER) && preload(),
      {
        passive: true,
      },
    );
  }
})();
