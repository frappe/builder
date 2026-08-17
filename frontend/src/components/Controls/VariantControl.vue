<template>
	<div
		ref="rowRef"
		class="relative flex"
		:class="isTopLabel ? 'flex-col gap-1' : 'group/variant items-start justify-between gap-2'"
		v-bind="$attrs"
		@focusout="handleFocusOut">
		<InputLabel
			v-if="isTopLabel"
			class="text-sm"
			:class="{ 'cursor-ns-resize': enableSlider }"
			@mousedown="$emit('labelMousedown', $event)">
			{{ label }}
		</InputLabel>
		<template v-else>
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
				<InputLabel
					:class="{ 'cursor-ns-resize': enableSlider }"
					@mousedown="$emit('labelMousedown', $event)">
					{{ label }}
				</InputLabel>
			</div>
		</template>
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
			<button
				v-if="isTopLabel"
				type="button"
				class="absolute right-1 top-1 text-ink-gray-7 hover:text-ink-gray-9"
				@mousedown.stop.prevent
				@click="emit('clear')">
				<span class="lucide-x size-3" aria-hidden="true" />
			</button>
		</div>
	</div>
</template>

<script lang="ts" setup>
import InputLabel from "@/components/Controls/InputLabel.vue";
import { useEventListener } from "@vueuse/core";
import type { Component } from "vue";
import { computed, ref, watch } from "vue";

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

const isTopLabel = computed(() => props.labelPlacement === "top");

const rowRef = ref<HTMLElement | null>(null);
const panelSelector = "[data-slot='content']";

const hasFocus = () => rowRef.value?.contains(document.activeElement) ?? false;
const focusField = () => rowRef.value?.querySelector<HTMLElement>("input, select")?.focus();

// Reclaim focus after a label dropdown closes, until another element owns it.
let claimingFocus = false;

const endPreview = () => {
	claimingFocus = false;
	emit("blur");
};

const keepFocus = (framesLeft: number) => {
	claimingFocus = framesLeft > 0 && !!props.isActive;
	if (!claimingFocus) return;
	if (document.activeElement === document.body) focusField();
	requestAnimationFrame(() => keepFocus(framesLeft - 1));
};

// Panels render outside the row, so preserve the preview until they close.
let watchedPanel: Element | null = null;
let lastMouseDown: MouseEvent | null = null;

useEventListener(document, "mousedown", (event: MouseEvent) => (lastMouseDown = event), {
	capture: true,
});

// Row presses and prevented canvas-handle presses retain the preview.
const shouldKeepPreview = () => {
	const press = lastMouseDown;
	return !!press && (press.defaultPrevented || rowRef.value?.contains(press.target as Node));
};

const waitForPanelClose = (panel: Element) => {
	if (watchedPanel === panel) return;
	watchedPanel = panel;
	lastMouseDown = null;
	const waitForClose = () => {
		if (watchedPanel !== panel) return;
		if (panel.isConnected) return requestAnimationFrame(waitForClose);
		watchedPanel = null;
		claimingFocus = false;
		// Another control now owns the state.
		if (!props.isActive || hasFocus()) return;
		if (shouldKeepPreview()) return focusField();
		endPreview();
	};
	requestAnimationFrame(waitForClose);
};

// A focusout ends the preview unless a panel is closing.
const handleFocusOut = (event: FocusEvent) => {
	const relatedTarget = event.relatedTarget as Element | null;
	if (rowRef.value?.contains(relatedTarget)) return;
	const panel = relatedTarget?.closest?.(panelSelector) || document.querySelector(panelSelector);
	if (panel) return waitForPanelClose(panel);
	// Focus that goes nowhere is a panel opening or a dropdown closing. A press inside
	// the row keeps editing this state, so it is not the user leaving.
	if (!relatedTarget && (claimingFocus || shouldKeepPreview())) return;
	endPreview();
};

// An active canvas preview needs the field focused for row styling.
watch(
	() => props.isActive,
	(isActive) => {
		if (!isActive || hasFocus()) return;
		focusField();
		keepFocus(20);
	},
	{ immediate: true, flush: "post" },
);
</script>
