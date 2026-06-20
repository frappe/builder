// @ts-ignore
import yaml from "js-yaml";
import { lucideSVG } from "./lucideIcon";
import { normalizeStyles } from "./normalizeStyles";
import type { ChatMessage } from "./types";

/** HTML attributes that map to first-class Block attributes (vs. customAttributes). */
export const STANDARD_ATTRS = new Set(["src", "alt", "href", "title", "value", "type", "placeholder"]);

export function buildLocalMessage(
	role: "user" | "assistant",
	content: string,
	metadata: Record<string, any> = {},
): ChatMessage {
	return {
		id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
		role,
		content,
		created_at: new Date().toISOString(),
		metadata,
	} as ChatMessage;
}

/** Parse possibly-incomplete YAML (a stream in progress), trimming trailing lines
 * until it parses. Tolerates markdown fences. */
export function getValidPartialYAML(yamlStr: string): any {
	let cleaned = yamlStr.trim();
	if (cleaned.startsWith("```")) {
		const lines = cleaned.split("\n");
		lines.shift();
		if (lines.at(-1)?.startsWith("```")) lines.pop();
		cleaned = lines.join("\n");
	}
	try {
		return yaml.load(cleaned);
	} catch {
		// Mid-stream YAML fails because the TAIL is incomplete — dropping the last
		// (partial) line or few usually yields a valid prefix. Bound the retry to a
		// few trailing lines instead of scanning all N (that was O(N²) per chunk).
		const lines = cleaned.split("\n");
		const floor = Math.max(1, lines.length - 12);
		for (let i = lines.length - 1; i >= floor; i--) {
			try {
				const parsed = yaml.load(lines.slice(0, i).join("\n"));
				if (parsed) return parsed;
			} catch {}
		}
	}
	return null;
}

/** Convert the agent's compact block YAML into the editor's BlockOptions shape.
 * `isRoot` marks the top-level block of a generated page as the <body>; the editor
 * then derives blockId="root" from that (Block.isRoot() === originalElement "body").
 * Block ids are NOT carried in the YAML — the editor assigns them. */
export function convertYAMLtoBlock(yamlBlock: Record<string, any>, isRoot = false): BlockOptions {
	if (!yamlBlock || typeof yamlBlock !== "object" || Array.isArray(yamlBlock)) return yamlBlock;
	const ensureObject = (value: any) =>
		value && typeof value === "object" && !Array.isArray(value) ? value : {};
	const ensureArray = (value: any) => (Array.isArray(value) ? value : []);
	// Icon reference: the agent emits `{ icon: <lucide-name> }` instead of pasting
	// raw SVG/emoji — we bake the SVG into innerHTML here (renders everywhere) and
	// keep the name in data-lucide so the server can re-collapse it for cheap edit context.
	if (yamlBlock.icon) return convertIconBlock(yamlBlock, ensureObject, ensureArray);
	const block: BlockOptions = {
		element: yamlBlock.el || "div",
		blockName: yamlBlock.name || "",
		baseStyles: normalizeStyles(yamlBlock.style),
		attributes: ensureObject(yamlBlock.attrs),
		mobileStyles: normalizeStyles(yamlBlock.m_style),
		tabletStyles: normalizeStyles(yamlBlock.t_style),
		classes: ensureArray(yamlBlock.classes),
	};
	if (isRoot) block.originalElement = "body";
	if (yamlBlock.text) block.innerText = yamlBlock.text;
	if (yamlBlock.component) block.extendedFromComponent = yamlBlock.component;
	if (yamlBlock.child_of) block.isChildOfComponent = yamlBlock.child_of;
	// `bind` maps a template field to a loop-item key → dynamicValues. innerHTML/text
	// bind by content ("key"); anything else binds an HTML attribute (e.g. href, src).
	if (yamlBlock.bind && typeof yamlBlock.bind === "object" && !Array.isArray(yamlBlock.bind)) {
		block.dynamicValues = Object.entries(yamlBlock.bind).map(([prop, field]) =>
			prop === "innerHTML" || prop === "text"
				? { key: String(field), property: "innerHTML", type: "key" }
				: { key: String(field), property: prop, type: "attribute" },
		);
	}
	// NB: pass each child explicitly — Array.map would feed the index as `isRoot`.
	block.children = Array.isArray(yamlBlock.c) ? yamlBlock.c.map((c: any) => convertYAMLtoBlock(c)) : [];
	// `repeat` = a static repeater: ONE template + JSON data. The data array is NOT
	// stored on the block — it's collected into the page_data_script shim (see
	// buildRepeaterDataScript); the block keeps only the loop wiring + template child.
	if (yamlBlock.repeat && typeof yamlBlock.repeat === "object" && yamlBlock.repeat.item) {
		block.isRepeaterBlock = true;
		block.dataKey = { key: String(yamlBlock.repeat.data || ""), property: "innerHTML", type: "key" };
		block.children = [convertYAMLtoBlock(yamlBlock.repeat.item)];
	}
	return block;
}

/** Walk the raw generation YAML and collect each repeater's static data array,
 * keyed by its `repeat.data` key. */
function collectRepeaterData(node: any, out: Record<string, unknown[]>): void {
	if (!node || typeof node !== "object") return;
	if (Array.isArray(node)) {
		node.forEach((n) => collectRepeaterData(n, out));
		return;
	}
	const rep = node.repeat;
	if (rep && typeof rep === "object" && rep.data && Array.isArray(rep.items)) {
		out[String(rep.data)] = rep.items;
		collectRepeaterData(rep.item, out); // a template may itself nest a repeater
	}
	if (Array.isArray(node.c)) node.c.forEach((n: any) => collectRepeaterData(n, out));
}

/** Build the page_data_script shim for a generated page: `data.<key> = <json>` per
 * repeater. The AI supplies only JSON data — this fixed assignment is the ONLY code,
 * so there is no AI-authored Python. Returns "" when the page has no repeaters. */
export function buildRepeaterDataScript(yamlString: string): string {
	const parsed = getValidPartialYAML(yamlString);
	if (!parsed) return "";
	const out: Record<string, unknown[]> = {};
	collectRepeaterData(parsed, out);
	return Object.entries(out)
		.map(([key, items]) => `data.${key} = ${JSON.stringify(items)}`)
		.join("\n");
}

/** Expand a `{ icon: <lucide-name> }` node into an inline-SVG span block. */
function convertIconBlock(
	node: Record<string, any>,
	ensureObject: (v: any) => any,
	ensureArray: (v: any) => any[],
): BlockOptions {
	const name = String(node.icon).trim();
	const style = normalizeStyles(node.style);
	// Size lives on the WRAPPER (the inner svg fills it at 100%), so it stays
	// editable — resizing the block or setting style.width/height resizes the icon.
	const rawSize = node.size ?? "24px";
	const size = /^\d+$/.test(String(rawSize)) ? `${parseInt(String(rawSize), 10)}px` : String(rawSize);
	const svg = lucideSVG(name, Number(node.stroke) || 2);
	const block: BlockOptions = {
		element: "svg",
		blockName: node.name || `Icon: ${name}`,
		baseStyles: {
			display: "inline-flex",
			alignItems: "center",
			justifyContent: "center",
			lineHeight: "0",
			flexShrink: 0,
			width: size,
			height: size,
			...style, // explicit style.width/height/color override these defaults
		},
		attributes: ensureObject(node.attrs),
		customAttributes: { "data-lucide": name },
		mobileStyles: normalizeStyles(node.m_style),
		tabletStyles: normalizeStyles(node.t_style),
		classes: ensureArray(node.classes),
		children: [],
	};
	if (svg) block.innerHTML = svg;
	return block;
}

export function parseBlock(raw: string): BlockOptions | null {
	const parsed = getValidPartialYAML(raw);
	if (!parsed) return null;
	const block = Array.isArray(parsed) ? parsed[0] : parsed;
	return block && typeof block === "object" && block.el ? convertYAMLtoBlock(block, true) : null;
}
