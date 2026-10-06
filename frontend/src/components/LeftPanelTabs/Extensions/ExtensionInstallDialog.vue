<template>
	<!-- Gets the permissions to grant at install, and nothing else. -->
	<Dialog :modelValue="open" size="sm" @update:modelValue="(value: boolean) => emit('update:open', value)">
		<template #body>
			<div class="bg-surface-elevation-2 p-5">
				<h3 class="text-md-semibold text-ink-gray-9">Install {{ label }}?</h3>
				<p class="pt-2 text-p-sm text-ink-gray-6">
					<template v-if="requested.length">
						Turn off what you do not want it to do. You can change this later in its details.
					</template>
					<template v-else>It asks for no permissions.</template>
				</p>

				<div v-if="requested.length" class="pt-4">
					<ExtensionPermissions
						:extension="extension"
						:label="label"
						:requested="requested"
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
import ExtensionPermissions from "@/components/LeftPanelTabs/Extensions/ExtensionPermissions.vue";
import type { Permission } from "frappe-builder-extension-sdk/types";
import { Button } from "frappe-ui";
import { ref, watch } from "vue";

const props = defineProps<{
	open: boolean;
	extension: string;
	label: string;
	requested: Permission[];
}>();

const emit = defineEmits<{
	"update:open": [open: boolean];
	install: [permissions: Permission[]];
}>();

const granted = ref<Permission[]>([]);

// all permissions start on each time the dialog opens. So a choice from an
// earlier try does not stay
watch(
	() => props.open,
	(open) => open && (granted.value = [...props.requested]),
	{ immediate: true },
);
</script>
