<template>
	<div class="flex w-full flex-col gap-2">
		<SplitPropertyControl
			propertyKey="gap"
			label="Gap"
			:splits="splits"
			:toControlValues="toControlValues"
			:toModelValue="toModelValue"
			:getModelValue="readValue"
			:getPlaceholder="getPlaceholder"
			:getMergedValue="getMergedValue"
			:splitOptions="SPLIT_OPTIONS"
			:setModelValue="setModelValue" />
	</div>
</template>

<script lang="ts" setup>
import SplitPropertyControl from "@/components/Controls/SplitPropertyControl.vue";
import type Block from "@/block";
import blockController from "@/utils/blockController";
import { collapseGapShorthand, expandGapShorthand } from "@/utils/cssUtils";
import { computed } from "vue";

const isColumnDirection = computed(() =>
	String(blockController.getNativeStyle("flexDirection") || blockController.getCascadingStyle("flexDirection") || "").startsWith("column"),
);

const splits = computed(() => isColumnDirection.value ? [{ label: "H" }, { label: "V" }] : [{ label: "V" }, { label: "H" }]);

const getBlockGap = (block: Block): [string, string] => {
	const [exR, exC] = expandGapShorthand(block.getNativeStyle("gap"));
	return [String(block.getNativeStyle("rowGap") ?? "").trim() || exR, String(block.getNativeStyle("columnGap") ?? "").trim() || exC];
};

const getEffectiveGap = (): [string, string] => {
	const blocks = blockController.getSelectedBlocks();
	if (!blocks.length) return ["", ""];
	let [r, c] = getBlockGap(blocks[0]);
	for (let i = 1; i < blocks.length; i++) {
		const [bR, bC] = getBlockGap(blocks[i]);
		if (r !== bR) r = "Mixed";
		if (c !== bC) c = "Mixed";
	}
	return [r, c];
};

const readValue = (state: string | null = null) => {
	if (state) return String(blockController.getNativeStyle(`${state}:gap`) ?? "");
	const [r, c] = getEffectiveGap();
	if (r === "Mixed" || c === "Mixed") return r === "Mixed" && c === "Mixed" ? "Mixed" : collapseGapShorthand([r, c]);
	return !r && !c ? "" : r === c ? r : collapseGapShorthand([r, c]);
};

const getPlaceholder = () => String(blockController.getCascadingStyle("gap") ?? "unset");

const toControlValues = (value: unknown) => {
	const [r, c] = typeof value === "string" && value.includes("Mixed") ? getEffectiveGap() : expandGapShorthand(value);
	return isColumnDirection.value ? [c, r] : [r, c];
};

const toModelValue = (parts: StyleValue[], changedIndex?: number) => ({
	type: "gap-split",
	rowGap: isColumnDirection.value ? parts[1] : parts[0],
	colGap: isColumnDirection.value ? parts[0] : parts[1],
	changedAxis: changedIndex !== undefined ? ((isColumnDirection.value ? changedIndex === 0 : changedIndex === 1) ? "columnGap" : "rowGap") : null,
});

const SPLIT_OPTIONS = [
	{ label: "Use for all", value: false, icon: "lucide-square", tooltip: "Use for all" },
	{ label: "Set separately", value: true, icon: "lucide-layout-grid", tooltip: "Set separately" },
];

const getMergedValue = (parts: StyleValue[]) => parts.find((part) => part && String(part) !== "Mixed") ?? 0;

const setModelValue = (val: unknown) => {
	if (typeof val === "boolean") return;
	const payload = val && typeof val === "object" && (val as any).type === "gap-split" ? (val as any) : null;

	blockController.getSelectedBlocks().forEach((block) => {
		if (payload) {
			const [exR, exC] = getBlockGap(block);
			let r = (payload.changedAxis === "columnGap" ? exR : String(payload.rowGap ?? "").trim());
			let c = (payload.changedAxis === "rowGap" ? exC : String(payload.colGap ?? "").trim());
			r = r === "Mixed" ? "" : r;
			c = c === "Mixed" ? "" : c;

			block.setStyle("gap", null);
			if (r && c && r === c) {
				block.setStyle("rowGap", null);
				block.setStyle("columnGap", null);
				block.setStyle("gap", r);
			} else {
				block.setStyle("rowGap", r || null);
				block.setStyle("columnGap", c || null);
			}
		} else {
			const value = String(val ?? "").trim();
			block.setStyle("rowGap", null);
			block.setStyle("columnGap", null);
			block.setStyle("gap", value || null);
		}
	});
};
</script>
