import type Block from "@/block";
import type useCanvasStore from "@/stores/canvasStore";
import type usePageStore from "@/stores/pageStore";
import type { BuilderClientScript } from "@/types/Builder/BuilderClientScript";
import { getBlockInstance } from "@/utils/helpers";
import { createResource } from "frappe-ui";
import { ref } from "vue";
import { normalizeStyles } from "./normalizeStyles";
import type { AffectedBlock, AffectedScript } from "./types";
import { buildRepeaterDataScript, convertYAMLtoBlock, parseBlock, STANDARD_ATTRS } from "./yaml";

type PageStore = ReturnType<typeof usePageStore>;
type CanvasStore = ReturnType<typeof useCanvasStore>;

/** Make an AI-suggested script name safe to use as a Builder Client Script doc name:
 * keep letters/numbers/spaces/hyphens (the doc name is also used in the public file path),
 * collapse whitespace, and cap the length. Returns "" if nothing usable remains. */
function sanitizeScriptName(raw?: string): string {
	if (!raw || typeof raw !== "string") return "";
	return raw
		.trim()
		.replace(/[^\w\s-]/g, "")
		.replace(/\s+/g, " ")
		.trim()
		.slice(0, 40)
		.trim();
}

/**
 * Applies the agent's client-side tool operations to the canvas block tree and
 * tracks what changed (for the "affected items" UI and script undo). Holds its
 * own per-turn pending state; call `reset()` at the start of each turn.
 */
export class ToolDispatcher {
	readonly pendingScriptOps = ref<Promise<string | null>[]>([]);
	readonly pendingAffectedBlocks = ref<AffectedBlock[]>([]);
	readonly pendingAffectedScripts = ref<AffectedScript[]>([]);

	constructor(
		private readonly pageStore: PageStore,
		private readonly canvasStore: CanvasStore,
		private readonly getPageId: () => string,
	) {}

	private get rootBlock(): Block | null {
		return (this.pageStore.pageBlocks[0] || null) as Block | null;
	}

	reset() {
		this.pendingScriptOps.value = [];
		this.pendingAffectedBlocks.value = [];
		this.pendingAffectedScripts.value = [];
	}

	findBlockInTree(blockId: string, root?: Block | null): Block | null {
		const searchRoot = root !== undefined ? root : this.rootBlock;
		if (!searchRoot) return null;
		if (searchRoot.blockId === blockId) return searchRoot;
		for (const child of searchRoot.children || []) {
			const found = this.findBlockInTree(blockId, child as Block);
			if (found) return found;
		}
		return null;
	}

	/** Replace the entire page with a freshly generated YAML document.
	 * `persistRepeaterData` is true only on the FINAL apply — never while streaming
	 * (persisting per chunk would fire a network setValue + re-parse on every token). */
	applyPageYaml(yamlString: string, persistRepeaterData = false) {
		const block = parseBlock(yamlString);
		if (!block) return;
		try {
			this.pageStore.pageBlocks = [getBlockInstance(block)];
			this.canvasStore.activeCanvas?.setRootBlock(this.pageStore.pageBlocks[0] as Block, false);
			// Repeaters carry static JSON data; persist it as the page_data_script shim
			// so the loops render. Final apply only — see note above.
			if (persistRepeaterData) {
				const dataScript = buildRepeaterDataScript(yamlString);
				if (dataScript) this.pageStore.applyRepeaterDataScript(dataScript);
			}
		} catch {}
	}

	private extractChangedProps(toolName: string, args: Record<string, any>): string[] {
		switch (toolName) {
			case "update_block": {
				const props: string[] = [];
				if (args.base_styles) props.push(...Object.keys(args.base_styles));
				if (args.mobile_styles) props.push(...Object.keys(args.mobile_styles).map((k) => `m:${k}`));
				if (args.tablet_styles) props.push(...Object.keys(args.tablet_styles).map((k) => `t:${k}`));
				if (args.attributes) props.push(...Object.keys(args.attributes));
				if (args.inner_text !== undefined) props.push("text");
				if (args.inner_html !== undefined) props.push("html");
				if (args.element !== undefined) props.push("element");
				if (args.classes !== undefined) props.push("classes");
				return props;
			}
			case "add_block":
				return ["added child"];
			case "remove_block":
				return ["removed"];
			case "move_block":
				return ["moved"];
			case "update_script": {
				const props = ["script"];
				if (args.script_type) props.push("script_type");
				return props;
			}
			default:
				return [];
		}
	}

	/** Record what a tool op changed. Call BEFORE applying so remove_block can
	 * still read the block's info while it exists. */
	trackAffectedItem(toolName: string, args: Record<string, any>) {
		const trackBlock = (blockId: string, changedProps: string[]) => {
			if (!blockId || !changedProps.length) return;
			const block = this.findBlockInTree(blockId);
			const existing = this.pendingAffectedBlocks.value.find((b) => b.block_id === blockId);
			if (existing) {
				existing.changedProps = [...new Set([...existing.changedProps, ...changedProps])];
			} else {
				this.pendingAffectedBlocks.value.push({
					block_id: blockId,
					blockName: block?.blockName || "",
					element: block?.element || "div",
					changedProps,
				});
			}
		};

		// Batch edit: each block may have changed different props (patches mode), so
		// derive props per-block rather than once for the whole op.
		if (toolName === "update_blocks") {
			if (Array.isArray(args.patches)) {
				for (const patch of args.patches as Record<string, any>[]) {
					trackBlock(patch.block_id as string, this.extractChangedProps("update_block", patch));
				}
			} else {
				const props = this.extractChangedProps("update_block", args);
				for (const id of (args.block_ids as string[]) || []) trackBlock(id, props);
			}
			return;
		}

		const changedProps = this.extractChangedProps(toolName, args);
		if (!changedProps.length) return;

		if (["update_block", "remove_block", "move_block"].includes(toolName)) {
			trackBlock(args.block_id as string, changedProps);
		} else if (toolName === "add_block") {
			trackBlock(args.parent_block_id as string, changedProps);
		} else if (toolName === "update_script") {
			const scriptName = args.script_name as string | undefined;
			if (!scriptName) return;
			const existing = this.pendingAffectedScripts.value.find((s) => s.script_name === scriptName);
			if (existing) {
				existing.changedProps = [...new Set([...existing.changedProps, ...changedProps])];
			} else {
				this.pendingAffectedScripts.value.push({ script_name: scriptName, changedProps });
			}
		}
	}

	/** Merge one block's worth of changes (styles/attrs/text/element/classes) into
	 * `block`. Shared by update_block (single) and update_blocks (batch) so the two
	 * can never drift. Reads the same field names the tools declare. */
	private applyBlockUpdate(block: Block, args: Record<string, any>) {
		// Fix the model's mechanical CSS slips (camelCased values, missing units, …) at the
		// single point styles land — same pass the generation path uses (see normalizeStyles).
		const baseStyles = normalizeStyles(args.base_styles);
		const mobileStyles = normalizeStyles(args.mobile_styles);
		const tabletStyles = normalizeStyles(args.tablet_styles);
		Object.entries(baseStyles).forEach(([key, value]) => block.setBaseStyle(key as any, value as StyleValue));
		Object.entries(mobileStyles).forEach(([key, value]) => {
			block.mobileStyles[key] = value as StyleValue;
		});
		Object.entries(tabletStyles).forEach(([key, value]) => {
			block.tabletStyles[key] = value as StyleValue;
		});
		if (args.attributes) {
			Object.entries(args.attributes).forEach(([key, value]) => {
				if (STANDARD_ATTRS.has(key)) {
					block.setAttribute(key, value as string | undefined);
				} else {
					block.customAttributes[key] = value as string | undefined;
				}
			});
		}
		if (args.inner_text !== undefined) block.setInnerHTML(args.inner_text);
		if (args.inner_html !== undefined) block.setInnerHTML(args.inner_html);
		if (args.element !== undefined) block.element = args.element;
		if (args.classes !== undefined) block.classes = args.classes;
		// `bind` = {property: data_key} → dynamicValues (same mapping as yaml.ts).
		// One entry per property: a re-bind replaces, a null value unbinds.
		if (args.bind && typeof args.bind === "object" && !Array.isArray(args.bind)) {
			for (const [rawProp, field] of Object.entries(args.bind as Record<string, string | null>)) {
				const property = rawProp === "text" ? "innerHTML" : rawProp;
				const kept = block.dynamicValues.filter((dv: any) => dv.property !== property);
				block.dynamicValues.splice(0, block.dynamicValues.length, ...kept);
				if (field != null) {
					block.dynamicValues.push(
						property === "innerHTML"
							? { key: String(field), property: "innerHTML", type: "key" }
							: { key: String(field), property, type: "attribute" },
					);
				}
			}
		}
	}

	applyToolOperation(toolName: string, args: Record<string, any>) {
		switch (toolName) {
			case "generate_page": {
				// Final authoritative apply — persist repeater data here (not while streaming).
				this.applyPageYaml(args.yaml as string, true);
				return;
			}
			case "update_block": {
				const block = this.findBlockInTree(args.block_id);
				if (!block) return;
				this.applyBlockUpdate(block, args);
				return;
			}
			case "update_blocks": {
				// Per-block mode wins over uniform mode (matches the tool contract).
				if (Array.isArray(args.patches)) {
					for (const patch of args.patches as Record<string, any>[]) {
						const block = this.findBlockInTree(patch.block_id);
						if (block) this.applyBlockUpdate(block, patch);
					}
					return;
				}
				const ids = (args.block_ids as string[]) || [];
				for (const id of ids) {
					const block = this.findBlockInTree(id);
					if (block) this.applyBlockUpdate(block, args);
				}
				return;
			}
			case "add_block": {
				const parent = this.findBlockInTree(args.parent_block_id);
				if (!parent) return;
				const newBlock = getBlockInstance(convertYAMLtoBlock(args.block as Record<string, any>));
				if (args.after_block_id) {
					const sibling = this.findBlockInTree(args.after_block_id, parent);
					if (sibling) {
						parent.addChildAfter(newBlock, sibling);
						return;
					}
				}
				parent.addChild(newBlock, typeof args.index === "number" ? args.index : null);
				return;
			}
			case "remove_block": {
				const block = this.findBlockInTree(args.block_id);
				if (!block) return;
				block.getParentBlock()?.removeChild(block);
				return;
			}
			case "move_block": {
				const block = this.findBlockInTree(args.block_id);
				const newParent = this.findBlockInTree(args.new_parent_block_id);
				if (!block || !newParent) return;
				block.getParentBlock()?.removeChild(block);
				if (args.after_block_id) {
					const sibling = this.findBlockInTree(args.after_block_id, newParent);
					if (sibling) {
						newParent.addChildAfter(block, sibling);
						return;
					}
				}
				newParent.addChild(block, typeof args.index === "number" ? args.index : null, false);
				return;
			}
			case "update_script": {
				const op = createResource({ url: "frappe.client.set_value" })
					.submit({
						doctype: "Builder Client Script",
						name: args.script_name as string,
						fieldname: {
							script: args.script as string,
							...(args.script_type ? { script_type: args.script_type as string } : {}),
						},
					})
					.then(() => {
						const existing = this.pageStore.activePageScripts.find(
							(s) => s.name === (args.script_name as string),
						);
						if (existing) {
							existing.script = args.script as string;
							if (args.script_type) existing.script_type = args.script_type as any;
						}
						return args.script_name as string;
					})
					.catch(() => null);
				this.pendingScriptOps.value.push(op);
				return;
			}
			case "set_page_script": {
				const scriptType = (args.script_type as string) || "JavaScript";
				// Use the model's descriptive name as the doc name (autoname is "prompt"), so the
				// script list reads "Confetti On Load", not "JavaScript-52b52". Falls back to the
				// auto hash name if the chosen name is empty or already taken.
				const desiredName = sanitizeScriptName(args.name as string);
				const insertScript = (useName: boolean) =>
					createResource({ url: "frappe.client.insert" }).submit({
						doc: {
							doctype: "Builder Client Script",
							script_type: scriptType,
							script: args.script as string,
							...(useName && desiredName ? { name: desiredName } : {}),
						},
					}) as Promise<BuilderClientScript>;
				const op = insertScript(true)
					.catch(() => insertScript(false))
					.then((res: BuilderClientScript) =>
						createResource({ url: "frappe.client.insert" })
							.submit({
								doc: {
									doctype: "Builder Page Client Script",
									parent: this.getPageId(),
									parenttype: "Builder Page",
									parentfield: "client_scripts",
									builder_script: res.name,
								},
							})
							.then(() => {
								this.pageStore.activePageScripts.push(res);
								return res.name;
							}),
					)
					.catch(() => null);
				this.pendingScriptOps.value.push(op);
				return;
			}
		}
	}
}
