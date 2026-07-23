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
				<span class="lucide-x h-3 w-3" aria-hidden="true" />
			</button>
		</div>
	</div>

	<div v-else class="group/variant relative flex items-start justify-between gap-2" v-bind="$attrs">
		<span
			class="pointer-events-none absolute left-[5.5px] top-0 w-px bg-surface-gray-4"
			:class="isLast ? 'h-3.5' : '-bottom-2'"
			aria-hidden="true" />
		<div class="relative flex h-7 w-1/3 min-w-[88px] shrink-0 items-center gap-2">
			<span class="relative z-[1] flex size-3 shrink-0 items-center justify-center bg-surface-base">
				<span class="size-1.5 rounded-full bg-surface-gray-4 group-hover/variant:hidden" />
				<button
					type="button"
					class="invisible absolute inset-0 flex items-center justify-center text-ink-gray-7 hover:text-ink-gray-9 group-hover/variant:visible"
					@click="$emit('clear')">
					<span class="lucide-x size-3" aria-hidden="true" />
				</button>
			</span>
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
	isLast?: boolean;
}>();

defineEmits<{
	(e: "update:modelValue", value: any): void;
	(e: "keydown", event: KeyboardEvent): void;
	(e: "labelMousedown", event: MouseEvent): void;
	(e: "clear"): void;
}>();
</script>
