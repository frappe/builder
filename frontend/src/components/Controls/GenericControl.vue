<template>
	<div class="flex w-full flex-col gap-2">
		<!-- Top label placement -->
		<div v-if="labelPlacement === 'top' && label" class="flex items-center gap-2">
			<Dropdown v-if="enableStateControls || allowDynamicValue" size="sm" :options="options">
				<template v-slot="{ open }">
					<FeatherIcon
						ref="dropdownTrigger"
						name="plus-circle"
						class="h-3 w-3 cursor-pointer text-ink-gray-7 hover:text-ink-gray-9"
						@click="open" />
				</template>
			</Dropdown>
			<InputLabel class="truncate" :class="{ 'cursor-ns-resize': enableSlider }" @mousedown="handleMouseDown">
				{{ label }}
			</InputLabel>
		</div>

		<!-- Control container with conditional layout -->
		<div
			class="relative flex w-full gap-2"
			:class="labelPlacement === 'top' ? 'items-start' : 'items-center'">
			<!-- Left label placement (original layout) -->
			<div
				class="flex w-[88px] shrink-0 items-center"
				v-if="labelPlacement === 'left' && (enableStateControls || label)">
				<Dropdown v-if="enableStateControls || allowDynamicValue" size="sm" :options="options">
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

			<!-- Hidden popup for dynamic values -->
			<DraggablePopup
				v-model="showDynamicValueModal"
				:container="dropdownTrigger?.$el"
				placement="middle-right"
				:clickOutsideToClose="false"
				:placementOffset="20"
				v-if="showDynamicValueModal">
				<template #header>Set Dynamic Value</template>
				<template #content>
					<DynamicValueHandler @setDynamicValue="setDynamicValue" :selectedValue="dynamicValue" :options="dynamicValueFilterOptions" />
				</template>
			</DraggablePopup>

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
					v-if="dynamicValue?.key">
					<FeatherIcon
						v-if="dynamicValue?.comesFrom == 'props'"
						name="git-commit"
						class="size-3"></FeatherIcon>
					<FeatherIcon v-else name="zap" class="size-3"></FeatherIcon>
					<span class="truncate">{{ dynamicValue.key }}</span>
				</div>
				<button
					class="absolute right-1 top-1 z-20 cursor-pointer p-1 text-ink-gray-4 hover:text-ink-gray-5"
					tabindex="-1"
					v-show="dynamicValue?.key"
					@click="clearDynamicValue">
					<CrossIcon />
				</button>
			</div>
		</div>
	</div>
</template>
<script lang="ts" setup>
import DynamicValueHandler from "@/components/Controls/DynamicValueHandler.vue";
import Input from "@/components/Controls/Input.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import CrossIcon from "@/components/Icons/Cross.vue";
import blockController from "@/utils/blockController";
import { extractNumberAndUnit, normalizeValueWithUnits } from "@/utils/helpers";
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
		property?: string;
		label?: string;
		placeholder?: string;
		controlType?: "style" | "attribute" | "key";
		getModelValue?: () => string;
		getPlaceholder?: () => string;
		getDynamicValue?: () => { key: string; comesFrom: BlockDataKey["comesFrom"] } | undefined;
		setModelValue?: (value: string) => void;
		setDynamicValue?: (key: string | null, comesFrom: BlockDataKey["comesFrom"] | null) => void;
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
		labelPlacement?: "left" | "top";
		dynamicValueFilterOptions?: {
			excludePassedDownProps?: boolean;
			excludePassedDownBlockData?: boolean;
			excludeOwnProps?: boolean;
			excludeOwnBlockData?: boolean;
		};
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
		labelPlacement: "left",
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
	return props.defaultValue;
});

const modelValue = computed(() => props.getModelValue?.() ?? "");

const placeholderValue = computed(() => props.getPlaceholder?.() ?? String(props.placeholder));

const updateValue = (value: string | number | null | { label: string; value: string }) => {
	if (typeof value === "object" && value !== null && "value" in value) {
		value = value.value;
	}
	if (props.setModelValue) {
		props.setModelValue(value as string);
	}
};

const handleMouseDown = (e: MouseEvent) => {
	if (!props.enableSlider) return;
	const { number } = extractNumberAndUnit(String(modelValue.value || ""));
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

const showDynamicValueModal = ref(false);

const handleKeyDown = (e: KeyboardEvent, state?: string) => {
	if (!props.enableSlider) return;
	if (e.key === "ArrowUp" || e.key === "ArrowDown") {
		const step = e.key === "ArrowUp" ? 1 : -1;
		incrementOrDecrement(step);
		e.preventDefault();
	}
};

const incrementOrDecrement = (step: number, initialValue: null | number = null) => {
	const value = String(modelValue.value || "");
	const { number, unit: existingUnit } = extractNumberAndUnit(value);
	const unit =
		existingUnit || (props.unitOptions.length && !isNaN(Number(number)) ? props.unitOptions[0] : "");
	let newValue = (initialValue != null ? Number(initialValue) : Number(number)) + step;
	if (typeof props.minValue === "number" && newValue <= props.minValue) {
		newValue = props.minValue;
	}
	if (typeof props.maxValue === "number" && props.maxValue !== null && newValue >= props.maxValue) {
		newValue = props.maxValue;
	}
	updateValue(newValue + "" + unit);
};

const options = computed(() => {
	const opts = [];
	if (props.allowDynamicValue) {
		opts.unshift({
			label: "Set Dynamic Value",
			onClick: () => {
				showDynamicValueModal.value = true;
			},
		});
	}
	return opts;
});

function setDynamicValue({ key, comesFrom }: { key: string; comesFrom?: BlockDataKey["comesFrom"] }) {
	if (!comesFrom) comesFrom = "dataScript";
	if (props.setDynamicValue) {
		props.setDynamicValue(key, comesFrom);
	} else {
		blockController.getSelectedBlocks().forEach((block) => {
			block.setDynamicValue(props.property, props.controlType, key, comesFrom);
		});
	}
	showDynamicValueModal.value = false;
	emit("setDynamicValue");
}

const dynamicValue = computed(() => {
	if (props.getDynamicValue) {
		return props.getDynamicValue();
	}
	const blocks = blockController.getSelectedBlocks();
	if (!blocks?.length) return undefined;
	const dataKeyObj = blocks[0].dynamicValues.find((obj) => {
		return obj.type === props.controlType && obj.property === props.property;
	});

	if (dataKeyObj) {
		return {
			key: dataKeyObj.key || "",
			comesFrom: dataKeyObj.comesFrom || ("dataScript" as BlockDataKey["comesFrom"]),
		};
	} else {
		return { key: "", comesFrom: "dataScript" as BlockDataKey["comesFrom"] };
	}
});

const clearDynamicValue = () => {
	if (props.setDynamicValue) {
		props.setDynamicValue(null, null);
	} else {
		const blocks = blockController.getSelectedBlocks();
		blocks.forEach((block) => {
			block.removeDynamicValue(props.property, props.controlType);
		});
	}
	emit("clearDynamicValue");
};
</script>
