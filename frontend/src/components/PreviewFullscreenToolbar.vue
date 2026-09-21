<template>
	<div
		ref="toolbar"
		:style="style"
		class="fixed z-20 flex touch-none select-none items-center gap-0.5 rounded-full border border-outline-gray-2 bg-surface-base p-1 shadow-xl">
		<span
			ref="dragHandle"
			class="lucide-grip-vertical size-4 shrink-0 text-ink-gray-4 hover:text-ink-gray-7"
			:class="isDragging ? 'cursor-grabbing' : 'cursor-grab'"
			aria-hidden="true" />
		<Button
			v-for="action in actions"
			:key="action.label"
			variant="ghost"
			size="sm"
			class="!rounded-full"
			:icon="action.icon"
			:label="action.label"
			:tooltip="action.label"
			@click="action.onClick" />
		<PublishButton size="sm" iconOnly />
	</div>
</template>
<script lang="ts" setup>
import PublishButton from "@/components/PublishButton.vue";
import { placeWithinBounds } from "@/utils/floatingPosition";
import { Position, StorageSerializers, useDraggable, useEventListener, useStorage } from "@vueuse/core";
import { Button } from "frappe-ui";
import { ref, watch } from "vue";

const props = defineProps<{
	container: HTMLElement | null;
	actions: { icon: string; label: string; onClick: () => void }[];
}>();

const toolbar = ref<HTMLElement | null>(null);
const dragHandle = ref<HTMLElement | null>(null);
const savedPosition = useStorage<Position | null>("previewFullscreenToolbarPosition", null, localStorage, {
	serializer: StorageSerializers.object,
});

const { x, y, style, isDragging } = useDraggable(toolbar, {
	handle: dragHandle,
	containerElement: () => props.container,
	initialValue: savedPosition.value || { x: 0, y: 0 },
	// capture the pointer, else the preview iframe swallows the move events
	onStart: (_, event) => {
		dragHandle.value?.setPointerCapture(event.pointerId);
	},
	onEnd: (position) => (savedPosition.value = { ...position }),
});

const placeInsideContainer = () => {
	const bounds = props.container?.getBoundingClientRect();
	const size = toolbar.value?.getBoundingClientRect();
	if (!bounds || !size) return;
	const position = placeWithinBounds(bounds, size, savedPosition.value);
	x.value = position.x;
	y.value = position.y;
};

watch(() => props.container, placeInsideContainer, { immediate: true, flush: "post" });
useEventListener(window, "resize", placeInsideContainer);
</script>
