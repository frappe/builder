<template>
	<TabsRoot :modelValue="currentIndex" @update:modelValue="handleChange">
		<TabsList class="box-border flex space-x-1 rounded bg-surface-gray-2 p-0.5 text-sm">
			<TabsTrigger
				v-for="(button, i) in buttons"
				:key="button.label"
				:value="i"
				:class="[
					'flex flex-1 justify-center gap-2 whitespace-nowrap rounded px-2 py-1 leading-none transition-colors focus:outline-none focus-visible:ring focus-visible:ring-outline-gray-2',
					isValueSet()
						? 'text-ink-gray-7 data-[state=active]:bg-surface-white data-[state=active]:text-ink-gray-9 data-[state=active]:shadow'
						: 'text-ink-gray-7 data-[state=active]:border data-[state=active]:border-dashed data-[state=active]:border-outline-gray-3',
				]">
				<Tooltip :disabled="!button.showTooltip" :text="button.label" placement="top">
					<div class="flex min-h-4 items-center gap-2">
						<component
							v-if="button.icon"
							:is="typeof button.icon === 'string' ? FeatherIcon : button.icon"
							class="size-4"
							v-bind="typeof button.icon === 'string' ? { name: button.icon, label: button.label } : {}"
							:aria-label="button.label" />
						<span class="flex items-center" v-show="button.label && !button.hideLabel">
							{{ button.label }}
						</span>
					</div>
				</Tooltip>
			</TabsTrigger>
		</TabsList>
	</TabsRoot>
</template>

<script lang="ts" setup>
import { FeatherIcon, Tooltip } from "frappe-ui";
import { TabsList, TabsRoot, TabsTrigger } from "reka-ui";
import type { Component } from "vue";
import { computed } from "vue";

interface Button {
	label: string;
	value?: string | number | boolean;
	icon?: string | Component;
	hideLabel?: boolean;
	showTooltip?: boolean;
}

const props = defineProps<{
	buttons: Button[];
	modelValue?: string | number | boolean;
	defaultValue?: string | number;
}>();

const emit = defineEmits<{
	(e: "update:modelValue", value: string | number | boolean): void;
}>();

const isValueSet = (): boolean => {
	return props.modelValue !== undefined && props.modelValue !== null && props.modelValue !== "";
};

const activeValue = computed(() => (isValueSet() ? props.modelValue : props.defaultValue));

const currentIndex = computed(() => {
	const idx = props.buttons.findIndex((b) => (b.value ?? b.label) === activeValue.value);
	return idx >= 0 ? idx : 0;
});

function handleChange(index: string | number) {
	const i = typeof index === "string" ? parseInt(index) : index;
	const button = props.buttons[i];
	if (button) {
		emit("update:modelValue", button.value ?? button.label);
	}
}
</script>
