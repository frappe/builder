<template>
	<div ref="containerRef" class="group relative w-full" :class="paddingClass">
		<Select
			v-if="type === 'select'"
			:modelValue="data as string"
			@update:modelValue="(value) => (data = value as typeof data)"
			:disabled="disabled"
			v-bind="attrs" />
		<FormControl
			v-else
			:type="type"
			@change="triggerUpdate"
			@paste="triggerUpdate"
			@cut="triggerUpdate"
			@focus="handleFocus"
			@input="($event: Event) => emit('input', ($event.target as HTMLInputElement).value)"
			autocomplete="off"
			:autofocus="autofocus"
			:disabled="disabled"
			v-bind="attrs"
			:modelValue="data">
			<template #prefix v-if="$slots.prefix">
				<slot name="prefix" />
			</template>
			<template #suffix v-if="hasSuffix">
				<div class="flex items-center gap-0.5">
					<NumberArrows
						:modelValue="hasNumber"
						v-if="canShowArrows"
						@increment="incrementValue"
						@decrement="decrementValue" />

					<slot v-if="$slots.suffix" name="suffix" />

					<button
						v-if="hasClearButton"
						class="cursor-pointer text-ink-gray-4 hover:text-ink-gray-5"
						tabindex="-1"
						@click="clearValue">
						<CrossIcon />
					</button>
				</div>
			</template>
		</FormControl>
	</div>
</template>
<script lang="ts" setup>
import NumberArrows from "@/components/Controls/NumberArrows.vue";
import CrossIcon from "@/components/Icons/Cross.vue";
import { useNumberInput } from "@/utils/useNumberInput";
import { useDebounceFn, useResizeObserver, useVModel } from "@vueuse/core";
import { Select } from "frappe-ui";
import { computed, ref, useAttrs, useSlots } from "vue";

const props = withDefaults(
	defineProps<{
		modelValue?: string | number | boolean | null;
		type?: string;
		hideClearButton?: boolean;
		autofocus?: boolean;
		disabled?: boolean;
		selectOnFocus?: boolean;
	}>(),
	{
		type: "text",
		modelValue: "",
		selectOnFocus: true,
	},
);
const emit = defineEmits(["update:modelValue", "input"]);
const data = useVModel(props, "modelValue", emit);

interface UseNumberInputOptions {
	getValue: () => string | number | boolean | null | undefined;
	setValue: (value: string) => void;
	getAttrs?: () => Record<string, unknown>;
}

const isStrictNumber = computed(() => {
	if (typeof data.value !== "string") return false;

	return /^\d*\.?\d+(px|%|em|rem)?$/.test(data.value.trim());
});

defineOptions({
	inheritAttrs: false,
});

const attrs = useAttrs();
const slots = useSlots();

const containerRef = ref<HTMLElement | null>(null);
const containerWidth = ref(Infinity);
useResizeObserver(containerRef, (entries) => {
	containerWidth.value = entries[0].contentRect.width;
});

const canShowArrows = computed(
	() => !props.disabled && hasNumber.value && isStrictNumber.value && containerWidth.value >= 60,
);

const hasClearButton = computed(
	() =>
		!["select", "checkbox"].includes(props.type) && !props.hideClearButton && !!data.value && !props.disabled,
);

const hasSuffix = computed(() => canShowArrows.value || hasClearButton.value || !!slots.suffix);

const paddingClass = computed(() => {
	if (canShowArrows.value && hasClearButton.value) return "has-both-suffix";
	if (canShowArrows.value && !hasClearButton.value) return "arrows-only-suffix";
	if (!canShowArrows.value && hasClearButton.value) return "cross-only-suffix";
	return "";
});

const { hasNumber, incrementValue, decrementValue } = useNumberInput({
	getValue: () => data.value,
	setValue: (v) => {
		data.value = v;
		emit("update:modelValue", v);
	},
	getAttrs: () => attrs,
});

const clearValue = () => {
	data.value = "";
	emit("update:modelValue", "");
	emit("input", "");
};

const triggerUpdate = useDebounceFn(($event: Event) => {
	if (props.type === "checkbox") {
		emit("update:modelValue", ($event.target as HTMLInputElement).checked);
	} else {
		emit("update:modelValue", ($event.target as HTMLInputElement).value);
	}
}, 100);

const handleFocus = ($event: Event) => {
	if (props.selectOnFocus && !props.disabled && props.type !== "checkbox") {
		const target = $event.target as HTMLInputElement;
		setTimeout(() => {
			target.select();
		}, 0);
	}
};
</script>

<style>
input[type="number"]::-webkit-outer-spin-button,
input[type="number"]::-webkit-inner-spin-button {
	-webkit-appearance: none !important;
	margin: 0 !important;
}

input[type="number"] {
	-moz-appearance: textfield !important;
	appearance: textfield !important;
}
</style>

<style scoped>
.arrows-only-suffix :deep(input + div) {
	padding-inline-end: 3px;
}

.arrows-only-suffix :deep(input) {
	padding-inline-end: 3px;
}

.arrows-only-suffix:hover :deep(input) {
	padding-right: 1.4rem !important;
}

.cross-only-suffix :deep(input) {
	padding-right: 1.8rem !important;
}

.has-both-suffix :deep(input) {
	padding-right: 1.5rem !important;
}

.has-both-suffix:hover :deep(input) {
	padding-right: 2.8rem !important;
}
</style>
