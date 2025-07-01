<template>
	<div class="flex w-full flex-col gap-2">
		<div class="flex w-full items-center gap-2">
			<div class="flex w-[80px] shrink-0 items-center">
				<Dropdown v-if="enableStates" size="sm" :options="stateOptions">
					<template v-slot="{ open }">
						<FeatherIcon
							name="plus-circle"
							class="mr-2 h-3 w-3 cursor-pointer text-ink-gray-7 hover:text-ink-gray-9"
							@click="open" />
					</template>
				</Dropdown>
				<InputLabel
					class="truncate"
					:class="{ 'cursor-ns-resize': enableSlider }"
					v-if="label"
					@mousedown="handleMouseDown">
					{{ label }}
				</InputLabel>
			</div>
			<component
				:is="props.component"
				v-bind="controlAttrs"
				v-on="props.events || {}"
				:modelValue="modelValue"
				:defaultValue="defaultValue"
				:placeholder="placeholderValue"
				@update:modelValue="updateValue"
				@keydown.stop="handleKeyDown"
				class="w-full" />
		</div>
		<template v-if="enableStates" v-for="state in statesToShow" :key="String(state)">
			<div
				class="group ml-[5px] flex items-center justify-between before:-mt-7 before:h-7 before:w-[1px] before:bg-surface-gray-4 before:content-['_'] after:absolute after:left-3.5 after:h-1.5 after:w-1.5 after:rounded-full after:bg-surface-gray-4 hover:after:hidden">
				<button
					type="button"
					class="absolute left-[11px] z-10 hidden text-ink-gray-7 hover:text-ink-gray-9 group-hover:block"
					@click="clearState(state)">
					<FeatherIcon name="x" class="h-3 w-3" />
				</button>
				<InputLabel class="ml-3 w-[80px] shrink-0">{{ stateLabels[String(state)] }}</InputLabel>
				<component
					:is="props.component"
					v-bind="controlAttrs"
					v-on="props.events || {}"
					:modelValue="getStateValue(state)"
					:defaultValue="defaultValue"
					:placeholder="placeholderValue"
					@update:modelValue="(v: any) => updateStateValue(state, v)"
					@keydown.stop="(e: KeyboardEvent) => handleKeyDown(e, state)"
					class="shrink-1 w-auto" />
			</div>
		</template>
	</div>
</template>
<script lang="ts" setup>
import Input from "@/components/Controls/Input.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import blockController from "@/utils/blockController";
import { Dropdown, FeatherIcon } from "frappe-ui";
import type { Component } from "vue";
import { computed, useAttrs } from "vue";

const props = withDefaults(
	defineProps<{
		styleProperty: string;
		label?: string;
		placeholder?: string;
		getModelValue?: () => string;
		getPlaceholder?: () => string;
		setModelValue?: (value: string) => void;
		enableSlider?: boolean;
		unitOptions?: string[];
		changeFactor?: number;
		minValue?: number;
		maxValue?: number | null;
		hideClearButton?: boolean;
		component?: Component;
		events?: Record<string, unknown>;
		defaultValue?: string | number;
		enableStates?: boolean;
		enabledStates?: string[];
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
		component: Input,
		enableStates: true,
		enabledStates: () => ["hover", "active", "focus"],
	},
);

const stateLabels: Record<string, string> = {
	hover: "On Hover",
	active: "On Active",
	focus: "On Focus",
};

const controlAttrs = computed(() => {
	const attrs = useAttrs();
	const propKeys = Object.keys(props);
	propKeys.push("style");
	return Object.fromEntries(Object.entries(attrs).filter(([key]) => !propKeys.includes(key)));
});

const defaultValue = computed(() => {
	return blockController.getCascadingStyle(props.styleProperty) ?? props.defaultValue;
});

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

const getStateValue = (state: string) => {
	return blockController.getNativeStyle(`${state}:${props.styleProperty}`);
};

const updateStateValue = (
	state: string,
	value: string | number | null | { label: string; value: string },
) => {
	if (typeof value === "object" && value !== null && "value" in value) {
		value = value.value;
	}
	if (value && typeof value === "string") {
		let [_, number, unit] = value.match(/([0-9]+)([a-z%]*)/) || ["", "", ""];
		if (!unit && props.unitOptions.length && number) {
			value = number + props.unitOptions[0];
		}
	}
	blockController.setStyle(`${state}:${props.styleProperty}`, value as string);
};

const clearState = (state: string) => {
	blockController.setStyle(`${state}:${props.styleProperty}`, undefined);
};

const stateOptions = computed(() =>
	props.enabledStates
		.filter((state: string) => !getStateValue(state))
		.map((state: string) => ({
			label: stateLabels[state] || state,
			onClick: () => {
				blockController.setStyle(`${state}:${props.styleProperty}`, modelValue.value);
			},
		})),
);

const statesToShow = computed(() => {
	if (!props.enableStates) return [];
	return props.enabledStates.filter((state: string) => {
		return blockController.getNativeStyle(`${state}:${props.styleProperty}`) !== undefined;
	});
});

const handleKeyDown = (e: KeyboardEvent, state?: string) => {
	if (!props.enableSlider) return;
	if (e.key === "ArrowUp" || e.key === "ArrowDown") {
		const step = e.key === "ArrowUp" ? 1 : -1;
		if (state) {
			incrementOrDecrementState(state, step);
		} else {
			incrementOrDecrement(step);
		}
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

const incrementOrDecrementState = (state: string, step: number, initialValue: null | number = null) => {
	const value = getStateValue(state) + "" || "";
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
	updateStateValue(state, newValue + "" + unit);
};
</script>
