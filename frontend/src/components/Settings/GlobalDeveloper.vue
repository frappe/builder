<template>
	<div class="flex flex-col gap-5">
		<div class="flex justify-between gap-x-2.5">
			<div class="flex flex-col gap-1">
				<label class="w-fit shrink-0 text-p-base font-medium text-ink-gray-8">
					Execute Block Client Scripts in Editor
				</label>
				<div class="flex flex-col gap-2">
					<p class="text-p-sm text-ink-gray-7">
						Block Scripts are executed in a sandboxed environment. This may have limitations and might not
						perfectly replicate live site behavior. Executing untrusted scripts could be unsafe.
					</p>
				</div>
			</div>
			<Select
				class="h-max !w-[200px]"
				:modelValue="builderSettings.doc?.execute_block_scripts_in_editor"
				@update:modelValue="
					(value) => builderStore.updateBuilderSettings('execute_block_scripts_in_editor', value)
				"
				:options="[
					{ label: 'Don\'t Execute', value: 'Don\'t Execute' },
					{ label: 'Restricted', value: 'Restricted' },
					{ label: 'Unrestricted', value: 'Unrestricted' },
				]" />
		</div>
		<Switch
			size="sm"
			label="Prevent Click Emulation"
			description="Prevents click events from being emulated in the editor for blocks with Block Client Scripts."
			:modelValue="Boolean(builderSettings.doc?.restrict_click_handlers)"
			@update:modelValue="
				(val: Boolean) => {
					builderStore.updateBuilderSettings('restrict_click_handlers', val);
				}
			" />
		<div class="flex justify-between gap-x-2.5">
			<div class="flex flex-col gap-1">
				<label class="text-p-base font-medium text-ink-gray-8">Integrate with External Editor</label>
				<span v-if="lnaPermissionStatus === 'denied'" class="inline text-p-sm text-ink-gray-7">
					Follow this
					<a
						href="https://docs.frappe.io/builder/external-editor"
						target="_blank"
						class="text-ink-blue-6 text-p-sm underline"
						v-text="'guide'"></a>
					to enable local network access.
				</span>
				<p v-else class="text-p-sm text-ink-gray-7">
					Allow Builder to access your local network for integration with external editors like VS Code. Click
					<a
						href="https://docs.frappe.io/builder/external-editor"
						target="_blank"
						class="text-ink-blue-6 text-p-sm underline"
						v-text="'here'"></a>
					for more information.
				</p>
			</div>
			<div class="flex shrink-0 gap-3">
				<div v-if="['granted', 'denied', 'unsupported'].includes(lnaPermissionStatus)">
					<span v-if="lnaPermissionStatus === 'granted'" class="text-p-sm text-ink-green-3">
						Access Granted
					</span>
					<span v-else-if="lnaPermissionStatus === 'denied'" class="text-p-sm text-ink-red-4">
						Access Denied
					</span>
					<span v-else-if="lnaPermissionStatus === 'unsupported'" class="text-p-sm text-ink-gray-7">
						Unsupported
					</span>
				</div>
				<Button
					v-if="lnaPermissionStatus === 'prompt'"
					@click="requestLocalNetworkAccess"
					:loading="isRequestingAccess"
					variant="subtle">
					Request Access
				</Button>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import Switch from "@/components/Controls/Switch.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { useExternalEditor } from "@/composables/useExternalEditor";
import { Button, Select } from "frappe-ui";

const builderStore = useBuilderStore();
const { lnaPermissionStatus, isRequestingAccess, requestLocalNetworkAccess } = useExternalEditor();
</script>
