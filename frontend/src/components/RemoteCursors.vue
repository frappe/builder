<template>
	<div class="pointer-events-none fixed left-0 top-0 h-full w-full">
		<div
			v-for="[clientId, user] in remoteUsers"
			:key="clientId"
			v-show="user.cursor?.position?.x"
			class="pointer-events-none absolute left-0 top-0 transition-transform duration-150 ease-out will-change-transform"
			:style="{
				transform: `translate(${transformedPosition(user).x}px, ${transformedPosition(user).y}px)`,
				opacity: user.cursor?.position ? 1 : 0,
				transitionProperty: 'transform, opacity',
			}">
			<svg
				class="[filter:drop-shadow(0_2px_4px_rgba(0,0,0,0.1))_drop-shadow(0_1px_2px_rgba(0,0,0,0.2))]"
				width="24"
				height="24"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg">
				<path
					d="M5.65376 12.3673H5.46026L5.31717 12.4976L0.500002 16.8829L0.500002 1.19841L11.7841 12.3673H5.65376Z"
					:fill="user.userColor"
					stroke="white"
					stroke-width="1.5" />
			</svg>
			<div
				class="absolute left-3 top-5 flex items-center whitespace-nowrap rounded-md px-2 py-1 text-xs capitalize text-white shadow-xl"
				:style="{ backgroundColor: user.userColor }">
				{{ user.userName }}
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { UserAwareness } from "@/utils/yjsHelpers";
import { PropType } from "vue";

const props = defineProps({
	remoteUsers: {
		type: Map as PropType<Map<number, UserAwareness>>,
		required: true,
	},
	canvasProps: {
		type: Object as PropType<any>,
		required: true,
	},
	canvasElement: {
		type: Object as PropType<any>,
		required: false,
	},
});

const transformedPosition = (user: UserAwareness) => {
	if (!user.cursor?.position || !props.canvasElement) {
		return { x: -9999, y: -9999 };
	}

	const canvasEl = props.canvasElement as HTMLElement;
	if (!canvasEl) {
		return { x: -9999, y: -9999 };
	}

	const firstCanvas = canvasEl.querySelector('.canvas:not([style*="display: none"])') as HTMLElement;
	if (!firstCanvas) {
		return { x: -9999, y: -9999 };
	}

	const rect = firstCanvas.getBoundingClientRect();
	const scale = props.canvasProps.scale;

	// Cursor positions are stored as logical coordinates (scale-independent)
	// Convert to visual coordinates by multiplying by scale
	const visualX = user.cursor.position.x * scale;
	const visualY = user.cursor.position.y * scale;

	// Since RemoteCursors is position:absolute in canvasContainer,
	// we need viewport coordinates directly
	const x = rect.left + visualX;
	const y = rect.top + visualY;

	return { x, y };
};
</script>
