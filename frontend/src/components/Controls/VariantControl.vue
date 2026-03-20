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

	<div v-else class="group flex items-center justify-between gap-2" v-bind="$attrs">
		<div
			class="relative flex w-1/3 min-w-[88px] shrink-0 items-center gap-2 before:absolute before:left-[5px] before:-mt-[33px] before:h-[22px] before:w-[1px] before:bg-surface-gray-4 before:content-['_'] after:absolute after:ml-[3px] after:h-1.5 after:w-1.5 after:rounded-full after:bg-surface-gray-4 hover:after:hidden">
			<button
				type="button"
				class="invisible text-ink-gray-7 hover:text-ink-gray-9 group-hover:visible"
				@click="$emit('clear')">
				<FeatherIcon name="x" class="size-3" />
			</button>
			<InputLabel :class="{ 'cursor-ns-resize': enableSlider }" @mousedown="$emit('labelMousedown', $event)">
				{{ label }}
			</InputLabel>
		</div>
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
				class="shrink-1 w-full">
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
