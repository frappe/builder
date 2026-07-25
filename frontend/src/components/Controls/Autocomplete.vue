<template>
	<ComboboxRoot
		v-model="selectedValue"
		v-model:open="isOpen"
		open-on-click
		open-on-focus
		:reset-search-term-on-blur="false">
		<div class="group/autocomplete relative" ref="containerRef">
			<div
				class="group form-input flex h-7 flex-1 items-center gap-2 rounded bg-surface-gray-2 p-0 text-sm text-ink-gray-8 transition-colors focus-within:bg-surface-base focus-within:ring-1 focus-within:ring-outline-gray-4"
				:class="{
					'can-show-arrows': canShowArrows,
				}">
				<div v-if="$slots.prefix" class="flex items-center pl-2">
					<slot name="prefix" />
				</div>
				<ComboboxInput
					ref="comboboxInput"
					v-model="searchQuery"
					autocomplete="off"
					@focus="
						() => {
							emit('focus');
							return false;
						}
					"
					@blur="handleBlur"
					@keydown.enter="handleEnter"
					:display-value="getDisplayValue"
					:placeholder="placeholder"
					class="h-full w-full flex-1 border-none bg-transparent px-0 text-base placeholder:text-ink-gray-4 focus:outline-none focus:ring-0"
					:class="{
						'pl-2': !$slots.prefix,
						'pr-2': !hasValue && !canShowArrows,
					}" />
				<span
					v-if="hasOverflow"
					class="pointer-events-none relative z-10 -ml-4 w-4 flex-shrink-0 self-stretch bg-gradient-to-r from-transparent to-surface-gray-2 group-focus-within:hidden group-hover:to-surface-gray-3"
					aria-hidden="true" />
				<div class="flex items-center gap-0.5">
					<NumberArrows
						v-if="canShowArrows"
						:modelValue="hasNumber"
						@increment="incrementValue"
						@decrement="decrementValue" />

					<button
						v-if="hasValue"
						class="mr-2 flex-shrink-0 cursor-pointer text-ink-gray-4 hover:text-ink-gray-5"
						tabindex="-1"
						@click.stop="clearSelection"
						@mousedown.prevent>
						<span class="lucide-x size-3.5" />
					</button>
				</div>
			</div>

			<Teleport to="body" :disabled="!referenceElementSelector">
				<ComboboxContent
					ref="contentRef"
					class="z-50 max-h-80 w-full overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-base shadow-xl"
					:class="[
						referenceElementSelector ? 'fixed' : 'absolute',
						!referenceElementSelector && openOptionsAbove ? 'bottom-full mb-1' : '',
						!referenceElementSelector && !openOptionsAbove ? 'mt-1' : '',
					]"
					:style="fixedPositionStyles"
					@after-enter="updateOptionsPosition"
					@after-leave="fixedPositionStyles = {}">
					<div class="overflow-y-auto p-1">
						<template v-for="(option, index) in displayOptions" :key="`${option.value}-${index}`">
							<ComboboxSeparator
								v-if="option.value.startsWith('_separator_line')"
								class="bg-outline-gray-2 mx-2 my-1 h-px" />
							<ComboboxLabel
								v-else-if="option.value.startsWith('_separator')"
								class="text-xs-semibold px-2 py-1 text-ink-gray-5">
								{{ option.label }}
							</ComboboxLabel>
							<ComboboxItem
								v-else
								:value="option.value"
								:disabled="option.disabled"
								@mousedown.prevent
								class="group flex cursor-default select-none items-center gap-2 rounded px-2 py-1.5 text-sm text-ink-gray-9 transition-colors data-[disabled]:pointer-events-none data-[highlighted]:bg-surface-gray-1 data-[disabled]:opacity-50">
								<component v-if="option.prefix" :is="option.prefix" class="h-4 w-4 flex-shrink-0" />
								<MiddleTruncate :text="option.label" />
								<component
									v-if="option.suffix"
									:is="option.suffix"
									class="h-4 min-w-4 flex-shrink-0 opacity-60 group-hover:opacity-100"
									@mousedown.stop.prevent
									@click.stop.prevent />
							</ComboboxItem>
						</template>
					</div>
					<div v-if="actionButton" class="border-t border-outline-gray-2 bg-surface-gray-1">
						<component v-if="actionButton.component" :is="actionButton.component" @change="refreshOptions" />
						<Button
							v-else
							:icon-left="actionButton.icon"
							variant="ghost"
							class="w-full justify-start rounded-none text-sm"
							@click="actionButton.handler">
							{{ actionButton.label }}
						</Button>
					</div>
				</ComboboxContent>
			</Teleport>
		</div>
	</ComboboxRoot>
</template>

<script setup lang="ts">
import NumberArrows from "@/components/Controls/NumberArrows.vue";
import { useNumberInput } from "@/utils/useNumberInput";
import { useResizeObserver } from "@vueuse/core";
import {
	ComboboxContent,
	ComboboxInput,
	ComboboxItem,
	ComboboxLabel,
	ComboboxRoot,
	ComboboxSeparator,
} from "reka-ui";
import type { Component, ComponentPublicInstance } from "vue";
import { computed, nextTick, onMounted, ref, useAttrs, watch } from "vue";
import MiddleTruncate from "../MiddleTruncate.vue";

const OPTIONS_GAP = 4;
// keep in sync with the max-h-80 on the options container
const MAX_OPTIONS_HEIGHT = 320;

interface Option {
	label: string;
	value: string;
	prefix?: Component;
	suffix?: Component;
	disabled?: boolean;
}

interface ActionButton {
	label: string;
	handler: () => void;
	icon: string;
	component?: Component;
}

interface Props {
	options?: Option[];
	getOptions?: (query: string) => Promise<Option[]>;
	modelValue?: string | null;
	placeholder?: string;
	showInputAsOption?: boolean;
	actionButton?: ActionButton;
	referenceElementSelector?: string;
	allowArbitraryValue?: boolean;
	disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
	options: () => [],
	placeholder: "Search",
	showInputAsOption: false,
	allowArbitraryValue: true,
});

const emit = defineEmits<{
	"update:modelValue": [value: string | null];
	focus: [];
	blur: [];
}>();

const containerRef = ref<HTMLElement | null>(null);
const isOpen = ref(false);
const searchQuery = ref("");
const asyncOptions = ref<Option[]>([]);
const hasValue = computed(() => props.modelValue != null && props.modelValue !== "");
const comboboxInput = ref<ComponentPublicInstance | null>(null);
const contentRef = ref<ComponentPublicInstance | null>(null);
const fixedPositionStyles = ref<Record<string, string>>({});
const openOptionsAbove = ref(false);
const allOptions = computed(() => (props.getOptions ? asyncOptions.value : props.options));

const hasOverflow = ref(false);

const checkOverflow = () => {
	const input = containerRef.value?.querySelector("input");
	hasOverflow.value = !!input && input.scrollWidth > input.clientWidth;
};

useResizeObserver(containerRef, checkOverflow);
onMounted(checkOverflow);

const attrs = useAttrs();

const { hasNumber, incrementValue, decrementValue } = useNumberInput({
	getValue: () => props.modelValue,
	setValue: (v) => emit("update:modelValue", v),
	getAttrs: () => attrs,
});

const isStrictNumber = computed(() => {
	if (typeof props.modelValue !== "string") return false;
	const nonNumericValues = allOptions.value.map((opt) => opt.value);
	if (nonNumericValues.includes(props.modelValue)) return false;
	return /^\d*\.?\d+(px|%|em|rem)?$/.test(props.modelValue.trim());
});

const canShowArrows = computed(() => hasNumber.value && isStrictNumber.value);

const displayOptions = computed(() => {
	let options = allOptions.value;
	if (
		props.showInputAsOption &&
		searchQuery.value &&
		!options.some((opt) => opt.value === searchQuery.value)
	) {
		options = [{ label: searchQuery.value, value: searchQuery.value }, ...options];
	}
	return options;
});

const selectedValue = computed({
	get: () => props.modelValue,
	set: (value) => {
		emit("update:modelValue", value ?? null);
		isOpen.value = false;
	},
});

const getDisplayValue = (item: any): string => {
	if (typeof item === "object") return item?.label || item?.value || "";
	const found = allOptions.value.find((opt) => opt.value === item);
	return found?.label || item || "";
};

const refreshOptions = async (query = "") => {
	if (!props.getOptions) return;
	try {
		asyncOptions.value = await props.getOptions(query);
	} catch (error) {
		console.error("Failed to load options:", error);
	}
};

const clearSelection = () => emit("update:modelValue", null);

const getInputValue = (event: Event) => (event.target as HTMLInputElement)?.value?.trim();

const submitArbitraryValue = (inputValue: string) => {
	if (!inputValue) return;
	const matchingOption = allOptions.value.find((opt) => opt.label.toLowerCase() === inputValue.toLowerCase());
	emit("update:modelValue", matchingOption?.value ?? inputValue);
	isOpen.value = false;
};

const handleEnter = (event: KeyboardEvent) => {
	if (!props.allowArbitraryValue) return;
	const highlightedItem = containerRef.value?.querySelector("[data-highlighted]");
	const inputValue = getInputValue(event);
	// If there's a highlighted item and user hasn't typed anything different, let the combobox handle it
	if (highlightedItem && !inputValue) return;
	// If user typed something, check if it matches the highlighted item's value
	if (highlightedItem && inputValue) {
		const highlightedValue = highlightedItem.getAttribute("data-value");
		const matchingOption = allOptions.value.find((opt) => opt.value === highlightedValue);
		// If input matches highlighted item's label, let combobox handle it
		if (matchingOption && matchingOption.label.toLowerCase() === inputValue.toLowerCase()) return;
	}
	event.preventDefault();
	event.stopPropagation();
	submitArbitraryValue(inputValue);
};

const handleBlur = (event: FocusEvent) => {
	const relatedTarget = event.relatedTarget as HTMLElement;
	if (relatedTarget && containerRef.value?.contains(relatedTarget)) {
		emit("blur");
		return;
	}
	if (props.allowArbitraryValue) submitArbitraryValue(getInputValue(event));
	emit("blur");
};

watch(searchQuery, (query) => props.getOptions && refreshOptions(query));
watch([searchQuery, () => props.modelValue, allOptions], () => nextTick(checkOverflow), { flush: "post" });
watch(
	() => props.modelValue,
	(val) => (searchQuery.value = val ?? ""),
	{ immediate: true },
);

watch(isOpen, (val) => {
	if (val) nextTick(updateOptionsPosition);
});

watch(displayOptions, () => {
	if (isOpen.value) nextTick(updateOptionsPosition);
});

if (props.getOptions) refreshOptions();

const shouldOpenOptionsAbove = () => {
	const comboboxInputRect = containerRef.value?.getBoundingClientRect();
	if (!comboboxInputRect) return false;

	const contentRect = (contentRef.value?.$el as HTMLElement | undefined)?.getBoundingClientRect();
	const optionsHeight = Math.min(contentRect?.height || MAX_OPTIONS_HEIGHT, MAX_OPTIONS_HEIGHT);
	const spaceBelow = window.innerHeight - comboboxInputRect.bottom - OPTIONS_GAP;
	const spaceAbove = comboboxInputRect.top - OPTIONS_GAP;

	return spaceBelow < optionsHeight && spaceAbove > spaceBelow;
};

const updateOptionsPosition = () => {
	openOptionsAbove.value = shouldOpenOptionsAbove();
	fixedPositionStyles.value = props.referenceElementSelector ? getFixedPositionStyles() : {};
};

// inside a Popover, absolute positioning keeps the options within the Popover and takes extra
// space; fixed positioning lets them float above the Popover container instead
const getFixedPositionStyles = (): Record<string, string> => {
	const comboboxInputRect = containerRef.value?.getBoundingClientRect();
	if (!comboboxInputRect) return {};

	const top = openOptionsAbove.value ? "unset" : comboboxInputRect.bottom + OPTIONS_GAP + "px";
	const bottom = openOptionsAbove.value
		? window.innerHeight - comboboxInputRect.top + OPTIONS_GAP + "px"
		: "unset";
	const left = comboboxInputRect.left + "px";

	return {
		top,
		bottom,
		left,
		width: comboboxInputRect.width + "px",
		zIndex: "999",
	};
};

defineExpose({
	refreshOptions,
	clearSelection,
});
</script>
<style scoped>
.can-show-arrows:hover {
	gap: 3px !important;
}
</style>
