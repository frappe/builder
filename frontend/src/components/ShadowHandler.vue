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
				class="shadow-popover-body max-h-[80vh] w-72 select-none space-y-2 overflow-y-auto rounded-lg border border-outline-gray-1 bg-surface-white p-3 shadow-xl">
				<InlineInput
					label="Preset"
					type="select"
					:modelValue="currentPreset"
					:options="presetOptions"
					@update:modelValue="applyPreset" />

				<div class="bg-outline-gray-2 my-2 h-px w-full" />

				<div
					v-for="(shadow, index) in shadowConfigs"
					:key="index"
					class="mb-3 space-y-2 border-b border-outline-gray-2 pb-3 last:mb-0 last:border-b-0 last:pb-0">
					<div class="flex items-center justify-between">
						<span class="text-xs font-medium text-ink-gray-5">Layer {{ index + 1 }}</span>
						<Button
							icon="trash-2"
							variant="ghost"
							class="!h-6 !w-6 !p-1 text-ink-gray-5 hover:text-ink-red-3"
							@click="removeShadow(index)"></Button>
					</div>

					<InlineInput
						label="X Offset"
						:modelValue="shadow.x"
						:unitOptions="['px']"
						:enableSlider="true"
						@update:modelValue="(val: any) => updateShadow(index, 'x', val)" />
					<InlineInput
						label="Y Offset"
						:modelValue="shadow.y"
						:unitOptions="['px']"
						:enableSlider="true"
						@update:modelValue="(val: any) => updateShadow(index, 'y', val)" />
					<InlineInput
						label="Blur"
						:modelValue="shadow.blur"
						:unitOptions="['px']"
						:minValue="0"
						:enableSlider="true"
						@update:modelValue="(val: any) => updateShadow(index, 'blur', val)" />
					<InlineInput
						label="Spread"
						:modelValue="shadow.spread"
						:unitOptions="['px']"
						:enableSlider="true"
						@update:modelValue="(val: any) => updateShadow(index, 'spread', val)" />

					<ColorInput
						label="Color"
						:modelValue="shadow.color"
						@update:modelValue="(val: any) => updateShadow(index, 'color', val)" />

					<div class="flex items-center justify-between">
						<InputLabel>Type</InputLabel>
						<OptionToggle
							class="[&>div]:min-w-[auto]"
							:modelValue="shadow.inset"
							:options="[
								{ label: 'Inset', value: true },
								{ label: 'Outset', value: false },
							]"
							@update:modelValue="(val: any) => updateShadow(index, 'inset', val)" />
					</div>
				</div>

				<div v-if="shadowConfigs.length > 0" class="bg-outline-gray-2 my-2 h-px w-full" />

				<Button class="w-full" variant="ghost" @click="addShadow">+ Add Shadow Layer</Button>
			</div>
		</template>
	</Popover>
</template>

<script lang="ts" setup>
import ColorInput from "@/components/Controls/ColorInput.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import Input from "@/components/Controls/Input.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { Button, Popover } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";

const activeState = ref<string | null>(null);

const updateActiveState = (e: FocusEvent) => {
	const target = e.target as HTMLElement;

	if (target.closest(".shadow-popover-body")) return;

	const variantRow = target.closest("[data-variant]");
	const mainPropRow = target.closest("[data-property]");

	if (variantRow) {
		activeState.value = variantRow.getAttribute("data-variant") as string;
	} else if (mainPropRow) {
		activeState.value = null;
	}
};

const getStyleKey = (prop: string, state: string | null = activeState.value) => {
	return state ? `${state}:${prop}` : prop;
};

const boxShadow = computed(() => blockController.getStyle(getStyleKey("boxShadow")) as string);

const getBoxShadowValue = (state: string | null) => {
	return (blockController.getStyle(getStyleKey("boxShadow", state)) || "") as string;
};

const presetOptions = [
	{ label: "None", value: "none" },
	{
		label: "Small",
		value: "rgba(0, 0, 0, 0.05) 0px 1px 2px 0px, rgba(0, 0, 0, 0.05) 0px 1px 3px 0px",
	},
	{
		label: "Medium",
		value: "rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.1) 0px 4px 6px -4px",
	},
	{
		label: "Large",
		value: "rgba(0, 0, 0, 0.1) 0px 20px 25px -5px, rgba(0, 0, 0, 0.1) 0px 10px 10px -5px",
	},
	{ label: "Custom", value: "custom" },
];

const currentPreset = computed(() => {
	const val = boxShadow.value;
	if (!val || val === "none") return "none";
	const match = presetOptions.find((p) => p.value === val);
	return match ? match.value : "custom";
});

const applyPreset = (val: string) => {
	if (val === "custom") return;
	if (val === "none") {
		clearShadow();
	} else {
		setBoxShadow(val);
	}
};

interface ShadowConfig {
	x: string;
	y: string;
	blur: string;
	spread: string;
	color: any;
	inset: boolean;
}

const shadowConfigs = reactive<ShadowConfig[]>([]);

// Split shadows by comma but ignore commas inside parentheses (like in rgba)
const splitShadows = (value: string): string[] => {
	if (!value || value === "none") return [];
	const result: string[] = [];
	let current = "";
	let inParens = 0;

	for (let i = 0; i < value.length; i++) {
		const char = value[i];
		if (char === "(") inParens++;
		if (char === ")") inParens--;
		if (char === "," && inParens === 0) {
			result.push(current.trim());
			current = "";
		} else {
			current += char;
		}
	}
	if (current.trim()) result.push(current.trim());

	return result;
};

// Parser for multiple box-shadows
const parseBoxShadows = (value: string): ShadowConfig[] => {
	if (!value || value === "none") return [];

	const shadows = splitShadows(value);
	return shadows.map((shadow) => {
		const config: ShadowConfig = {
			x: "0px",
			y: "0px",
			blur: "0px",
			spread: "0px",
			color: "rgba(0,0,0,0.5)",
			inset: false,
		};

		config.inset = shadow.includes("inset");
		let cleaned = shadow.replace("inset", "").trim();

		const parts = cleaned.split(/\s+(?![^(]*\))/);

		// Find the color part (simplification: part that is not a numeric value with unit)
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

watch(
	boxShadow,
	(newVal) => {
		if (newVal) {
			const parsed = parseBoxShadows(newVal);
			shadowConfigs.splice(0, shadowConfigs.length, ...parsed);
		} else {
			shadowConfigs.splice(0, shadowConfigs.length);
		}
	},
	{ immediate: true },
);

const updateShadow = <K extends keyof ShadowConfig>(index: number, key: K, value: ShadowConfig[K]) => {
	shadowConfigs[index][key] = value;
	applyShadow();
};

const addShadow = () => {
	shadowConfigs.push({
		x: "0px",
		y: "4px",
		blur: "6px",
		spread: "-1px",
		color: "rgba(0, 0, 0, 0.1)",
		inset: false,
	});
	applyShadow();
};

const removeShadow = (index: number) => {
	shadowConfigs.splice(index, 1);
	applyShadow();
};

const applyShadow = () => {
	if (shadowConfigs.length === 0) {
		clearShadow();
		return;
	}
	const shadowStr = shadowConfigs
		.map((conf) => {
			const { x, y, blur, spread, color, inset } = conf;
			return `${inset ? "inset " : ""}${x} ${y} ${blur} ${spread} ${color}`.trim();
		})
		.join(", ");
	blockController.setStyle(getStyleKey("boxShadow"), shadowStr);
};

const setBoxShadow = (val: string) => {
	blockController.setStyle(getStyleKey("boxShadow"), val);
};

const clearShadow = () => {
	blockController.setStyle(getStyleKey("boxShadow"), null);
};

const handleSetVariant = (variantName: string, value: string | number | boolean | null) => {
	const shadowKey = `${variantName}:boxShadow`;

	if (value === null) {
		blockController.setStyle(shadowKey, null);
	} else {
		blockController.getSelectedBlocks().forEach((block) => {
			if (!block.getStyle("transitionDuration")) {
				block.setStyle("transitionDuration", "300ms");
				block.setStyle("transitionTimingFunction", "ease");
				block.setStyle("transitionProperty", "all");
			}
		});
		blockController.setStyle(shadowKey, value as string);
	}
};
</script>
