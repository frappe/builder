// @ts-ignore
import yaml from "js-yaml";
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
		const lines = cleaned.split("\n");
		for (let i = lines.length - 1; i > 0; i--) {
			try {
				const parsed = yaml.load(lines.slice(0, i).join("\n"));
				if (parsed) return parsed;
			} catch {}
		}
	}
	return null;
}

/** Convert the agent's compact block YAML into the editor's BlockOptions shape. */
export function convertYAMLtoBlock(yamlBlock: Record<string, any>): BlockOptions {
	if (!yamlBlock || typeof yamlBlock !== "object" || Array.isArray(yamlBlock)) return yamlBlock;
	const ensureObject = (value: any) =>
		value && typeof value === "object" && !Array.isArray(value) ? value : {};
	const ensureArray = (value: any) => (Array.isArray(value) ? value : []);
	const block: BlockOptions = {
		element: yamlBlock.el || "div",
		blockName: yamlBlock.name || "",
		baseStyles: ensureObject(yamlBlock.style),
		attributes: ensureObject(yamlBlock.attrs),
		mobileStyles: ensureObject(yamlBlock.m_style),
		tabletStyles: ensureObject(yamlBlock.t_style),
		classes: ensureArray(yamlBlock.classes),
	};
	if (yamlBlock.id) {
		block.blockId = yamlBlock.id;
		block.originalElement = yamlBlock.id === "root" ? "body" : undefined;
	}
	if (yamlBlock.text) block.innerText = yamlBlock.text;
	if (yamlBlock.component) block.extendedFromComponent = yamlBlock.component;
	if (yamlBlock.child_of) block.isChildOfComponent = yamlBlock.child_of;
	block.children = Array.isArray(yamlBlock.c) ? yamlBlock.c.map(convertYAMLtoBlock) : [];
	return block;
}

export function parseBlock(raw: string): BlockOptions | null {
	const parsed = getValidPartialYAML(raw);
	if (!parsed) return null;
	const block = Array.isArray(parsed) ? parsed[0] : parsed;
	return block && typeof block === "object" && block.el ? convertYAMLtoBlock(block) : null;
}
