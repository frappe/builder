import { builderSettings } from "@/data/builderSettings";
import { isMounted } from "@/utils/frappePage";
import createDOMPurify from "dompurify";

/**
 * On frappe.page the editors of every site share the app host's origin, so markup or a
 * script of one site that runs in the canvas could reach the editor of another. There the
 * canvas draws block HTML without anything that runs, and block scripts run only on the
 * live site and in its preview. Off frappe.page the canvas behaves as it always did.
 */

// its own instance: the hook below must not reach the markdown that the AI panel sanitizes
const purify = createDOMPurify(window);

const isSameOrigin = (url: string) => {
	try {
		return new URL(url, window.location.href).origin === window.location.origin;
	} catch {
		return false;
	}
};

const isScriptURL = (url: unknown) => {
	try {
		return new URL(String(url), window.location.href).protocol === "javascript:";
	} catch {
		return false;
	}
};

// a same-origin frame would load a page of the site, scripts and all, with the editor's origin
purify.addHook("afterSanitizeAttributes", (node) => {
	if (node.tagName === "IFRAME" && isSameOrigin(node.getAttribute("src") || "")) {
		node.setAttribute("sandbox", "");
	}
});

const SANITIZE_OPTIONS = {
	// embeds are iframes, and font stylesheets come in as links
	ADD_TAGS: ["iframe", "link"],
	ADD_ATTR: ["allow", "allowfullscreen", "frameborder", "scrolling", "target"],
	FORBID_ATTR: ["srcdoc"],
	// without it a leading <style> parses into <head> and is dropped
	FORCE_BODY: true,
};

export function sanitizeBlockHTML(html: string): string {
	return isMounted ? purify.sanitize(html, SANITIZE_OPTIONS) : html;
}

// a block's element comes from its stored JSON, so it could name one that loads or runs code
const ACTIVE_TAGS = new Set(["script", "object", "embed", "applet", "frame", "frameset", "base", "meta"]);

/** The element the canvas draws for a block's tag: an active one is drawn as a plain div. */
export function canvasTag(tag: string): string {
	return isMounted && ACTIVE_TAGS.has(tag.trim().toLowerCase()) ? "div" : tag;
}

const URL_ATTRIBUTES = new Set(["href", "src", "action", "formaction", "xlink:href", "data"]);

/** Drops what would run from a block's attributes. `keep` holds the ones Builder itself passes. */
export function isolateBlockAttributes(tag: string, attributes: Record<string, unknown>, keep: object) {
	if (!isMounted) return;
	for (const [name, value] of Object.entries(attributes)) {
		if (name in keep) continue;
		const key = name.trim().toLowerCase();
		if (key.startsWith("on") || key === "srcdoc" || (URL_ATTRIBUTES.has(key) && isScriptURL(value))) {
			delete attributes[name];
		}
	}
	if (tag === "iframe" && isSameOrigin(String(attributes.src ?? ""))) attributes.sandbox = "";
}

export function blockScriptsMode() {
	if (isMounted) return "Don't Execute";
	return builderSettings.doc?.execute_block_scripts_in_editor ?? "Restricted";
}
