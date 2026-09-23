<template>
	<teleport to="#popovers">
		<div class="relative" ref="popover">
			<!-- fixed makes this a stacking context, so the popup clears panel chrome from here -->
			<div class="fixed z-50" @mousedown.stop>
				<div
					ref="popoverContent"
					class="fixed flex flex-col gap-1 overflow-hidden rounded-6 border border-outline-gray-2 bg-surface-base shadow-2xl"
					:class="{ 'transition-all duration-300 ease-in-out': isTransitioning }"
					:style="{
						width: popupWidth + 'px',
						minHeight: popupHeight + 'px',
						height: resizable ? popupHeight + 'px' : '',
						left: popupLeft + 'px',
						top: popupTop + 'px',
					}">
					<div
						ref="headerRef"
						class="flex cursor-grab select-none items-center justify-between px-4 py-2 pr-3 text-sm text-ink-gray-9"
						:class="{ 'cursor-grabbing': isDragging }"
						@mousedown="startDrag">
						<slot name="header"></slot>
						<div class="flex items-center gap-2">
							<Button
								v-if="actionLabel && actionHandler"
								@click="actionHandler"
								:label="actionLabel"
								variant="solid"></Button>
							<Button @click="togglePopup" icon="lucide-x" variant="subtle"></Button>
						</div>
					</div>
					<div class="min-h-0 flex-1 px-3 pb-3">
						<slot name="content"></slot>
					</div>
					<!-- grab corners: the popup owns its size, so the handles live with the chrome -->
					<template v-if="resizable">
						<div
							class="absolute bottom-0 left-0 size-4 cursor-sw-resize"
							@mousedown.stop="startResize($event, 'left')" />
						<div
							class="absolute bottom-0 right-0 size-4 cursor-se-resize"
							@mousedown.stop="startResize($event, 'right')" />
					</template>
				</div>
			</div>
		</div>
	</teleport>
</template>

<script setup lang="ts">
import { useEventListener } from "@vueuse/core";
import { nextTick, onMounted, Ref, ref } from "vue";

const popover = ref(null) as Ref<HTMLElement | null>;

const props = withDefaults(
	defineProps<{
		modelValue: boolean;
		width?: number;
		height?: number;
		placement?:
			| "top-left"
			| "top-right"
			| "bottom-left"
			| "bottom-right"
			| "center"
			| "top-middle"
			| "bottom-middle"
			| "middle-left"
			| "middle-right";
		placementOffset?: number;
		placementOffsetLeft?: number;
		placementOffsetTop?: number;
		clickOutsideToClose?: boolean;
		container?: HTMLElement | null;
		actionLabel?: string;
		actionHandler?: () => void;
		resizable?: boolean;
	}>(),
	{
		width: 300,
		height: 200,
		clickOutsideToClose: false,
		resizable: false,
		placement: "top-left",
		placementOffset: 0,
	},
);

// "dragging" and "resizing" let a consumer whose content swallows the pointer,
// such as an iframe, stop taking events until the gesture ends
const emit = defineEmits(["update:modelValue", "dragging", "resizing"]);

const MIN_WIDTH = 240;
const MIN_HEIGHT = 180;
const VIEWPORT_PADDING = 10;

const popoverContent = ref(null) as Ref<HTMLElement | null>;
const headerRef = ref<HTMLElement | null>(null);
const popupLeft = ref(1500);
const popupTop = ref(100);
// The popup owns its size from here on: `width` and `height` only seed it.
const popupWidth = ref(props.width);
const popupHeight = ref(props.height);
const isDragging = ref(false);
const resizingCorner = ref<"left" | "right" | null>(null);
const isTransitioning = ref(false);

let startX = 0;
let startY = 0;
let startLeft = 0;
let startTop = 0;
let startWidth = 0;
let startHeight = 0;

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

onMounted(async () => {
	await nextTick();
	setPosition();
});

const togglePopup = () => {
	emit("update:modelValue", !props.modelValue);
};

const startDrag = (event: MouseEvent) => {
	isDragging.value = true;
	emit("dragging", true);
	startX = event.clientX;
	startY = event.clientY;
	startLeft = popupLeft.value;
	startTop = popupTop.value;

	document.addEventListener("mousemove", drag);
	document.addEventListener("mouseup", stopDrag, { once: true });
};

const drag = (event: MouseEvent) => {
	if (!isDragging.value || !popoverContent.value || !headerRef.value) return;

	const dx = event.clientX - startX;
	const dy = event.clientY - startY;

	popupTop.value = startTop + dy;
	popupLeft.value = startLeft + dx;
};

const stopDrag = () => {
	isDragging.value = false;
	emit("dragging", false);
	document.removeEventListener("mousemove", drag);

	if (popoverContent.value && headerRef.value) {
		const headerHeight = headerRef.value.offsetHeight;

		const maxTop = window.innerHeight - headerHeight - VIEWPORT_PADDING;
		const maxLeft = window.innerWidth - popupWidth.value - VIEWPORT_PADDING;

		const clampedTop = clamp(popupTop.value, VIEWPORT_PADDING, maxTop);
		const clampedLeft = clamp(popupLeft.value, VIEWPORT_PADDING, maxLeft);

		// transition if position needs adjustment
		if (clampedTop !== popupTop.value || clampedLeft !== popupLeft.value) {
			isTransitioning.value = true;
			popupTop.value = clampedTop;
			popupLeft.value = clampedLeft;

			setTimeout(() => {
				isTransitioning.value = false;
			}, 300);
		}
	}
};

const startResize = (event: MouseEvent, corner: "left" | "right") => {
	resizingCorner.value = corner;
	emit("resizing", true);
	startX = event.clientX;
	startY = event.clientY;
	startLeft = popupLeft.value;
	startWidth = popupWidth.value;
	startHeight = popupHeight.value;

	document.addEventListener("mousemove", resize);
	document.addEventListener("mouseup", stopResize, { once: true });
};

/** Clamped as it moves, so the corner never leaves the viewport. */
const resize = (event: MouseEvent) => {
	if (!resizingCorner.value) return;

	const dx = event.clientX - startX;
	const maxHeight = window.innerHeight - popupTop.value - VIEWPORT_PADDING;
	popupHeight.value = clamp(startHeight + event.clientY - startY, MIN_HEIGHT, maxHeight);

	if (resizingCorner.value === "right") {
		popupWidth.value = clamp(startWidth + dx, MIN_WIDTH, window.innerWidth - startLeft - VIEWPORT_PADDING);
		return;
	}

	// the right edge stays put, so the left edge follows the width
	popupWidth.value = clamp(startWidth - dx, MIN_WIDTH, startLeft + startWidth - VIEWPORT_PADDING);
	popupLeft.value = startLeft + startWidth - popupWidth.value;
};

const stopResize = () => {
	resizingCorner.value = null;
	emit("resizing", false);
	document.removeEventListener("mousemove", resize);
};

const handleClickOutside = (event: Event) => {
	if (props.modelValue && popoverContent.value && !popoverContent.value.contains(event.target as Node)) {
		emit("update:modelValue", false);
	}
};

const setPosition = () => {
	if (props.container) {
		const { left, top, right, bottom } = props.container.getBoundingClientRect();
		const horizontalOffset = props.placementOffsetLeft ?? props.placementOffset;
		const verticalOffset = props.placementOffsetTop ?? props.placementOffset;
		switch (props.placement) {
			case "top-left":
				popupLeft.value = left + horizontalOffset;
				popupTop.value = top + verticalOffset;
				break;
			case "top-right":
				popupLeft.value = right - popupWidth.value - horizontalOffset;
				popupTop.value = top + verticalOffset;
				break;
			case "bottom-left":
				popupLeft.value = left + horizontalOffset;
				popupTop.value = bottom - popupHeight.value - verticalOffset;
				break;
			case "bottom-right":
				popupLeft.value = right - popupWidth.value - horizontalOffset;
				popupTop.value = bottom - popupHeight.value - verticalOffset;
				break;
			case "center":
				popupLeft.value = left + (right - left) / 2 - popupWidth.value / 2;
				popupTop.value = top + (bottom - top) / 2 - popupHeight.value / 2;
				break;
			case "top-middle":
				popupLeft.value = left + (right - left) / 2 - popupWidth.value / 2;
				popupTop.value = top + verticalOffset;
				break;
			case "bottom-middle":
				popupLeft.value = left + (right - left) / 2 - popupWidth.value / 2;
				popupTop.value = bottom - popupHeight.value - verticalOffset;
				break;
			case "middle-left":
				popupLeft.value = left + horizontalOffset;
				popupTop.value = top + (bottom - top) / 2 - popupHeight.value / 2;
				break;
			case "middle-right":
				popupLeft.value = right - popupWidth.value - horizontalOffset;
				popupTop.value = top + (bottom - top) / 2 - popupHeight.value / 2;
				break;
		}
	} else {
		const { innerWidth, innerHeight } = window;
		popupLeft.value = innerWidth / 2 - popupWidth.value / 2;
		popupTop.value = innerHeight / 2 - popupHeight.value / 2;
	}
};

if (props.clickOutsideToClose) {
	useEventListener(document, "click", handleClickOutside, {
		capture: true,
		passive: true,
	});
}

useEventListener(window, "resize", setPosition);
</script>
