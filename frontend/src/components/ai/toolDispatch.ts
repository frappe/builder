import type Block from "@/block";
import type BuilderCanvas from "@/components/BuilderCanvas.vue";
import type usePageStore from "@/stores/pageStore";
import type { BuilderClientScript } from "@/types/doctypes";
import { findBlockInTree } from "@/utils/block/tree";
import { getBlockInstance } from "@/utils/helpers";
import { ref, type Ref } from "vue";
import { bindingEntry, STANDARD_ATTRS, visibilityCondition } from "./blockFields";
import type { AffectedBlock, AffectedScript } from "./types";

type PageStore = ReturnType<typeof usePageStore>;
export type PageCanvas = Ref<InstanceType<typeof BuilderCanvas> | null>;

const SCRIPT_TOOLS = new Set([
	"update_script",
	"set_page_script",
	"attach_page_script",
	"detach_page_script",
]);

/** The store keeps what the page fetches for each script: its name, type and code. */
const scriptDoc = (name: string, scriptType: unknown, script: unknown): BuilderClientScript => ({
	name,
	creation: "",
	modified: "",
	owner: "",
	modified_by: "",
	script_type: typeof scriptType === "string" && scriptType ? scriptType : "JavaScript",
	script: typeof script === "string" ? script : "",
});

export type AffectedItems = { blocks: AffectedBlock[]; scripts: AffectedScript[] };

function addAffected<T extends { changedProps: string[] }, K extends keyof T>(list: T[], key: K, item: T) {
	const existing = list.find((entry) => entry[key] === item[key]);
	if (existing) existing.changedProps = [...new Set([...existing.changedProps, ...item.changedProps])];
	else list.push(item);
}

/**
 * Applies the agent's client-side tool operations to the page's block tree and
 * tracks what changed (for the "affected items" UI). Holds its own per-turn
 * pending state; call `reset()` at the start of each turn.
 *
 * Ops target the page canvas, never the active one: while a component is open on
 * its own canvas, the active canvas holds that component, not the page Bob edits.
 */
export class ToolDispatcher {
	readonly pendingAffectedBlocks = ref<AffectedBlock[]>([]);
	readonly pendingAffectedScripts = ref<AffectedScript[]>([]);

	constructor(
		private readonly pageStore: PageStore,
		private readonly pageCanvas: PageCanvas,
	) {}

	reset() {
		this.pendingAffectedBlocks.value = [];
		this.pendingAffectedScripts.value = [];
	}

	private findBlock(blockId: string, within?: Block): Block | null {
		const root = within ?? this.pageCanvas.value?.getRootBlock();
		return root ? findBlockInTree(blockId, [root]) : null;
	}

	/** Swap in a whole new page tree. Streamed previews keep the undo stack; the
	 * final apply resets it once instead of on every preview frame. */
	private replaceRoot(blockData: BlockOptions, resetHistory: boolean) {
		const root = getBlockInstance(blockData);
		this.pageStore.pageBlocks = [root];
		this.pageCanvas.value?.setRootBlock(root, false, resetHistory);
	}

	/** Show a preview frame of a page still being generated. The final
	 * generate_page op replaces it and resets the undo stack once. */
	applyPreview(root: BlockOptions) {
		try {
			this.replaceRoot(root, false);
		} catch {}
	}

	private extractChangedProps(toolName: string, args: Record<string, any>): string[] {
		switch (toolName) {
			case "update_block": {
				const props: string[] = [];
				if (args.base_styles) props.push(...Object.keys(args.base_styles));
				if (args.name !== undefined) props.push("name");
				if (args.mobile_styles) props.push(...Object.keys(args.mobile_styles).map((k) => `m:${k}`));
				if (args.tablet_styles) props.push(...Object.keys(args.tablet_styles).map((k) => `t:${k}`));
				if (args.attributes) props.push(...Object.keys(args.attributes));
				if (args.inner_text !== undefined) props.push("text");
				if (args.inner_html !== undefined) props.push("html");
				if (args.element !== undefined) props.push("element");
				if (args.classes !== undefined) props.push("classes");
				if (args.props) props.push("props");
				if (args.client_script) props.push("client_script");
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
			case "set_page_script":
				return ["created"];
			case "attach_page_script":
				return ["attached"];
			case "detach_page_script":
				return ["removed"];
			default:
				return [];
		}
	}

	/** Record what a tool op changed. Call BEFORE applying so remove_block can
	 * still read the block's info while it exists. */
	trackAffectedItem(toolName: string, args: Record<string, any>, into: AffectedItems = this.pending()) {
		const trackBlock = (blockId: string, changedProps: string[]) => {
			if (!blockId || !changedProps.length) return;
			const block = this.findBlock(blockId);
			addAffected(into.blocks, "block_id", {
				block_id: blockId,
				blockName: block?.blockName || "",
				element: block?.element || "div",
				changedProps,
			});
		};

		const changedProps = this.extractChangedProps(toolName, args);
		if (!changedProps.length) return;

		if (["update_block", "remove_block", "move_block"].includes(toolName)) {
			trackBlock(args.block_id as string, changedProps);
		} else if (toolName === "add_block") {
			trackBlock(args.parent_block_id as string, changedProps);
		} else if (SCRIPT_TOOLS.has(toolName)) {
			const scriptName = args.script_name as string | undefined;
			if (scriptName) addAffected(into.scripts, "script_name", { script_name: scriptName, changedProps });
		}
	}

	/** Fold items recorded aside (a batch whose chat wasn't known yet) into this turn's. */
	mergeAffected(items: AffectedItems) {
		const pending = this.pending();
		items.blocks.forEach((item) => addAffected(pending.blocks, "block_id", item));
		items.scripts.forEach((item) => addAffected(pending.scripts, "script_name", item));
	}

	private pending(): AffectedItems {
		return { blocks: this.pendingAffectedBlocks.value, scripts: this.pendingAffectedScripts.value };
	}

	/** Merge one block's worth of changes (styles/attrs/text/element/classes) into
	 * `block`: the canvas twin of tree.merge_block_update, reading the same args. */
	private applyBlockUpdate(block: Block, args: Record<string, any>) {
		// The server normalized these; a null value removes the property.
		for (const [key, target] of [
			["base_styles", block.baseStyles],
			["mobile_styles", block.mobileStyles],
			["tablet_styles", block.tabletStyles],
		] as const) {
			for (const [prop, value] of Object.entries((args[key] as Record<string, any>) || {})) {
				if (value === null) delete target[prop];
				else target[prop] = value;
			}
		}
		if (args.name !== undefined) block.blockName = args.name;
		if (args.attributes) {
			Object.entries(args.attributes).forEach(([key, value]) => {
				if (STANDARD_ATTRS.has(key)) {
					block.setAttribute(key, value as string | undefined);
					delete block.customAttributes[key];
				} else {
					block.customAttributes[key] = value as string | undefined;
				}
			});
		}
		// props = {name: value}. Starts from the instance's OWN props so untouched
		// defaults keep flowing; a first override borrows its config from the merged view.
		if (args.props && typeof args.props === "object" && !Array.isArray(args.props)) {
			const root = block.getPropsRoot() || block;
			const own = { ...(root.props || {}) };
			const merged = block.getBlockProps();
			for (const [name, value] of Object.entries(args.props as Record<string, any>)) {
				if (value === null) {
					delete own[name];
					continue;
				}
				// Typed like the server twin (tree.prop_config), so the props panel
				// renders a proper input for a fresh declaration.
				const propType = Array.isArray(value)
					? "array"
					: typeof value === "boolean"
						? "boolean"
						: typeof value === "number"
							? "number"
							: typeof value === "object"
								? "object"
								: "string";
				const config = own[name] ||
					merged[name] || {
						isDynamic: false,
						isPassedDown: false,
						comesFrom: null,
						isStandard: true,
						propOptions: { type: propType },
					};
				own[name] = { ...config, value };
			}
			block.setBlockProps(own);
		}
		// client_script = {js?, css?}; null clears a key.
		if (args.client_script && typeof args.client_script === "object" && !Array.isArray(args.client_script)) {
			for (const kind of ["js", "css"] as const) {
				if (!(kind in args.client_script)) continue;
				const value = (args.client_script as Record<string, string | null>)[kind];
				if (value === null) delete block.clientScript[kind];
				else block.clientScript[kind] = value;
			}
		}
		if (args.inner_text !== undefined) block.setInnerHTML(args.inner_text);
		if (args.inner_html !== undefined) block.setInnerHTML(args.inner_html);
		if (args.element !== undefined) block.element = args.element;
		if (args.classes !== undefined) block.classes = args.classes;
		// `bind` = {property: data_key} → dynamicValues (same mapping as page_writer).
		// One entry per property: a re-bind replaces, a null value unbinds.
		if (args.bind && typeof args.bind === "object" && !Array.isArray(args.bind)) {
			for (const [rawProp, field] of Object.entries(args.bind as Record<string, string | null>)) {
				if (rawProp === "visible") {
					block.visibilityCondition = field == null ? undefined : visibilityCondition(field);
					continue;
				}
				const property = rawProp === "text" ? "innerHTML" : rawProp;
				const kept = block.dynamicValues.filter((dv: any) => dv.property !== property);
				block.dynamicValues.splice(0, block.dynamicValues.length, ...kept);
				if (field != null) {
					block.dynamicValues.push(bindingEntry(property, field));
				}
			}
		}
	}

	applyToolOperation(toolName: string, args: Record<string, any>) {
		switch (toolName) {
			case "generate_page": {
				// Final authoritative apply. The server persisted the page and ships the
				// expanded block tree (server-assigned ids: the canvas must key the same
				// refs the agent's later edits target); the frames streamed earlier were
				// only the live preview.
				if (!Array.isArray(args.blocks) || !args.blocks.length) return;
				this.replaceRoot(args.blocks[0], true);
				if (args.data_script) this.pageStore.applyRepeaterDataScript(args.data_script as string);
				return;
			}
			case "set_page_blocks": {
				// A server tool rewrote the tree; replace it wholesale. Blocks keep
				// their blockIds, so refs/selection stay valid — unlike generate_page.
				if (!args.blocks) return;
				this.replaceRoot(args.blocks, true);
				return;
			}
			case "update_block": {
				const block = this.findBlock(args.block_id);
				if (!block) return;
				this.applyBlockUpdate(block, args);
				return;
			}
			case "add_block": {
				const parent = this.findBlock(args.parent_block_id);
				if (!parent) return;
				// block_json is the server-expanded block, refs (whole subtree) included:
				// the canvas must use the same ids the agent chains follow-up edits onto.
				if (!args.block_json) return;
				const newBlock = getBlockInstance(args.block_json as BlockOptions);
				if (args.after_block_id) {
					const sibling = this.findBlock(args.after_block_id, parent);
					if (sibling) {
						parent.addChildAfter(newBlock, sibling);
						return;
					}
				}
				parent.addChild(newBlock, typeof args.index === "number" ? args.index : null);
				return;
			}
			case "remove_block": {
				const block = this.findBlock(args.block_id);
				if (!block) return;
				block.getParentBlock()?.removeChild(block);
				return;
			}
			case "move_block": {
				const block = this.findBlock(args.block_id);
				const newParent = this.findBlock(args.new_parent_block_id);
				if (!block || !newParent) return;
				block.getParentBlock()?.removeChild(block);
				if (args.after_block_id) {
					const sibling = this.findBlock(args.after_block_id, newParent);
					if (sibling) {
						newParent.addChildAfter(block, sibling);
						return;
					}
				}
				newParent.addChild(block, typeof args.index === "number" ? args.index : null, false);
				return;
			}
			case "update_script": {
				// Scripts are server-authoritative (SCRIPT_TWIN_TOOLS): the loop has
				// already persisted the change, so only mirror the local UI state.
				const existing = this.pageStore.activePageScripts.find((s) => s.name === args.script_name);
				if (existing) {
					existing.script = args.script;
					if (args.script_type) existing.script_type = args.script_type;
				}
				this.pageStore.scriptsVersion++;
				return;
			}
			case "set_page_script":
			case "attach_page_script": {
				// Server-authoritative: the doc exists and is attached, and the server
				// enriched the op with its type and content for the list.
				const name = args.script_name;
				if (!name || this.pageStore.activePageScripts.some((s) => s.name === name)) return;
				this.pageStore.activePageScripts.push(scriptDoc(name, args.script_type, args.script));
				this.pageStore.scriptsVersion++;
				return;
			}
			case "detach_page_script": {
				const scripts = this.pageStore.activePageScripts;
				const index = scripts.findIndex((s) => s.name === args.script_name);
				if (index === -1) return;
				scripts.splice(index, 1);
				this.pageStore.scriptsVersion++;
				return;
			}
			case "load_plugin": {
				// Bob's write_plugin waits on this load's report, so it runs now, outside the page edit
				const { plugin, label, version, entry_url, token } = args;
				void import("@/plugins/tryPlugin").then(({ tryPlugin }) =>
					tryPlugin({ plugin, label, version, entry_url, token }),
				);
				return;
			}
		}
	}
}
