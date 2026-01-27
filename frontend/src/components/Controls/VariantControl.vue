<template>
	<div v-if="labelPlacement === 'top'" class="flex flex-col gap-1">
		<InputLabel
			class="text-sm"
			:class="{ 'cursor-ns-resize': enableSlider }"
			@mousedown="$emit('labelMousedown', $event)">
			{{ label }}
		</InputLabel>
		<div class="relative">
			<component
				:is="component"
				v-bind="controlAttrs"
				v-on="events || {}"
				:modelValue="modelValue"
				:defaultValue="defaultValue"
				:placeholder="placeholder"
				@update:modelValue="$emit('update:modelValue', $event)"
				@keydown.stop="$emit('keydown', $event)"
				class="w-full">
				<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
					<slot :name="name" v-bind="slotData || {}" />
				</template>
			</component>
			<button
				type="button"
				class="absolute right-1 top-1 text-ink-gray-7 hover:text-ink-gray-9"
				@click="$emit('clear')">
				<FeatherIcon name="x" class="h-3 w-3" />
			</button>
		</div>
	</div>

	<div
		v-else
		class="group ml-[5px] flex items-center justify-between before:-mt-7 before:h-7 before:w-[1px] before:bg-surface-gray-4 before:content-['_'] after:absolute after:left-3.5 after:h-1.5 after:w-1.5 after:rounded-full after:bg-surface-gray-4 hover:after:hidden">
		<button
			type="button"
			class="absolute left-[11px] hidden text-ink-gray-7 hover:text-ink-gray-9 group-hover:block"
			@click="$emit('clear')">
			<FeatherIcon name="x" class="h-3 w-3" />
		</button>
		<InputLabel
			class="ml-3 w-[80px] shrink-0"
			:class="{ 'cursor-ns-resize': enableSlider }"
			@mousedown="$emit('labelMousedown', $event)">
			{{ label }}
		</InputLabel>
		<component
			:is="component"
			v-bind="controlAttrs"
			v-on="events || {}"
			:modelValue="modelValue"
			:defaultValue="defaultValue"
			:placeholder="placeholder"
			@update:modelValue="$emit('update:modelValue', $event)"
			@keydown.stop="$emit('keydown', $event)"
			class="shrink-1 w-full">
			<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
				<slot :name="name" v-bind="slotData || {}" />
			</template>
		</component>
	</div>
</template>

<script lang="ts" setup>
import InputLabel from "@/components/Controls/InputLabel.vue";
import { FeatherIcon } from "frappe-ui";
import type { Component } from "vue";

defineProps<{
	label: string;
	labelPlacement: "left" | "top";
	component: Component;
	controlAttrs?: Record<string, unknown>;
	events?: Record<string, unknown>;
	modelValue: string;
	defaultValue?: string | number;
	placeholder?: string;
	enableSlider?: boolean;
}>();

defineEmits<{
	(e: "update:modelValue", value: any): void;
	(e: "keydown", event: KeyboardEvent): void;
	(e: "labelMousedown", event: MouseEvent): void;
	(e: "clear"): void;
}>();
</script>
