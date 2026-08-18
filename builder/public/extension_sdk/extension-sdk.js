var j = Object.defineProperty;
var B = (e, t, r) => t in e ? j(e, t, { enumerable: !0, configurable: !0, writable: !0, value: r }) : e[t] = r;
var R = (e, t, r) => B(e, typeof t != "symbol" ? t + "" : t, r);
const D = (e, t, r) => ({
  v: 1,
  type: "request",
  id: e,
  method: t,
  params: r
}), U = (e, t) => ({
  v: 1,
  type: "response",
  id: e,
  result: t
}), m = (e, t) => ({
  v: 1,
  type: "response",
  id: e,
  error: t
}), F = (e, t) => ({
  v: 1,
  type: "event",
  event: e,
  payload: t
}), P = (e) => ({
  message: `This Builder speaks protocol version 1, not ${e}.`,
  code: "unsupported_version"
}), G = (e, t) => m(e, P(t)), K = (e) => typeof e == "object" && e !== null, z = (e) => !K(e) || typeof e.v != "number" ? !1 : e.type === "request" ? typeof e.id == "number" && typeof e.method == "string" : e.type === "response" ? typeof e.id == "number" : e.type === "event" ? typeof e.event == "string" : !1, J = (e) => e.v === 1;
class f extends Error {
  constructor(r) {
    super(r.message);
    R(this, "code");
    this.name = "ChannelCallError", this.code = r.code;
  }
}
const Q = (e) => new f({ message: `Unknown method "${e}".`, code: "unknown_method" }), x = {
  message: "The extension channel is closed.",
  code: "channel_closed"
}, W = (e) => e instanceof f ? { message: e.message, code: e.code } : { message: e instanceof Error ? e.message : String(e) };
function X(e, t) {
  const r = /* @__PURE__ */ new Map(), i = /* @__PURE__ */ new Map(), g = /* @__PURE__ */ new Map();
  let I = 1, h = !1;
  const d = (n) => {
    h || e.postMessage(n);
  }, M = (n, o) => {
    const c = i.get(n);
    if (c) return c(o);
    throw Q(n);
  }, _ = async (n) => {
    try {
      d(U(n.id, await M(n.method, n.params)));
    } catch (o) {
      d(m(n.id, W(o)));
    }
  }, S = (n, o, c) => {
    const u = r.get(n);
    if (!u) return console.warn(`Extension channel received a response for unknown call ${n}`);
    r.delete(n), c ? u.reject(new f(c)) : u.resolve(o);
  }, L = (n) => {
    g.get(n.event)?.forEach((o) => o(n.payload));
  }, V = (n) => {
    if (n.type === "request") return d(G(n.id, n.v));
    if (n.type === "response") return S(n.id, void 0, P(n.v));
    console.warn(`Extension channel dropped an event at protocol version ${n.v}`);
  }, N = (n) => {
    if (z(n)) {
      if (!J(n)) return V(n);
      if (n.type === "request") return void _(n);
      if (n.type === "response") return S(n.id, n.result, n.error);
      L(n);
    }
  }, $ = (n, o) => new Promise((c, u) => {
    if (h) return u(new f(x));
    const C = I++;
    r.set(C, { resolve: c, reject: u }), d(D(C, n, o));
  }), k = (n, o) => {
    if (i.has(n)) throw new Error(`"${n}" already has a handler on this channel`);
    return i.set(n, o), () => {
      i.get(n) === o && i.delete(n);
    };
  }, q = (n, o) => {
    const c = g.get(n) ?? /* @__PURE__ */ new Set();
    return g.set(n, c), c.add(o), () => c.delete(o);
  }, A = (n, o) => d(F(n, o)), H = () => {
    h || (h = !0, r.forEach((n) => n.reject(new f(x))), r.clear(), i.clear(), g.clear(), e.close());
  };
  return e.onmessage = (n) => N(n.data), { call: $, handle: k, listen: q, emit: A, close: H };
}
const y = /* @__PURE__ */ new Map(), Y = (e, t) => y.set(e, t), Z = (e) => y.delete(e), ee = (e) => {
  const { action: t, context: r } = e ?? {}, i = y.get(String(t));
  if (!i) throw new Error(`This extension registered no action named "${t}"`);
  return i(r ?? {});
};
let w = null, a = null;
const O = /* @__PURE__ */ new Map(), te = (e) => a = e, ne = () => a, T = (e, t) => {
  if (t) throw new Error(`This extension already registered its "${e}" slot`);
}, re = (e) => {
  T("main", w !== null), w = e;
}, E = (e, t) => {
  T(e, O.has(e)), O.set(e, t);
}, oe = () => {
  if (a === "main") return w?.();
  a && !O.has(a) && console.warn(`This extension registered no "${a}" slot`);
}, se = new URL(import.meta.url).origin;
let p = null;
const v = () => {
  if (!p) throw new Error("The Builder SDK is not connected yet");
  return p;
}, ie = (e) => typeof e == "object" && e !== null && e.type === "connect" && e.v === 1, b = (e) => document.documentElement.setAttribute("data-theme", String(e)), ce = async (e, t) => {
  p = X(t), p.listen("theme", b), p.handle("action.invoke", ee), b(e.theme), e.props, te(e.slot), await import(
    /* @vite-ignore */
    e.entry
  ), oe();
}, le = () => {
  window.addEventListener("message", (e) => {
    e.origin === se && (p || !ie(e.data) || !e.ports[0] || ce(e.data, e.ports[0]));
  });
}, s = (e, t) => v().call(e, t), l = (e, t) => {
  if (ne() !== "main") return Promise.resolve();
  const r = s(e, t);
  return r.catch((i) => {
    if (i.code === "unknown_method") {
      console.warn(`[builder] this Builder has no "${e}", so that surface is skipped`);
      return;
    }
    console.error(`[builder] "${e}" was refused`, i);
  }), r;
}, ue = {
  register: ({ load: e, ...t }) => (e && E("panel", { load: e }), l("leftPanel.register", t)),
  unregister: (e) => s("leftPanel.unregister", { name: e }),
  update: (e, t) => s("leftPanel.update", { name: e, patch: t })
}, ae = {
  register: (e) => l("toolbar.register", e),
  unregister: (e) => s("toolbar.unregister", { name: e }),
  update: (e, t) => s("toolbar.update", { name: e, patch: t })
}, pe = {
  register: (e) => l("contextMenu.register", e),
  unregister: (e) => s("contextMenu.unregister", { name: e }),
  update: (e, t) => s("contextMenu.update", { name: e, patch: t })
}, de = {
  registerSection: (e) => l("properties.registerSection", e),
  unregisterSection: (e) => s("properties.unregisterSection", { name: e }),
  /** Replaces the whole list, for a control list that depends on the extension's own state. */
  setControls: (e, t) => s("properties.setControls", { name: e, controls: t }),
  update: (e, t) => s("properties.update", { name: e, patch: t })
}, fe = {
  registerItem: ({ load: e, ...t }) => (e && E("settings", { load: e }), l("settings.registerItem", t)),
  unregisterItem: (e) => s("settings.unregisterItem", { name: e }),
  update: (e, t) => s("settings.update", { name: e, patch: t })
}, ge = {
  /** The whole snapshot, once. For startup. */
  get: () => s("context.get"),
  /**
   * Names the fields this extension cares about, so the host sends nothing else
   * and only when one of them changes.
   *
   * Use it for a fact no rule can state — `isSVG` is in the snapshot but is not
   * a rule key — and push the answer back with `update`. Use `showWhen` for
   * anything the rule vocabulary already covers: it costs no messages.
   */
  subscribe: (e, t) => {
    const r = v().listen("context", (i) => t(i));
    return l("context.subscribe", { fields: e }), r;
  }
}, he = {
  /**
   * The handler stays in this frame, and the host learns only the name.
   *
   * Held in every frame and named to the host by the entry frame alone, so the
   * host always calls the frame that outlives the others.
   */
  register: (e, t) => (Y(e, t), l("actions.register", { name: e })),
  unregister: (e) => (Z(e), s("actions.unregister", { name: e })),
  /** Runs an action this extension owns, from any of its frames. */
  run: (e, t) => s("actions.run", { name: e, context: t })
}, Oe = {
  /**
   * Imperative startup work, in the hidden entry frame only.
   *
   * Registrations do not belong here. They are declarations, and every frame
   * needs to read them, so they go at module scope.
   */
  main: (e) => re(e),
  /**
   * A dialog has no registration to hang a loader on: it is opened by
   * `ui.openDialog`, never registered. So it declares its document on its own.
   * A panel and a settings page carry `load` on the item that shows them.
   */
  dialog: (e) => E("dialog", e),
  /** One tab, registered from the entry frame and drawn by the host (Tier C). */
  leftPanel: ue,
  /** A descriptor. Builder draws the button and posts the action back (Tier A). */
  toolbar: ae,
  /** A row in the block menu. Its rule is answered for the block under the cursor. */
  contextMenu: pe,
  /** Tier B. A list naming Builder's own controls, which the host renders. */
  properties: de,
  /** One page in the settings dialog, and the document it loads. */
  settings: fe,
  /** The editor snapshot: read it once, or name the fields to be told about. */
  context: ge,
  /** The functions this extension owns. A descriptor names one, the host calls it. */
  actions: he,
  host: {
    /** Which Builder this extension landed in. An extension ships on its own schedule. */
    info: () => v().call("host.info")
  }
};
le();
export {
  Oe as default
};
