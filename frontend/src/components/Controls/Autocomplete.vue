<template>
	<ComboboxRoot
		v-model="selectedValue"
		v-model:open="isOpen"
		open-on-click
		open-on-focus
		:reset-search-term-on-blur="false">
		<div class="relative">
			<div
				class="group form-input flex h-7 flex-1 items-center gap-2 rounded border-outline-gray-1 bg-surface-gray-1 p-0 text-sm text-ink-gray-8 transition-colors focus-within:ring-2 focus-within:ring-outline-gray-3 hover:border-outline-gray-2">
				<div v-if="$slots.prefix" class="flex items-center pl-2">
					<slot name="prefix" />
				</div>
				<ComboboxInput
					v-model="searchQuery"
					autocomplete="off"
					@focus="emit('focus')"
					@blur="handleBlur"
					@keydown.enter="handleEnter"
					:display-value="getDisplayValue"
					:placeholder="placeholder"
					class="h-full w-full flex-1 border-none bg-transparent px-0 text-base placeholder:text-ink-gray-4 focus:outline-none focus:ring-0"
					:class="{
						'pl-2': !$slots.prefix,
						'pr-2': !hasValue,
					}" />
				<Button v-if="hasValue" variant="ghost" @click.stop="clearSelection">
					<CrossIcon class="h-3 w-3" />
				</Button>
			</div>

			<ComboboxContent
				class="absolute z-50 mt-1 max-h-80 w-full overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white shadow-xl">
				<div class="overflow-y-auto p-1">
					<template v-for="(option, index) in displayOptions" :key="`${option.value}-${index}`">
						<ComboboxSeparator
							v-if="option.value.startsWith('_separator_line')"
							class="bg-outline-gray-2 mx-2 my-1 h-px" />
						<ComboboxLabel
							v-else-if="option.value.startsWith('_separator')"
							class="px-2 py-1 text-xs font-semibold text-ink-gray-5">
							{{ option.label }}
						</ComboboxLabel>
						<ComboboxItem
							v-else
							:value="option"
							:disabled="option.disabled"
							class="group flex cursor-default select-none items-center gap-2 rounded px-2 py-1.5 text-sm text-ink-gray-9 transition-colors data-[disabled]:pointer-events-none data-[highlighted]:bg-surface-gray-1 data-[disabled]:opacity-50">
							<component v-if="option.prefix" :is="option.prefix" class="h-4 w-4 flex-shrink-0" />
							<span class="w-full flex-1 truncate">{{ option.label }}</span>
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
					<BuilderButton
						v-else
						:icon-left="actionButton.icon"
						variant="ghost"
						class="w-full justify-start rounded-none text-sm"
						@click="actionButton.handler">
						{{ actionButton.label }}
					</BuilderButton>
				</div>
			</ComboboxContent>
		</div>
	</ComboboxRoot>
</template>

<script setup lang="ts">
import BuilderButton from "@/components/Controls/BuilderButton.vue";
import CrossIcon from "@/components/Icons/Cross.vue";
import {
	ComboboxContent,
	ComboboxInput,
	ComboboxItem,
	ComboboxLabel,
	ComboboxRoot,
	ComboboxSeparator,
} from "reka-ui";
import type { Component } from "vue";
import { computed, ref, watch } from "vue";

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
	allowArbitraryValue?: boolean;
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

const isOpen = ref(false);
const searchQuery = ref("");
const asyncOptions = ref<Option[]>([]);
const hasValue = computed(() => props.modelValue != null && props.modelValue !== "");
const allOptions = computed(() => (props.getOptions ? asyncOptions.value : props.options));

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

const clearSelection = () => {
	emit("update:modelValue", null);
};

const handleEnter = (event: KeyboardEvent) => {
	if (!props.allowArbitraryValue) return;

	const inputValue = (event.target as HTMLInputElement)?.value?.trim();
	if (inputValue) {
		event.preventDefault();
		event.stopPropagation();
		emit("update:modelValue", inputValue);
		isOpen.value = false;
	}
};

const handleBlur = (event: FocusEvent) => {
	if (props.allowArbitraryValue) {
		const inputValue = (event.target as HTMLInputElement)?.value?.trim();
		if (inputValue) {
			emit("update:modelValue", inputValue);
		}
	}
	emit("blur");
};

watch(searchQuery, (newQuery) => props.getOptions && refreshOptions(newQuery));

watch(
	() => props.modelValue,
	(newValue) => {
		searchQuery.value = newValue ?? "";
	},
);

if (props.getOptions) {
	refreshOptions();
}

defineExpose({
	refreshOptions,
	clearSelection,
});
</script>
