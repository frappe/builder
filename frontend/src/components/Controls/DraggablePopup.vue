<template>
	<div class="relative" v-if="modelValue">
		<div class="fixed z-50" @mousedown.stop>
			<div
				ref="popoverContent"
				class="fixed flex flex-col gap-1 overflow-hidden rounded-lg border-gray-700 bg-surface-white shadow-lg"
				:style="{
					width: width + 'px',
					minHeight: height + 'px',
					left: popupLeft + 'px',
					top: popupTop + 'px',
				}">
				<div
					class="text-ink-grainset-y-9 flex cursor-grab select-none items-center justify-between px-3 py-1 pr-1 text-sm"
					:class="{ 'cursor-grabbing': isDragging }"
					@mousedown="startDrag">
					<slot name="header">Search Block</slot>
					<Button @click="togglePopup" icon="x" variant="ghost"></Button>
				</div>
				<div class="px-3 pb-3">
					<slot name="content"></slot>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, Ref, ref } from "vue";

const props = withDefaults(
	defineProps<{
		modelValue: boolean;
		width?: number;
		height?: number;
		placement?: "top" | "bottom" | "left" | "right";
		clickOutsideToClose?: boolean;
	}>(),
	{
		width: 300,
		height: 200,
		clickOutsideToClose: false,
	},
);

const emit = defineEmits(["update:modelValue"]);

const popoverContent = ref(null) as Ref<HTMLElement | null>;
const popupLeft = ref(1500);
const popupTop = ref(100);
let isDragging = ref(false);

let startX = 0;
let startY = 0;
let startLeft = 0;
let startTop = 0;

const togglePopup = () => {
	emit("update:modelValue", !props.modelValue);
	if (props.modelValue) {
		console.log("open");
		// nextTick(() => {
		// 	popupLeft.value = 0;
		// 	popupTop.value = 0;
		// });
	}
};

const startDrag = (event: MouseEvent) => {
	isDragging.value = true;
	startX = event.clientX;
	startY = event.clientY;
	startLeft = popupLeft.value;
	startTop = popupTop.value;

	document.addEventListener("mousemove", drag);
	document.addEventListener("mouseup", stopDrag, { once: true });
};

const drag = (event: MouseEvent) => {
	if (!isDragging.value) return;
	const dx = event.clientX - startX;
	const dy = event.clientY - startY;
	popupLeft.value = startLeft + dx;
	popupTop.value = startTop + dy;
};

const stopDrag = () => {
	isDragging.value = false;
	document.removeEventListener("mousemove", drag);
};

const handleClickOutside = (event: Event) => {
	if (props.modelValue && popoverContent.value && !popoverContent.value.contains(event.target as Node)) {
		emit("update:modelValue", false);
	}
};

onMounted(() => {
	if (props.clickOutsideToClose) {
		document.addEventListener("click", handleClickOutside);
	}
});

onUnmounted(() => {
	if (props.clickOutsideToClose) {
		document.removeEventListener("click", handleClickOutside);
	}
});
</script>
