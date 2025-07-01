<template>
	<div class="flex w-full items-center gap-2 overflow-hidden">
		<InputLabel
			class="w-[80px] shrink-0 truncate"
			:class="{ 'cursor-ns-resize': enableSlider }"
			v-if="label"
			@mousedown="handleMouseDown">
			{{ label }}
		</InputLabel>
		<BuilderInput
			:type="type"
			:modelValue="modelValue"
			:placeholder="placeholderValue"
			@update:modelValue="updateValue"
			:options="options"
			:unitOptions="unitOptions"
			:hideClearButton="hideClearButton"
			@keydown.stop="handleKeyDown"
			class="w-full" />
	</div>
</template>
<script lang="ts" setup>
import InputLabel from "@/components/Controls/InputLabel.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

const props = withDefaults(
	defineProps<{
		styleProperty: string;
		label: string;
		type?: string;
		placeholder?: string;
		options?: Record<string, string> | Array<{ label: string; value: string }>;
		getModelValue?: () => string;
		getPlaceholder?: () => string;
		setModelValue?: (value: string) => void;
		enableSlider?: boolean;
		unitOptions?: string[];
		changeFactor?: number;
		minValue?: number;
		maxValue?: number | null;
		hideClearButton?: boolean;
	}>(),
	{
		placeholder: "unset",
		type: "text",
		enableSlider: false,
		unitOptions: () => [],
		changeFactor: 1,
		minValue: 0,
		maxValue: null,
		hideClearButton: false,
	},
);

const modelValue = computed(
	() => props.getModelValue?.() ?? blockController.getNativeStyle(props.styleProperty) ?? "",
);

const placeholderValue = computed(
	() =>
		props.getPlaceholder?.() ??
		String(blockController.getCascadingStyle(props.styleProperty) ?? props.placeholder),
);

const updateValue = (value: string | number | null | { label: string; value: string }) => {
	if (typeof value === "object" && value !== null && "value" in value) {
		value = value.value;
	}
	if (value && typeof value === "string") {
		let [_, number, unit] = value.match(/([0-9]+)([a-z%]*)/) || ["", "", ""];
		if (!unit && props.unitOptions.length && number) {
			value = number + props.unitOptions[0];
		}
	}
	if (props.setModelValue) {
		props.setModelValue(value as string);
	} else {
		blockController.setStyle(props.styleProperty, value as string);
	}
};

const handleMouseDown = (e: MouseEvent) => {
	if (!props.enableSlider) return;
	const number = ((modelValue.value + "" || "") as string).match(/([0-9]+)/)?.[0] || "0";
	const startY = e.clientY;
	const startValue = Number(number);
	const handleMouseMove = (e: MouseEvent) => {
		let diff = (startY - e.clientY) * props.changeFactor;
		diff = Math.round(diff);
		incrementOrDecrement(diff, startValue);
	};
	const handleMouseUp = () => {
		window.removeEventListener("mousemove", handleMouseMove);
	};
	window.addEventListener("mousemove", handleMouseMove);
	window.addEventListener("mouseup", handleMouseUp, { once: true });
};

const handleKeyDown = (e: KeyboardEvent) => {
	if (!props.enableSlider) return;
	if (e.key === "ArrowUp" || e.key === "ArrowDown") {
		const step = e.key === "ArrowUp" ? 1 : -1;
		incrementOrDecrement(step);
		e.preventDefault();
	}
};

const incrementOrDecrement = (step: number, initialValue: null | number = null) => {
	const value = modelValue.value + "" || "";
	let [_, number, unit] = value.match(/([0-9]+)([a-z%]*)/) || ["", "", ""];
	if (!unit && props.unitOptions.length && !isNaN(Number(number))) {
		unit = props.unitOptions[0];
	}
	let newValue = (initialValue != null ? Number(initialValue) : Number(number)) + step;
	if (typeof props.minValue === "number" && newValue <= props.minValue) {
		newValue = props.minValue;
	}
	if (typeof props.maxValue === "number" && props.maxValue !== null && newValue >= props.maxValue) {
		newValue = props.maxValue;
	}
	updateValue(newValue + "" + unit);
};
</script>
