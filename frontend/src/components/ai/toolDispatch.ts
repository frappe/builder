import type Block from "@/block";
import type useCanvasStore from "@/stores/canvasStore";
import type usePageStore from "@/stores/pageStore";
import { getBlockInstance } from "@/utils/helpers";
import { ref } from "vue";
import { normalizeStyles } from "./normalizeStyles";
import type { AffectedBlock, AffectedScript } from "./types";
import {
	bindingEntry,
	buildRepeaterDataScript,
	convertYAMLtoBlock,
	parseBlock,
	STANDARD_ATTRS,
} from "./yaml";

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
		// `bind` = {property: data_key} → dynamicValues (same mapping as yaml.ts).
		// One entry per property: a re-bind replaces, a null value unbinds.
		if (args.bind && typeof args.bind === "object" && !Array.isArray(args.bind)) {
			for (const [rawProp, field] of Object.entries(args.bind as Record<string, string | null>)) {
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
				// expanded block tree (server-assigned ids — the canvas must key the same
				// refs the agent's later edits target); the YAML streamed earlier was only
				// the live preview. args.yaml is the legacy fallback (recovered
				// YAML-as-content turns).
				if (Array.isArray(args.blocks) && args.blocks.length) {
					this.pageStore.pageBlocks = [getBlockInstance(args.blocks[0])];
					this.canvasStore.activeCanvas?.setRootBlock(this.pageStore.pageBlocks[0] as Block, false);
					if (args.data_script) this.pageStore.applyRepeaterDataScript(args.data_script as string);
					return;
				}
				this.applyPageYaml(args.yaml as string, true);
				return;
			}
			case "set_page_blocks": {
				// A server tool rewrote the tree; replace it wholesale. Blocks keep
				// their blockIds, so refs/selection stay valid — unlike generate_page.
				const root = args.blocks as Record<string, any>;
				if (!root) return;
				this.pageStore.pageBlocks = [getBlockInstance(root)];
				this.canvasStore.activeCanvas?.setRootBlock(this.pageStore.pageBlocks[0] as Block, false);
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
				// block_json is the server-expanded block, refs (whole subtree) included —
				// the canvas must use the same ids the agent chains follow-up edits onto.
				const newBlock = getBlockInstance(
					(args.block_json as Record<string, any>) ??
						convertYAMLtoBlock(args.block as Record<string, any>),
				);
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
				// Scripts are server-authoritative (SCRIPT_TWIN_TOOLS): the loop has
				// already persisted the change — only mirror the local UI state.
				const existing = this.pageStore.activePageScripts.find(
					(s) => s.name === (args.script_name as string),
				);
				if (existing) {
					existing.script = args.script as string;
					if (args.script_type) existing.script_type = args.script_type as any;
				}
				this.pendingScriptOps.value.push(Promise.resolve(args.script_name as string));
				return;
			}
			case "set_page_script": {
				// Server-authoritative like update_script: the doc exists and is attached.
				if (!args.script_name) return;
				this.pageStore.activePageScripts.push({
					name: args.script_name as string,
					script_type: ((args.script_type as string) || "JavaScript") as any,
					script: args.script as string,
				} as any);
				this.pendingScriptOps.value.push(Promise.resolve(args.script_name as string));
				return;
			}
			case "attach_page_script": {
				// Server-authoritative: an existing shared doc was linked to this page;
				// the server enriched the op with its type and content for the list.
				const name = args.script_name as string;
				if (!name || this.pageStore.activePageScripts.some((s) => s.name === name)) return;
				this.pageStore.activePageScripts.push({
					name,
					script_type: ((args.script_type as string) || "JavaScript") as any,
					script: (args.script as string) || "",
				} as any);
				this.pendingScriptOps.value.push(Promise.resolve(name));
				return;
			}
		}
	}
}
