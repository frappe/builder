<template>
	<div class="relative w-full min-w-0">
		<component
			:is="component"
			v-bind="controlAttrs"
			v-on="events || {}"
			:modelValue="modelValue"
			:defaultValue="defaultValue"
			:placeholder="placeholder"
			@update:modelValue="$emit('update:modelValue', $event)"
			@keydown="$emit('keydown', $event)"
			:class="componentClass">
			<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
				<slot :name="name" v-bind="slotData || {}" />
			</template>
		</component>

		<!-- Dynamic value overlay -->
		<div
			v-if="dynamicValueKey"
			class="absolute bottom-0 left-0 right-0 top-0 flex cursor-pointer items-center gap-2 rounded bg-surface-violet-2 py-0.5 pl-2.5 pr-6 text-sm text-ink-violet-8"
			@click.stop="$emit('openDynamicModal')">
			<span class="lucide-zap size-3" aria-hidden="true" />
			<MiddleTruncate :text="dynamicValueKey" />
		</div>

		<!-- Clear button -->
		<button
			v-show="dynamicValueKey"
			class="absolute right-1 top-1 cursor-pointer p-1 text-ink-gray-4 hover:text-ink-gray-5"
			tabindex="-1"
			@click="$emit('clearDynamic')">
			<span class="lucide-x size-3.5" />
		</button>
	</div>
</template>

<script lang="ts" setup>
import type { Component } from "vue";
import MiddleTruncate from "../MiddleTruncate.vue";

const props = defineProps<{
	component: Component;
	controlAttrs?: Record<string, unknown>;
	events?: Record<string, unknown>;
	modelValue: string | number | boolean;
	defaultValue?: string | number | boolean;
	placeholder?: string | number | boolean;
	dynamicValueKey?: string;
	componentClass?: string;
}>();

defineEmits<{
	(e: "update:modelValue", value: string | number | boolean): void;
	(e: "keydown", event: KeyboardEvent): void;
	(e: "openDynamicModal"): void;
	(e: "clearDynamic"): void;
}>();

console.log(99, props.controlAttrs);
</script>
