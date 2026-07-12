<template>
	<Popover v-model:open="popoverOpen" side="left" align="center" bare :offset="25">
		<template #trigger="{ open }">
			<div class="!block w-full">
			<div
				class="flex w-full items-center justify-between"
				@click.stop
				@pointerdown="selectActiveState"
				@focusin="updateActiveState">
				<StylePropertyControl
					propertyKey="borderRadius"
					:component="Input"
					label="Radius"
					:unitOptions="['px', '%']"
					:enableStates="true"
					placeholder="None"
					:getModelValue="() => getBorderRadiusValue(null)"
					:getVariantValue="getBorderRadiusValue"
					:setVariantValue="setVariantValue"
					@focus="openFromFocus(open)"
					@update:modelValue="setBorderRadius">
					<template #prefix="{ variant }">
						<button
							type="button"
							class="absolute left-2 top-[6px] size-4 cursor-pointer rounded border bg-surface-gray-4"
							@click="openPopover(open, variant)" />
					</template>
				</StylePropertyControl>
			</div>
			</div>
		</template>
		<template #default>
			<div
				class="radius-popover-body w-64 select-none rounded-lg border border-outline-gray-1 bg-surface-base p-3 shadow-xl">
				<div
					class="mb-4 flex h-28 items-center justify-center overflow-hidden rounded-md border border-outline-gray-1"
					style="
						background-image: conic-gradient(
							var(--surface-gray-1) 90deg,
							var(--surface-gray-2) 90deg 180deg,
							var(--surface-gray-1) 180deg 270deg,
							var(--surface-gray-2) 270deg
						);
						background-size: 16px 16px;
					">
					<div
						class="border bg-white transition-[border-radius] duration-200"
						:style="{ ...previewDimensions, borderRadius: scaledPreviewRadius }" />
				</div>

				<div class="mb-2 flex items-center justify-between">
					<span class="text-[10px] font-bold uppercase tracking-wider text-ink-gray-4">Corners</span>
					<Tooltip :text="cornersLinked ? 'Unlink corners' : 'Link corners'">
						<Button
							:icon="cornersLinked ? 'lucide-link' : 'lucide-unlink'"
							variant="ghost"
							size="sm"
							class="!size-6"
							@click="cornersLinked = !cornersLinked" />
					</Tooltip>
				</div>
				<div class="grid grid-cols-2 gap-2">
					<Tooltip v-for="corner in CORNERS" :key="corner.index" :text="corner.label">
						<StylePropertyControl
							propertyKey="borderRadius"
							:unitOptions="['px', '%']"
							:hideClearButton="true"
							:enableStates="false"
							:min="0"
							:getModelValue="() => cornerValues[corner.index]"
							:setModelValue="(value) => updateCorner(corner.index, value)">
							<template #prefix>
								<span :class="corner.icon" class="size-3 text-ink-gray-4" />
							</template>
						</StylePropertyControl>
					</Tooltip>
				</div>
			</div>
		</template>
	</Popover>
</template>

<script lang="ts" setup>
import Input from "@/components/Controls/Input.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { Button, Popover, Tooltip } from "frappe-ui";
import { computed, ref } from "vue";

const CORNERS = [
	{ index: 0, label: "Top Left", icon: "lucide-corner-up-right" },
	{ index: 1, label: "Top Right", icon: "lucide-corner-up-left" },
	{ index: 3, label: "Bottom Left", icon: "lucide-corner-down-right" },
	{ index: 2, label: "Bottom Right", icon: "lucide-corner-down-left" },
] as const;

const activeState = ref<string | null>(null);
const cornersLinked = ref(true);
const cornerValues = ref(["0px", "0px", "0px", "0px"]);
const popoverOpen = ref(false);
const previewDimensions = ref({ width: "64px", height: "64px" });
const previewScale = ref(1);

const getStyleKey = (state: string | null = activeState.value) =>
	state ? `${state}:borderRadius` : "borderRadius";

const getBorderRadiusValue = (state: string | null) =>
	(blockController.getStyle(getStyleKey(state)) || "") as string;

const expandRadius = (value: string): string[] => {
	const values = value.trim().split(/\s+/).filter(Boolean);
	if (!values.length) return ["0px", "0px", "0px", "0px"];
	if (values.length === 1) return Array(4).fill(values[0]);
	if (values.length === 2) return [values[0], values[1], values[0], values[1]];
	if (values.length === 3) return [values[0], values[1], values[2], values[1]];
	return values.slice(0, 4);
};

const previewRadius = computed(() => cornerValues.value.join(" "));

// converts every pixel radius into its scaled preview equivalent
const scaledPreviewRadius = computed(() =>
	previewRadius.value.replace(/(-?\d*\.?\d+)px\b/g, (_, value) => `${Number(value) * previewScale.value}px`),
);

const syncPreviewDimensions = () => {
	const block = blockController.getFirstSelectedBlock();
	const element = block
		? document.querySelector<HTMLElement>(`[data-block-id="${block.blockId}"][data-block-uid]`)
		: null;
	const width = element?.offsetWidth || parseFloat(String(block?.getStyle("width"))) || 64;
	const height = element?.offsetHeight || parseFloat(String(block?.getStyle("height"))) || 64;
	const scale = Math.min(160 / width, 80 / height);
	previewScale.value = scale;
	previewDimensions.value = {
		width: `${Math.max(1, width * scale)}px`,
		height: `${Math.max(1, height * scale)}px`,
	};
};

const syncCornerValues = (value = getBorderRadiusValue(activeState.value)) => {
	cornerValues.value = expandRadius(value);
	cornersLinked.value = new Set(cornerValues.value).size === 1;
	syncPreviewDimensions();
};

const updateActiveState = (event: FocusEvent) => {
	if (popoverOpen.value) return;
	selectActiveState(event);
};

const selectActiveState = (event: Event) => {
	const variantRow = (event.target as HTMLElement).closest("[data-variant]:not(input)");
	activeState.value = variantRow?.getAttribute("data-variant") || null;
	syncCornerValues();
};

const openPopover = (open: () => void, variant: string | null) => {
	activeState.value = variant;
	syncCornerValues();
	if (!popoverOpen.value) open();
};

const openFromFocus = (open: () => void) => {
	if (popoverOpen.value) return;
	syncCornerValues();
	open();
};

const ensureRoundedContentIsClipped = () => {
	if (!blockController.getStyle("overflowX")) blockController.setStyle("overflowX", "hidden");
	if (!blockController.getStyle("overflowY")) blockController.setStyle("overflowY", "hidden");
};

const setBorderRadius = (value: string | number | boolean | null) => {
	blockController.setStyle(getStyleKey(), value);
	cornerValues.value = expandRadius(String(value || ""));
	if (value) ensureRoundedContentIsClipped();
};

const updateCorner = (index: number, value: string | number | boolean | null) => {
	const nextValue = String(value || "0px");
	const values = [...cornerValues.value];
	if (cornersLinked.value) values.fill(nextValue);
	else values[index] = nextValue;
	setBorderRadius(values.join(" "));
};

const setVariantValue = (variant: string, value: string | number | boolean | null) => {
	activeState.value = variant;
	setBorderRadius(value);
};
</script>
