<template>
	<!-- Collects the capabilities granted at install, and nothing else. -->
	<section class="flex flex-col gap-3">
		<div>
			<h2 class="text-sm font-medium text-ink-gray-8">Grant these to {{ label }}</h2>
			<p class="pt-2 text-xs text-ink-gray-5">
				<template v-if="requested.length">
					Turn off what you do not want it to do. You can change this later in its details.
				</template>
				<template v-else>It asks for no capabilities.</template>
			</p>
		</div>

		<ExtensionCapabilities
			v-if="requested.length"
			:extension="extension"
			:label="label"
			:requested="requested"
			:doctype-grants="[]"
			v-model:granted="granted" />

		<div class="flex gap-2">
			<Button
				variant="solid"
				size="sm"
				icon-left="lucide-download"
				label="Install"
				@click="emit('install', granted)" />
			<Button variant="subtle" size="sm" label="Cancel" @click="emit('cancel')" />
		</div>
	</section>
</template>

<script setup lang="ts">
import ExtensionCapabilities from "@/components/LeftPanelTabs/Extensions/ExtensionCapabilities.vue";
import type { Capability } from "frappe-builder-extension-sdk/types";
import { Button } from "frappe-ui";
import { ref } from "vue";

const props = defineProps<{
	extension: string;
	label: string;
	requested: Capability[];
}>();

const emit = defineEmits<{
	install: [capabilities: Capability[]];
	cancel: [];
}>();

// the parent mounts this once for each attempt, so every capability starts on
const granted = ref<Capability[]>([...props.requested]);
</script>
