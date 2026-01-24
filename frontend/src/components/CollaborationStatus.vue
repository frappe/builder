<template>
	<div v-if="isEnabled" class="collaboration-status" :class="{ connected: isConnected, synced: isSynced }">
		<div class="status-indicator">
			<div class="status-dot" :class="{ connected: isConnected, syncing: isConnected && !isSynced }"></div>
			<span class="status-text">
				{{ statusText }}
			</span>
		</div>
		<div v-if="remoteUsers.size > 0" class="active-users">
			<div class="user-count">{{ remoteUsers.size }}</div>
			<div class="user-list">
				<div
					v-for="[clientId, user] in remoteUsers"
					:key="clientId"
					class="user-badge"
					:style="{ backgroundColor: user.userColor }"
					:title="user.userName">
					{{ getUserInitials(user.userName) }}
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { UserAwareness } from "@/utils/yjsHelpers";
import { computed, PropType } from "vue";

const props = defineProps({
	isEnabled: {
		type: Boolean,
		required: true,
	},
	isConnected: {
		type: Boolean,
		required: true,
	},
	isSynced: {
		type: Boolean,
		required: true,
	},
	remoteUsers: {
		type: Map as PropType<Map<number, UserAwareness>>,
		required: true,
	},
});

const statusText = computed(() => {
	if (!props.isEnabled) return "Collaborative editing disabled";
	if (!props.isConnected) return "Connecting...";
	if (!props.isSynced) return "Syncing...";
	return "Connected";
});

function getUserInitials(name: string): string {
	const parts = name.split(/[\s@._-]+/).filter(Boolean);
	if (parts.length === 0) return "?";
	if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
	return (parts[0][0] + parts[1][0]).toUpperCase();
}
</script>

<style scoped>
.collaboration-status {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 4px 12px;
	background: #f8f9fa;
	border-radius: 8px;
	font-size: 12px;
}

.status-indicator {
	display: flex;
	align-items: center;
	gap: 6px;
}

.status-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	background: #9ca3af;
	transition: background 0.3s;
}

.status-dot.connected {
	background: #10b981;
}

.status-dot.syncing {
	background: #f59e0b;
	animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
	0%,
	100% {
		opacity: 1;
	}
	50% {
		opacity: 0.5;
	}
}

.status-text {
	color: #6b7280;
	font-weight: 500;
}

.active-users {
	display: flex;
	align-items: center;
	gap: 8px;
}

.user-count {
	color: #6b7280;
	font-weight: 600;
}

.user-list {
	display: flex;
	gap: 4px;
}

.user-badge {
	width: 24px;
	height: 24px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	color: white;
	font-size: 10px;
	font-weight: 600;
	border: 2px solid white;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	cursor: pointer;
	transition: transform 0.2s;
}

.user-badge:hover {
	transform: scale(1.1);
}
</style>
