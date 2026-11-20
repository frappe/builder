<template>
	<!-- a provider's settings, under its row of the providers list. Off, its key and models are hidden,
	     as they cannot be used until it is on. Disconnect stays at the bottom either way -->
	<div class="flex flex-col gap-5 py-2">
		<template v-if="provider.enabled">
			<ProviderKey :provider="provider" @changed="emit('changed')" />
			<ProviderModels :provider="provider.name" @changed="emit('changed')" />
		</template>
		<!-- asked here, not in a dialog over Settings: the first click arms it, and a second click within a
		     few seconds disconnects -->
		<Button
			class="w-full"
			theme="red"
			icon-left="lucide-unplug"
			:variant="isArmed ? 'solid' : 'outline'"
			:label="isArmed ? __('Click again to confirm') : __('Disconnect Provider')"
			:loading="isDisconnecting"
			@click="clickDisconnect" />
	</div>
</template>

<script setup lang="ts">
import ProviderKey from "@/components/Settings/AI/ProviderKey.vue";
import ProviderModels from "@/components/Settings/AI/ProviderModels.vue";
import { disconnectProvider } from "@/data/aiModels";
import { __ } from "@/translation";
import type { BuilderAIProvider } from "@/types/doctypes";
import { Button, toast } from "frappe-ui";
import { onBeforeUnmount, ref } from "vue";

const props = defineProps<{ provider: BuilderAIProvider }>();
const emit = defineEmits<{ changed: [] }>();

const ARMED_MS = 4000;
const isArmed = ref(false);
const isDisconnecting = ref(false);
let timer: number | undefined;
onBeforeUnmount(() => window.clearTimeout(timer));

const clickDisconnect = () => {
	window.clearTimeout(timer);
	if (isArmed.value) {
		isArmed.value = false;
		return disconnect();
	}
	isArmed.value = true;
	timer = window.setTimeout(() => (isArmed.value = false), ARMED_MS);
};

const disconnect = async () => {
	isDisconnecting.value = true;
	try {
		await disconnectProvider(props.provider.name);
		toast.success(__("{0} disconnected", [props.provider.provider_name]));
		emit("changed");
	} finally {
		isDisconnecting.value = false;
	}
};
</script>
