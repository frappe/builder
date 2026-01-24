<template>
	<div class="remote-cursors">
		<div
			v-for="[clientId, user] in remoteUsers"
			:key="clientId"
			class="remote-cursor"
			:style="{
				transform:
					user.cursor?.position?.x !== undefined
						? `translate(${user.cursor.position.x}px, ${user.cursor.position.y}px)`
						: 'translate(-9999px, -9999px)',
				opacity: user.cursor?.position ? 1 : 0,
			}">
			<!-- Wrapper with counter-scale to keep visual size consistent -->
			<div
				class="cursor-visual"
				:style="{ transform: `scale(${1 / canvasScale})`, transformOrigin: 'top left' }">
				<svg
					class="cursor-icon"
					width="24"
					height="24"
					viewBox="0 0 24 24"
					xmlns="http://www.w3.org/2000/svg">
					<!-- Cursor arrow shape -->
					<path
						d="M5.65376 12.3673H5.46026L5.31717 12.4976L0.500002 16.8829L0.500002 1.19841L11.7841 12.3673H5.65376Z"
						:fill="user.userColor"
						stroke="white"
						stroke-width="1.5" />
				</svg>
				<div class="cursor-label" :style="{ backgroundColor: user.userColor }">
					{{ user.userName }}
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { UserAwareness } from "@/utils/yjsHelpers";
import { PropType } from "vue";

defineProps({
	remoteUsers: {
		type: Map as PropType<Map<number, UserAwareness>>,
		required: true,
	},
	canvasScale: {
		type: Number,
		required: true,
	},
});
</script>

<style scoped>
.remote-cursors {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	pointer-events: none;
	z-index: 9999;
	overflow: visible;
}

.remote-cursor {
	position: absolute;
	pointer-events: none;
	transition:
		transform 0.15s cubic-bezier(0.4, 0, 0.2, 1),
		opacity 0.2s ease;
	will-change: transform;
	left: 0;
	top: 0;
}

.cursor-icon {
	filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3)) drop-shadow(0 1px 2px rgba(0, 0, 0, 0.2));
}

.cursor-label {
	position: absolute;
	top: 20px;
	left: 12px;
	padding: 3px 8px;
	border-radius: 6px;
	color: white;
	font-size: 11px;
	font-weight: 600;
	white-space: nowrap;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
	letter-spacing: 0.3px;
	line-height: 1.2;
}
</style>
