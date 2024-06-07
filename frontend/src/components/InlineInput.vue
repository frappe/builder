<template>
	<div class="relative flex items-center justify-between [&>div>input]:!bg-red-600 [&>div>input]:pr-6">
		<InputLabel
			:class="{
				'cursor-ns-resize': enableSlider,
			}"
			@mousedown="handleMouseDown">
			{{ label }}
		</InputLabel>
		<Input
			:type="type"
			placeholder="unset"
			:modelValue="modelValue"
			:options="inputOptions"
			v-if="type != 'autocomplete'"
			@mousedown="handleMouseDown"
			@update:modelValue="handleChange"
			@keydown="handleKeyDown" />
		<Autocomplete
			v-if="type == 'autocomplete'"
			placeholder="unset"
			:modelValue="modelValue"
			:options="inputOptions"
			@update:modelValue="handleChange"
			class="w-[140px] [&>div>select]:text-sm [&>div>select]:text-gray-800 [&>div>select]:dark:border-zinc-700 [&>div>select]:dark:bg-zinc-800 [&>div>select]:dark:text-zinc-200 [&>div>select]:dark:focus:bg-zinc-700" />
		<div
			class="absolute right-1 top-[3px] cursor-pointer p-1 text-gray-700 dark:text-zinc-300"
			@click="clearValue"
			v-if="!['autocomplete', 'select', 'checkbox'].includes(type)"
			v-show="modelValue">
			<CrossIcon />
		</div>
	</div>
</template>
<script setup lang="ts">
import { isNumber } from "@tiptap/vue-3";
import { PropType, computed } from "vue";
import Autocomplete from "./Autocomplete.vue";
import CrossIcon from "./Icons/Cross.vue";
import Input from "./Input.vue";
import InputLabel from "./InputLabel.vue";

const props = defineProps({
	modelValue: {
		type: [String, Number],
		default: null,
	},
	label: {
		type: String,
		default: "",
	},
	type: {
		type: String,
		default: "text",
	},
	unitOptions: {
		type: Array as PropType<string[]>,
		default: () => [],
	},
	options: {
		type: Array,
		default: () => [],
	},
	enableSlider: {
		type: Boolean,
		default: false,
	},
	minValue: {
		type: Number,
		default: 0,
	},
	maxValue: {
		type: Number,
		default: null,
	},
});

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
	const number = ((props.modelValue || "") as string).match(/([0-9]+)/)?.[0] || "0";
	const startY = e.clientY;
	const startValue = Number(number);
	const handleMouseMove = (e: MouseEvent) => {
		const diff = startY - e.clientY;
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
	const value = (props.modelValue as string) || "";
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

const clearValue = () => emit("update:modelValue", null);
</script>
