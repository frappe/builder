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
					class="w-full"
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
import { computed, onMounted, ref } from "vue";

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
	(e: "endPreview"): void;
}>();

const isTopLabel = computed(() => props.labelPlacement === "top");

const rowRef = ref<HTMLElement | null>(null);
const panelSelector = "[data-slot='content']";

// Menus and popovers opened from the row render outside it.
const isInRow = (target: EventTarget | null) =>
	target instanceof Element && (!!rowRef.value?.contains(target) || !!target.closest(panelSelector));

// Focus that goes nowhere is a menu or popover closing, not the user leaving.
const handleFocusOut = (event: FocusEvent) => {
	if (event.relatedTarget && !isInRow(event.relatedTarget)) emit("endPreview");
};

// Canvas handles edit the previewed state and prevent their press, but only after
// this capture listener runs, so read the press once its dispatch is done.
useEventListener(
	document,
	"mousedown",
	(event: MouseEvent) => {
		if (!props.isActive || isInRow(event.target)) return;
		setTimeout(() => event.defaultPrevented || emit("endPreview"));
	},
	{ capture: true },
);

// Escape out of a menu or popover means the user is done with this state. A swatch
// click also closes the popover, but it stays in the row, so it keeps the preview.
// This listens in the bubble phase like the popover, so both see the same Escape.
useEventListener(document, "keydown", (event: KeyboardEvent) => {
	if (event.key !== "Escape" || !props.isActive) return;
	if (document.querySelector(panelSelector)) emit("endPreview");
});

// A row added from the label menu is ready to type into. Rows that a press
// activates leave focus to that press, so a swatch does not open the field's list.
onMounted(() => {
	if (props.isActive) rowRef.value?.querySelector<HTMLElement>("input, select")?.focus();
});
</script>
