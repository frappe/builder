<template>
	<div v-if="labelPlacement === 'top'" class="flex flex-col gap-1" v-bind="$attrs">
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
		class="group relative flex items-center gap-2 before:absolute before:left-[5px] before:-mt-9 before:h-7.5 before:w-[1px] before:bg-surface-gray-4 before:content-['_'] after:absolute after:left-[2.5px] after:size-1.5 after:rounded-full after:bg-surface-gray-4 hover:after:hidden"
		v-bind="$attrs">
		<button
			type="button"
			class="absolute hidden text-ink-gray-7 hover:text-ink-gray-9 group-hover:block"
			@click="$emit('clear')">
			<FeatherIcon name="x" class="size-3" />
		</button>
		<InputLabel
			class="flex w-1/3 min-w-[88px] max-w-none shrink-0 pl-5"
			:class="{ 'cursor-ns-resize': enableSlider }"
			@mousedown="$emit('labelMousedown', $event)">
			{{ label }}
		</InputLabel>
		<div class="relative w-full min-w-0">
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
		</div>
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
	modelValue: string | number | boolean;
	defaultValue?: string | number | boolean;
	placeholder?: string | number | boolean;
	enableSlider?: boolean;
}>();

defineEmits<{
	(e: "update:modelValue", value: any): void;
	(e: "keydown", event: KeyboardEvent): void;
	(e: "labelMousedown", event: MouseEvent): void;
	(e: "clear"): void;
}>();
</script>
