<template>
	<div class="relative">
		<Combobox
			:modelValue="value"
			@update:modelValue="
				(val) => {
					emit('update:modelValue', val);
				}
			"
			v-slot="{ open }"
			:nullable="nullable"
			:multiple="multiple">
			<ComboboxButton v-show="false" ref="comboboxButton"></ComboboxButton>
			<div
				class="form-input flex h-7 w-full items-center justify-between gap-2 rounded border-outline-gray-1 bg-surface-gray-1 p-0 text-sm text-ink-gray-8 transition-colors hover:border-outline-gray-2 hover:bg-surface-gray-1">
				<!-- {{ displayValue }} -->
				<template v-if="$slots.prefix">
					<div class="absolute left-2 top-1.5 z-10 flex items-center">
						<slot name="prefix" />
					</div>
				</template>
				<ComboboxInput
					autocomplete="off"
					@focus="
						() => {
							if (!open.value) {
								$refs.comboboxButton?.$el.click();
							}
							emit('focus');
							return false;
						}
					"
					@blur="emit('blur')"
					@change="query = $event.target.value"
					:displayValue="getDisplayValue"
					:placeholder="!modelValue ? placeholder : null"
					:class="[
						'h-full w-full rounded border-none bg-transparent pr-5.5 text-base focus:ring-2 focus:ring-outline-gray-3',
						$slots.prefix ? 'pl-1' : 'pl-2',
					]"></ComboboxInput>
			</div>
			<ComboboxOptions
				class="absolute right-0 z-50 w-full overflow-y-auto rounded-lg border border-outline-gray-2 bg-surface-white p-0 shadow-2xl"
				v-show="filteredOptions.length">
				<div class="w-full list-none px-1.5 py-1.5">
					<ComboboxOption v-if="query" :value="query" class="flex items-center"></ComboboxOption>
					<ComboboxOption
						v-for="option in filteredOptions"
						v-slot="{ active, selected }"
						:key="option.value"
						:value="option"
						:disabled="String(option.value).startsWith('_separator')"
						:title="option.label"
						class="flex items-center">
						<span
							v-if="String(option.value).startsWith('_separator')"
							class="flex w-full items-center gap-2 px-2.5 pb-2 pt-3 text-xs font-medium !text-ink-gray-5">
							{{ option.label }}
						</span>
						<li
							v-else
							class="w-full select-none truncate rounded px-2.5 py-1.5 text-xs"
							:class="{
								'bg-gray-100': active,
								'bg-gray-300': selected,
							}">
							{{ option.label }}
						</li>
					</ComboboxOption>
				</div>
				<div
					class="sticky bottom-0 rounded-b-sm border-t border-outline-gray-2 bg-surface-gray-1"
					v-if="actionButton">
					<component
						:is="actionButton.component"
						v-if="actionButton?.component"
						@change="updateOptions"></component>
					<BuilderButton
						v-else
						:iconLeft="actionButton.icon"
						class="w-full rounded-none text-xs text-ink-gray-8"
						@click="actionButton.handler">
						{{ actionButton.label }}
					</BuilderButton>
				</div>
			</ComboboxOptions>
		</Combobox>
		<div
			class="absolute right-[1px] top-[3px] cursor-pointer p-1 text-ink-gray-4 hover:text-ink-gray-5"
			@click="clearValue"
			v-show="modelValue">
			<CrossIcon />
		</div>
	</div>
</template>

<script setup lang="ts">
import BuilderButton from "@/components/Controls/BuilderButton.vue";
import CrossIcon from "@/components/Icons/Cross.vue";
import { Combobox, ComboboxButton, ComboboxInput, ComboboxOption, ComboboxOptions } from "@headlessui/vue";
import { ComputedRef, computed, ref, watch } from "vue";

type Option = {
	label: string;
	value: string;
};

const emit = defineEmits(["update:modelValue", "focus", "blur"]);

type Action = {
	label: String;
	handler: () => void;
	icon: string;
	component?: any;
};

const props = withDefaults(
	defineProps<{
		options?: Option[];
		getOptions?: (filterString: string) => Promise<Option[]>;
		modelValue?: any;
		placeholder?: string;
		showInputAsOption?: boolean;
		actionButton?: Action;
	}>(),
	{
		options: () => [],
		placeholder: "Search",
		showInputAsOption: false,
	},
);

const query = ref("");
const multiple = computed(() => Array.isArray(props.modelValue));
const nullable = computed(() => !multiple.value);
const filteredOptions = ref(props.options);

const getDisplayValue = (option: Option | Option[]) => {
	if (Array.isArray(option)) {
		return option.map((o) => o.label).join(", ");
	} else if (option) {
		return option.label || option.value || "";
	} else {
		return "";
	}
};

const value = computed(() => {
	if (!props.modelValue) {
		return null;
	}
	return (
		filteredOptions.value.find((option) => option.value === props.modelValue) || {
			label: props.modelValue,
			value: props.modelValue,
		}
	);
}) as ComputedRef<Option>;

watch(() => query.value || props.options, updateOptions, { immediate: true });

async function updateOptions() {
	if (props.getOptions) {
		const options = await props.getOptions(query.value);
		filteredOptions.value = options;
	} else {
		if (!query.value) {
			filteredOptions.value = props.options;
		} else {
			filteredOptions.value = props.options.filter((option) => {
				const label = option.label.toLowerCase();
				const value = option.label.toLowerCase();
				const queryLower = query.value.toLowerCase();
				return label.includes(queryLower) || value.includes(query.value);
			});
		}
	}
}

const clearValue = () => emit("update:modelValue", null);
defineExpose({
	updateOptions,
});
</script>
