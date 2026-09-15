<template>
	<!-- Collects the capabilities granted at install, and nothing else. -->
	<Dialog :modelValue="open" size="sm" @update:modelValue="(value: boolean) => emit('update:open', value)">
		<template #body>
			<div class="bg-surface-modal p-5">
				<h3 class="text-lg-semibold text-ink-gray-9">Install {{ label }}?</h3>
				<p class="pt-2 text-p-sm text-ink-gray-6">
					<template v-if="requested.length">
						Turn off what you do not want it to do. You can change this later in its details.
					</template>
					<template v-else>It asks for no capabilities.</template>
				</p>

				<div v-if="requested.length" class="pt-4">
					<ExtensionCapabilities
						:extension="extension"
						:label="label"
						:requested="requested"
						:doctype-grants="[]"
						v-model:granted="granted" />
				</div>

				<div class="flex justify-end gap-2 pt-4">
					<Button variant="subtle" label="Cancel" @click="emit('update:open', false)" />
					<Button variant="solid" label="Confirm" @click="emit('install', granted)" />
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import ExtensionCapabilities from "@/components/LeftPanelTabs/Extensions/ExtensionCapabilities.vue";
import type { Capability } from "frappe-builder-extension-sdk/types";
import { Button } from "frappe-ui";
import { ref, watch } from "vue";

const props = defineProps<{
	open: boolean;
	extension: string;
	label: string;
	requested: Capability[];
}>();

const emit = defineEmits<{
	"update:open": [open: boolean];
	install: [capabilities: Capability[]];
}>();

const granted = ref<Capability[]>([]);

// every capability starts on each time the dialog opens, so a choice from an
// earlier attempt does not carry over
watch(
	() => props.open,
	(open) => open && (granted.value = [...props.requested]),
	{ immediate: true },
);
</script>
