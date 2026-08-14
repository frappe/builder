<template>
	<div
		v-if="labelPlacement === 'top'"
		ref="rowRef"
		class="flex flex-col gap-1"
		v-bind="$attrs"
		@focusout="handleFocusOut">
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
				@mousedown.stop.prevent
				@click="emit('clear')">
				<span class="lucide-x h-3 w-3" aria-hidden="true" />
			</button>
		</div>
	</div>

	<div
		v-else
		ref="rowRef"
		class="group/variant relative flex items-start justify-between gap-2"
		v-bind="$attrs"
		@focusout="handleFocusOut">
		<span
			class="pointer-events-none absolute left-[5.5px] top-0 w-px bg-surface-gray-4"
			:class="isLast ? 'h-3.5' : '-bottom-2'"
			aria-hidden="true" />
		<div class="relative flex h-7 w-1/3 min-w-[88px] shrink-0 items-center gap-2">
			<span class="relative z-[1] flex size-3 shrink-0 items-center justify-center bg-surface-base">
				<span
					class="size-1.5 rounded-full group-hover/variant:hidden"
					:class="isActive ? 'bg-surface-gray-7' : 'bg-surface-gray-4'" />
				<button
					type="button"
					class="invisible absolute inset-0 flex items-center justify-center text-ink-gray-7 hover:text-ink-gray-9 group-hover/variant:visible"
					@mousedown.stop.prevent
					@click="emit('clear')">
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
import { useEventListener } from "@vueuse/core";
import type { Component } from "vue";
import { ref, watch } from "vue";

const props = defineProps<{
	label: string;
	labelPlacement: "left" | "top";
	component: Component;
	controlAttrs?: Record<string, unknown>;
	events?: Record<string, unknown>;
	modelValue: string | number | boolean;
	defaultValue?: string | number | boolean;
	placeholder?: string | number | boolean;
	enableSlider?: boolean;
	isActive?: boolean;
	isLast?: boolean;
}>();

const emit = defineEmits<{
	(e: "update:modelValue", value: any): void;
	(e: "keydown", event: KeyboardEvent): void;
	(e: "labelMousedown", event: MouseEvent): void;
	(e: "clear"): void;
	(e: "blur"): void;
}>();

const rowRef = ref<HTMLElement | null>(null);

const holdsFocus = () => !!rowRef.value?.contains(document.activeElement);
const field = () => rowRef.value?.querySelector<HTMLElement>("input, select");

// The label dropdown hands focus to its trigger span as it closes, so focus lands
// on <body> a few frames after the row appears. Take it back until something else holds it.
let claimingFocus = false;

const claimFocus = (framesLeft: number) => {
	claimingFocus = framesLeft > 0 && !!props.isActive;
	if (!claimingFocus) return;
	if (document.activeElement === document.body) field()?.focus();
	requestAnimationFrame(() => claimFocus(framesLeft - 1));
};

// A popover panel sits outside the row, so focus that lands in one is not the user leaving.
// The preview lasts until the panel closes.
const PANEL = "[data-slot='content']";
let watchedPanel: Element | null = null;
let pressThatClosedPanel: MouseEvent | null = null;

useEventListener(document, "mousedown", (event: MouseEvent) => (pressThatClosedPanel = event), {
	capture: true,
});

// A press on the row, or on a canvas handle that prevents the default, keeps editing this
// state. Anything else is the user leaving.
const pressKeepsPreview = () => {
	const press = pressThatClosedPanel;
	if (!press) return false;
	return press.defaultPrevented || Boolean(rowRef.value?.contains(press.target as Node));
};

const watchPanel = (panel: Element) => {
	if (watchedPanel === panel) return;
	watchedPanel = panel;
	pressThatClosedPanel = null;
	const check = () => {
		if (watchedPanel !== panel) return;
		if (panel.isConnected) return requestAnimationFrame(check);
		watchedPanel = null;
		claimingFocus = false;
		// Another control now owns the state.
		if (!props.isActive || holdsFocus()) return;
		if (pressKeepsPreview()) return field()?.focus();
		emit("blur");
	};
	requestAnimationFrame(check);
};

const panelFor = (relatedTarget: Element | null) =>
	relatedTarget?.closest?.(PANEL) || document.querySelector(PANEL);

// Leaving the row ends the preview. Focus that goes nowhere is the dropdown closing,
// not the user leaving.
const handleFocusOut = (event: FocusEvent) => {
	const relatedTarget = event.relatedTarget as Element | null;
	if (rowRef.value?.contains(relatedTarget)) return;
	const panel = panelFor(relatedTarget);
	if (panel) return watchPanel(panel);
	if (claimingFocus && !relatedTarget) return;
	claimingFocus = false;
	emit("blur");
};

// The canvas previews the active state, so put the caret in its field. This also marks
// the row with the focus styling.
watch(
	() => props.isActive,
	(isActive) => {
		if (!isActive || holdsFocus()) return;
		field()?.focus();
		claimFocus(20);
	},
	{ immediate: true, flush: "post" },
);
</script>
