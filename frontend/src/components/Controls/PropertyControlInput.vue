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
			@keydown.stop="$emit('keydown', $event)"
			:class="componentClass">
			<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
				<slot :name="name" v-bind="slotData || {}" />
			</template>
		</component>

		<!-- Dynamic value overlay -->
		<div
			v-if="dynamicValue"
			class="absolute bottom-0 left-0 right-0 top-0 flex cursor-pointer items-center gap-2 rounded bg-surface-violet-1 py-0.5 pl-2.5 pr-6 text-sm text-ink-violet-1"
			@click.stop="$emit('openDynamicModal')">
			<FeatherIcon name="zap" class="size-3"></FeatherIcon>
			<span class="truncate">{{ dynamicValue }}</span>
		</div>

		<!-- Clear button -->
		<button
			v-show="dynamicValue"
			class="absolute right-1 top-1 cursor-pointer p-1 text-ink-gray-4 hover:text-ink-gray-5"
			tabindex="-1"
			@click="$emit('clearDynamic')">
			<CrossIcon />
		</button>
	</div>
</template>

<script lang="ts" setup>
import CrossIcon from "@/components/Icons/Cross.vue";
import { FeatherIcon } from "frappe-ui";
import type { Component } from "vue";

defineProps<{
	component: Component;
	controlAttrs?: Record<string, unknown>;
	events?: Record<string, unknown>;
	modelValue: string | number;
	defaultValue?: string | number;
	placeholder?: string;
	dynamicValue?: string;
	componentClass?: string;
}>();

defineEmits<{
	(e: "update:modelValue", value: any): void;
	(e: "keydown", event: KeyboardEvent): void;
	(e: "openDynamicModal"): void;
	(e: "clearDynamic"): void;
}>();
</script>
