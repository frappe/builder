<template>
	<div class="flex w-full flex-col gap-2">
		<div class="relative flex w-full items-center gap-2">
			<div class="flex w-[88px] shrink-0 items-center" v-if="enableStateControls || label">
				<DraggablePopup
					v-model="showDynamicValueModal"
					:container="dropdownTrigger?.$el"
					placement="middle-right"
					:clickOutsideToClose="false"
					:placementOffset="20"
					v-if="showDynamicValueModal">
					<template #header>Set Dynamic Value</template>
					<template #content>
						<DynamicValueHandler @setDynamicValue="setDynamicValue" :selectedValue="dynamicValue" />
					</template>
				</DraggablePopup>
				<Dropdown v-if="enableStateControls || allowDynamicValue" size="sm" :options="stateOptions">
					<template v-slot="{ open }">
						<FeatherIcon
							ref="dropdownTrigger"
							name="plus-circle"
							class="mr-1.5 h-3 w-3 cursor-pointer text-ink-gray-7 hover:text-ink-gray-9"
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
			<div class="relative w-full">
				<component
					:is="props.component"
					v-bind="controlAttrs"
					v-on="props.events || {}"
					:modelValue="modelValue"
					:defaultValue="defaultValue"
					:placeholder="placeholderValue"
					@update:modelValue="updateValue"
					@keydown.stop="handleKeyDown"
					class="w-full">
					<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
						<slot :name="name" v-bind="slotData || {}" />
					</template>
				</component>

				<div
					class="absolute bottom-0 left-0 right-0 top-0 z-20 flex cursor-pointer items-center gap-2 rounded bg-surface-violet-1 py-0.5 pl-2.5 pr-6 text-sm text-ink-violet-1"
					@click.stop="showDynamicValueModal = true"
					v-if="dynamicValue">
					<FeatherIcon name="zap" class="size-3"></FeatherIcon>
					<span class="truncate">{{ dynamicValue }}</span>
				</div>
				<button
					class="absolute right-1 top-1 z-20 cursor-pointer p-1 text-ink-gray-4 hover:text-ink-gray-5"
					tabindex="-1"
					v-show="dynamicValue"
					@click="clearDynamicValue">
					<CrossIcon />
				</button>
			</div>
		</div>
		<template v-if="enableStateControls" v-for="state in statesToShow" :key="String(state)">
			<div
				class="group ml-[5px] flex items-center justify-between before:-mt-7 before:h-7 before:w-[1px] before:bg-surface-gray-4 before:content-['_'] after:absolute after:left-3.5 after:h-1.5 after:w-1.5 after:rounded-full after:bg-surface-gray-4 hover:after:hidden">
				<button
					type="button"
					class="absolute left-[11px] z-10 hidden text-ink-gray-7 hover:text-ink-gray-9 group-hover:block"
					@click="clearState(state)">
					<FeatherIcon name="x" class="h-3 w-3" />
				</button>
				<InputLabel
					class="ml-3 w-[80px] shrink-0"
					:class="{ 'cursor-ns-resize': enableSlider }"
					@mousedown="(ev: MouseEvent) => handleStateMouseDown(ev, state)">
					{{ stateLabels[String(state)] }}
				</InputLabel>
				<component
					:is="props.component"
					v-bind="controlAttrs"
					v-on="props.events || {}"
					:modelValue="getStateValue(state)"
					:defaultValue="defaultValue"
					:placeholder="placeholderValue"
					@focus="() => enableStyle(state)"
					@blur="() => disableStyle(state)"
					@update:modelValue="(v: any) => updateStateValue(state, v)"
					@keydown.stop="(e: KeyboardEvent) => handleKeyDown(e, state)"
					class="shrink-1 w-full">
					<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
						<slot :name="name" v-bind="slotData || {}" />
					</template>
				</component>
			</div>
		</template>
	</div>
</template>
<script lang="ts" setup>
import DynamicValueHandler from "@/components/Controls/DynamicValueHandler.vue";
import Input from "@/components/Controls/Input.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import CrossIcon from "@/components/Icons/Cross.vue";
import blockController from "@/utils/blockController";
import { Dropdown, FeatherIcon } from "frappe-ui";
import type { Component } from "vue";
import { computed, ref, useAttrs } from "vue";

const dropdownTrigger = ref<typeof FeatherIcon | null>(null);
const emit = defineEmits<{
	(setDynamicValue: string): void;
	(clearDynamicValue: void): void;
}>();

const props = withDefaults(
	defineProps<{
		styleProperty: string;
		label?: string;
		placeholder?: string;
		controlType?: "style" | "attribute" | "key";
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
		allowDynamicValue?: boolean;
		enabledStates?: string[];
	}>(),
	{
		placeholder: "unset",
		type: "text",
		controlType: "style",
		enableSlider: false,
		unitOptions: () => [],
		changeFactor: 1,
		minValue: 0,
		maxValue: null,
		hideClearButton: false,
		component: Input,
		allowDynamicValue: false,
		enabledStates: () => ["hover", "active", "focus"],
		enableStates: undefined,
	},
);

const enableStateControls = computed(() => {
	return props.enableStates ?? props.controlType === "style";
});

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
	blockController.setStyle(`${state}:${props.styleProperty}`, null);
};

const showDynamicValueModal = ref(false);

const stateOptions = computed(() => {
	const options = [];
	if (enableStateControls.value) {
		options.push(
			...props.enabledStates
				.filter((state: string) => !getStateValue(state))
				.map((state: string) => ({
					label: stateLabels[state] || state,
					onClick: () => {
						blockController.setStyle(`${state}:${props.styleProperty}`, modelValue.value);
					},
				})),
		);
	}

	if (props.allowDynamicValue) {
		options.unshift({
			label: "Set Dynamic Value",
			onClick: () => {
				showDynamicValueModal.value = true;
			},
		});
	}
	return options;
});

const statesToShow = computed(() => {
	if (!enableStateControls.value) return [];
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

const handleStateMouseDown = (e: MouseEvent, state: string) => {
	if (!props.enableSlider) return;
	const number = ((getStateValue(state) + "" || "") as string).match(/([0-9]+)/)?.[0] || "0";
	const startY = e.clientY;
	const startValue = Number(number);
	const handleMouseMove = (e: MouseEvent) => {
		let diff = (startY - e.clientY) * props.changeFactor;
		diff = Math.round(diff);
		incrementOrDecrementState(state, diff, startValue);
	};
	const handleMouseUp = () => {
		window.removeEventListener("mousemove", handleMouseMove);
	};
	window.addEventListener("mousemove", handleMouseMove);
	window.addEventListener("mouseup", handleMouseUp, { once: true });
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

const enableStyle = (state: string) => {
	blockController.getSelectedBlocks().forEach((block) => {
		block.activeState = `${state}:${props.styleProperty}`;
	});
};

const disableStyle = (state: string) => {
	blockController.getSelectedBlocks().forEach((block) => {
		if (block.activeState === `${state}:${props.styleProperty}`) {
			block.activeState = null;
		}
	});
};

function setDynamicValue(value: string) {
	blockController.getSelectedBlocks().forEach((block) => {
		block.setDynamicValue(props.styleProperty, props.controlType, value);
	});
	showDynamicValueModal.value = false;
	emit("setDynamicValue");
}

const dynamicValue = computed(() => {
	const blocks = blockController.getSelectedBlocks();
	if (!blocks?.length) return;
	const dataKeyObj = blocks[0].dynamicValues.find((obj) => {
		return obj.type === props.controlType && obj.property === props.styleProperty;
	});
	if (dataKeyObj) {
		return dataKeyObj.key;
	} else {
		return "";
	}
});

const clearDynamicValue = () => {
	const blocks = blockController.getSelectedBlocks();
	blocks.forEach((block) => {
		block.removeDynamicValue(props.styleProperty, props.controlType);
	});
	emit("clearDynamicValue");
};
</script>
