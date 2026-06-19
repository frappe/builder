import type Block from "@/block";
import type useCanvasStore from "@/stores/canvasStore";
import type usePageStore from "@/stores/pageStore";
import type { BuilderClientScript } from "@/types/Builder/BuilderClientScript";
import { getBlockInstance } from "@/utils/helpers";
import { createResource } from "frappe-ui";
import { ref } from "vue";
import type { AffectedBlock, AffectedScript } from "./types";
import { buildRepeaterDataScript, convertYAMLtoBlock, parseBlock, STANDARD_ATTRS } from "./yaml";

type PageStore = ReturnType<typeof usePageStore>;
type CanvasStore = ReturnType<typeof useCanvasStore>;

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
		const changedProps = this.extractChangedProps(toolName, args);
		if (!changedProps.length) return;

		const trackBlock = (blockId: string) => {
			if (!blockId) return;
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

		if (["update_block", "remove_block", "move_block"].includes(toolName)) {
			trackBlock(args.block_id as string);
		} else if (toolName === "add_block") {
			trackBlock(args.parent_block_id as string);
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
				if (args.base_styles) {
					Object.entries(args.base_styles).forEach(([key, value]) =>
						block.setBaseStyle(key as any, value as StyleValue),
					);
				}
				if (args.mobile_styles) {
					Object.entries(args.mobile_styles).forEach(([key, value]) => {
						block.mobileStyles[key] = value as StyleValue;
					});
				}
				if (args.tablet_styles) {
					Object.entries(args.tablet_styles).forEach(([key, value]) => {
						block.tabletStyles[key] = value as StyleValue;
					});
				}
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
				const op = createResource({ url: "frappe.client.insert" })
					.submit({
						doc: { doctype: "Builder Client Script", script_type: scriptType, script: args.script as string },
					})
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
