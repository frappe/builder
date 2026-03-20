<template>
	<Popover placement="left" class="!block w-full" :offset="25">
		<template #target="{ togglePopover }">
			<div class="flex w-full items-center justify-between" @focusin="updateActiveState">
				<StylePropertyControl
					propertyKey="boxShadow"
					:component="Input"
					label="Shadow"
					:enableStates="true"
					:allowDynamicValue="true"
					placeholder="None"
					@focus="togglePopover"
					:getModelValue="() => getBoxShadowValue(null)"
					:getVariantValue="(v: string) => getBoxShadowValue(v)"
					:setVariantValue="handleSetVariant"
					@update:modelValue="setBoxShadow">
					<template #prefix="{ variant }">
						<div
							class="absolute left-2 top-[6px] size-4 cursor-pointer rounded border border-outline-gray-1 shadow-sm"
							@click="
								() => {
									activeState = variant;
									togglePopover();
								}
							"
							:style="{
								backgroundColor: shadowConfigs[0]?.color ?? 'transparent',
							}" />
					</template>
				</StylePropertyControl>
			</div>
		</template>
		<template #body>
			<div
				class="shadow-popover-body max-h-[80vh] w-64 select-none overflow-y-auto rounded-lg border border-outline-gray-1 bg-surface-white p-3 shadow-xl">
				<div class="mb-3 space-y-3">
					<div
						class="flex h-24 w-full items-center justify-center rounded-md border border-outline-gray-1 bg-surface-white"
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
							class="size-10 rounded bg-white shadow-sm transition-shadow duration-200"
							:style="{ boxShadow: currentPreviewShadow }" />
					</div>
					<Input
						type="select"
						:modelValue="currentPreset"
						:options="presetOptions"
						@update:modelValue="applyPreset"
						placeholder="Presets" />
				</div>

				<div class="space-y-4">
					<div v-for="(shadow, index) in shadowConfigs" :key="index" class="space-y-2 rounded-md">
						<div class="flex items-center justify-between">
							<span class="text-[10px] font-bold uppercase tracking-wider text-ink-gray-4">
								Layer {{ index + 1 }}
							</span>
							<Button
								icon="x"
								variant="ghost"
								size="sm"
								class="!size-5 !text-ink-gray-4"
								@click="removeShadow(index)" />
						</div>
						<div class="flex gap-2">
							<div
								class="relative flex aspect-square w-[64px] cursor-crosshair items-center justify-center overflow-hidden rounded border border-outline-gray-2 bg-surface-white p-1"
								style="
									background-image: conic-gradient(
										var(--surface-gray-1) 90deg,
										var(--surface-gray-2) 90deg 180deg,
										var(--surface-gray-1) 180deg 270deg,
										var(--surface-gray-2) 270deg
									);
									background-size: 8px 8px;
								"
								@mousedown="handleVisualPickerMouseDown($event, index)">
								<div
									class="bg-outline-gray-2 pointer-events-none absolute inset-x-0 top-1/2 h-px opacity-50" />
								<div
									class="bg-outline-gray-2 pointer-events-none absolute inset-y-0 left-1/2 w-px opacity-50" />
								<div
									class="pointer-events-none absolute size-4 -translate-x-1/2 -translate-y-1/2 rounded-sm border border-outline-gray-1 bg-white shadow transition-shadow"
									:style="{
										left: getPickerPos(shadow.x),
										top: getPickerPos(shadow.y),
										boxShadow: formatShadow(shadow),
									}" />
							</div>
							<div class="grid flex-1 grid-cols-2 gap-2">
								<Tooltip v-for="control in SHADOW_CONTROLS" :key="control.key" :text="control.label">
									<Input
										:modelValue="shadow[control.key]"
										:hideClearButton="true"
										@update:modelValue="(val: any) => updateShadow(index, control.key, val)"
										:placeholder="control.prefix">
										<template #prefix>
											<span class="w-3 text-[10px] font-medium text-ink-gray-4">{{ control.prefix }}</span>
										</template>
									</Input>
								</Tooltip>
							</div>
						</div>
						<div class="flex items-center gap-2">
							<Tooltip :text="shadow.inset ? 'Inset Shadow' : 'Outset Shadow'">
								<OptionToggle
									class="!w-auto [&>div]:!h-7 [&>div]:min-w-[40px]"
									:modelValue="shadow.inset"
									:options="[
										{ label: 'O', value: false },
										{ label: 'I', value: true },
									]"
									@update:modelValue="(val: any) => updateShadow(index, 'inset', val)" />
							</Tooltip>
							<div class="flex-1">
								<Tooltip text="Shadow Color">
									<ColorInput
										:modelValue="shadow.color"
										@update:modelValue="(val: any) => updateShadow(index, 'color', val)" />
								</Tooltip>
							</div>
						</div>
					</div>
				</div>
				<div class="mt-3">
					<Button class="w-full" variant="subtle" @click="addShadow">+ Add Shadow Layer</Button>
				</div>
			</div>
		</template>
	</Popover>
</template>

<script lang="ts" setup>
import ColorInput from "@/components/Controls/ColorInput.vue";
import Input from "@/components/Controls/Input.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { Button, Popover, Tooltip } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";

const SHADOW_CONTROLS = [
	{ key: "x", label: "X Offset", prefix: "X" },
	{ key: "y", label: "Y Offset", prefix: "Y" },
	{ key: "blur", label: "Blur", prefix: "B" },
	{ key: "spread", label: "Spread", prefix: "S" },
] as const;

const activeState = ref<string | null>(null);

const updateActiveState = (e: FocusEvent) => {
	const target = e.target as HTMLElement;
	if (target.closest(".shadow-popover-body")) return;
	const variantRow = target.closest("[data-variant]");
	activeState.value = variantRow ? (variantRow.getAttribute("data-variant") as string) : null;
};

const getStyleKey = (prop: string, state: string | null = activeState.value) =>
	state ? `${state}:${prop}` : prop;
const boxShadow = computed(() => blockController.getStyle(getStyleKey("boxShadow")) as string);

const formatShadow = (conf: ShadowConfig) => {
	const { x, y, blur, spread, color, inset } = conf;
	return `${inset ? "inset " : ""}${x} ${y} ${blur} ${spread} ${color}`.trim();
};

const currentPreviewShadow = computed(() => shadowConfigs.map(formatShadow).join(", "));
const getBoxShadowValue = (state: string | null) =>
	(blockController.getStyle(getStyleKey("boxShadow", state)) || "") as string;

const presetOptions = [
	{ label: "None", value: "none" },
	{ label: "Small", value: "#0000000d 0px 1px 2px 0px, #0000000d 0px 1px 3px 0px" },
	{ label: "Medium", value: "#0000001a 0px 10px 15px -3px, #0000001a 0px 4px 6px -4px" },
	{ label: "Large", value: "#0000001a 0px 20px 25px -5px, #0000001a 0px 10px 10px -5px" },
	{ label: "Custom", value: "custom" },
];

const currentPreset = computed(() => {
	const val = boxShadow.value;
	if (!val || val === "none") return "none";
	return presetOptions.find((p) => p.value === val)?.value || "custom";
});

const applyPreset = (val: string) => (val === "none" ? clearShadow() : val !== "custom" && setBoxShadow(val));

interface ShadowConfig {
	x: string;
	y: string;
	blur: string;
	spread: string;
	color: any;
	inset: boolean;
}

const shadowConfigs = reactive<ShadowConfig[]>([]);

const parseBoxShadows = (value: string): ShadowConfig[] => {
	if (!value || value === "none") return [];
	const shadows: string[] = [];
	let current = "",
		inParens = 0;
	for (const char of value) {
		if (char === "(") inParens++;
		if (char === ")") inParens--;
		if (char === "," && inParens === 0) {
			shadows.push(current.trim());
			current = "";
		} else current += char;
	}
	if (current.trim()) shadows.push(current.trim());

	return shadows.map((shadow) => {
		const config: ShadowConfig = {
			x: "0px",
			y: "0px",
			blur: "0px",
			spread: "0px",
			color: "#00000080",
			inset: shadow.includes("inset"),
		};
		let cleaned = shadow.replace("inset", "").trim();
		const parts = cleaned.split(/\s+(?![^(]*\))/);
		const colorPart = parts.find(
			(p) => !/^[-+]?\d*\.?\d+(px|em|rem|%|vh|vw|pt|pc|in|cm|mm|ex|ch|vmin|vmax)$/.test(p) && p !== "0",
		);
		if (colorPart) {
			config.color = colorPart;
			cleaned = cleaned.replace(colorPart, "").trim();
		}
		const numericParts = cleaned.split(/\s+/).filter(Boolean);
		config.x = numericParts[0] || "0px";
		config.y = numericParts[1] || "0px";
		config.blur = numericParts[2] || "0px";
		config.spread = numericParts[3] || "0px";
		return config;
	});
};

watch(boxShadow, (val) => shadowConfigs.splice(0, shadowConfigs.length, ...parseBoxShadows(val || "")), {
	immediate: true,
});

const updateShadow = <K extends keyof ShadowConfig>(index: number, key: K, value: ShadowConfig[K]) => {
	shadowConfigs[index][key] = value;
	applyShadow();
};

const addShadow = () => {
	shadowConfigs.push({ x: "0px", y: "4px", blur: "6px", spread: "-1px", color: "#0000001a", inset: false });
	applyShadow();
};

const removeShadow = (index: number) => {
	shadowConfigs.splice(index, 1);
	applyShadow();
};

const getPickerPos = (val: string) =>
	`${Math.min(Math.max((((parseFloat(val) || 0) + 20) / 40) * 100, 0), 100)}%`;

const handleVisualPickerMouseDown = (e: MouseEvent, index: number) => {
	const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
	const update = (moveEvent: MouseEvent) => {
		const valX = Math.round(((moveEvent.clientX - rect.left) / rect.width) * 40 - 20);
		const valY = Math.round(((moveEvent.clientY - rect.top) / rect.height) * 40 - 20);
		updateShadow(index, "x", `${valX}px`);
		updateShadow(index, "y", `${valY}px`);
	};
	update(e);
	const move = (me: MouseEvent) => update(me);
	const stop = () => {
		window.removeEventListener("mousemove", move);
		window.removeEventListener("mouseup", stop);
	};
	window.addEventListener("mousemove", move);
	window.addEventListener("mouseup", stop);
};

const applyShadow = () =>
	blockController.setStyle(
		getStyleKey("boxShadow"),
		shadowConfigs.length ? shadowConfigs.map(formatShadow).join(", ") : null,
	);
const setBoxShadow = (val: string) => blockController.setStyle(getStyleKey("boxShadow"), val);
const clearShadow = () => blockController.setStyle(getStyleKey("boxShadow"), null);

const handleSetVariant = (variant: string, value: string | number | boolean | null) => {
	const key = `${variant}:boxShadow`;
	if (value === null) blockController.setStyle(key, null);
	else {
		blockController.getSelectedBlocks().forEach((b) => {
			if (!b.getStyle("transitionDuration")) {
				b.setStyle("transitionDuration", "300ms");
				b.setStyle("transitionTimingFunction", "ease");
				b.setStyle("transitionProperty", "all");
			}
		});
		blockController.setStyle(key, value as string);
	}
};
</script>
