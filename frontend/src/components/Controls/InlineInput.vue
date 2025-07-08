<template>
	<div class="flex items-center justify-between [&>div>input]:!bg-red-600 [&>div>input]:pr-6">
		<InputLabel
			v-if="label"
			:class="{
				'cursor-ns-resize': enableSlider,
			}"
			class="w-[88px] shrink-0"
			:description="description"
			@mousedown="handleMouseDown">
			{{ label }}
		</InputLabel>
		<BuilderInput
			class="w-full"
			:type="type"
			:placeholder="placeholder"
			:modelValue="modelValue"
			:options="inputOptions"
			v-if="type != 'autocomplete'"
			@update:modelValue="handleChange"
			:hideClearButton="hideClearButton"
			@keydown.stop="handleKeyDown" />
		<Autocomplete
			v-if="type == 'autocomplete'"
			:placeholder="placeholder"
			:modelValue="modelValue"
			:options="inputOptions"
			:getOptions="getOptions"
			@update:modelValue="handleChange"
			:actionButton="actionButton"
			:showInputAsOption="showInputAsOption"
			:hideClearButton="hideClearButton"
			class="w-full" />
	</div>
</template>
<script setup lang="ts">
import { isNumber } from "@tiptap/vue-3";
import { computed } from "vue";
import Autocomplete from "./Autocomplete.vue";
import InputLabel from "./InputLabel.vue";

type Action = {
	label: String;
	handler: () => void;
	icon: string;
	component?: any;
};

const props = withDefaults(
	defineProps<{
		modelValue?: StyleValue;
		label?: string;
		description?: string;
		type?: string;
		unitOptions?: string[];
		options?: any[];
		enableSlider?: boolean;
		changeFactor?: number;
		minValue?: number;
		maxValue?: number | null;
		showInputAsOption?: boolean;
		getOptions?: (filterString: string) => Promise<Option[]>;
		actionButton?: Action;
		placeholder?: StyleValue;
		hideClearButton?: boolean;
	}>(),
	{
		label: "",
		description: "",
		type: "text",
		unitOptions: () => [],
		options: () => [],
		enableSlider: false,
		changeFactor: 1,
		minValue: 0,
		maxValue: null,
		showInputAsOption: false,
		placeholder: "unset",
		hideClearButton: false,
	},
);

const emit = defineEmits(["update:modelValue"]);

type Option = {
	label: string;
	value: string;
};

const inputOptions = computed(() => {
	return (props.options || []).map((option) => {
		if (typeof option === "string" || (typeof option === "number" && props.type === "autocomplete")) {
			return {
				label: option,
				value: option,
			};
		}
		return option;
	}) as Option[];
});

// TODO: Refactor
const handleChange = (value: string | number | null | { label: string; value: string }) => {
	if (typeof value === "object" && value !== null && "value" in value) {
		value = value.value;
	}
	if (value && typeof value === "string") {
		let [_, number, unit] = value.match(/([0-9]+)([a-z%]*)/) || ["", "", ""];
		if (!unit && props.unitOptions.length && number) {
			value = number + props.unitOptions[0];
		}
	}

	emit("update:modelValue", value);
};

const handleMouseDown = (e: MouseEvent) => {
	if (!props.enableSlider) {
		return;
	}
	const number = ((props.modelValue + "" || "") as string).match(/([0-9]+)/)?.[0] || "0";
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
	if (e.key === "ArrowUp" || e.key === "ArrowDown") {
		const step = e.key === "ArrowUp" ? 1 : -1;
		incrementOrDecrement(step);
		e.preventDefault();
	}
};

const incrementOrDecrement = (step: number, initialValue: null | number = null) => {
	const value = props.modelValue + "" || "";
	let [_, number, unit] = value.match(/([0-9]+)([a-z%]*)/) || ["", "", ""];
	if (!unit && props.unitOptions.length && !isNaN(Number(number))) {
		unit = props.unitOptions[0];
	}
	let newValue = (initialValue != null ? Number(initialValue) : Number(number)) + step;
	if (isNumber(props.minValue) && newValue <= props.minValue) {
		newValue = props.minValue;
	}
	if (isNumber(props.maxValue) && newValue >= props.maxValue) {
		newValue = props.maxValue;
	}
	handleChange(newValue + "" + unit);
};
</script>
