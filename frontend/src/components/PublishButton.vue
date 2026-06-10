<template>
	<div class="flex items-center">
		<Button
			variant="solid"
			:disabled="disabled"
			@click="
				() => {
					publishing = true;
					pageStore.publishPage().finally(() => (publishing = false));
				}
			"
			class="border-0"
			:class="{
				'rounded-br-none rounded-tr-none': showDropdown,
			}"
			:loading="publishing">
			{{ publishButtonLabel }}
		</Button>
		<Dropdown
			v-if="showDropdown"
			:options="[
				{
					label: 'Version History',
					onClick: () => (showVersionHistory = true),
					icon: 'lucide-history',
				},
				{
					label: 'Revert Changes',
					onClick: () => pageStore.revertChanges(),
					condition: () => pageStore.activePage?.draft_blocks,
					icon: 'lucide-refresh-cw',
				},
				{
					label: 'Unpublish',
					onClick: () => pageStore.unpublishPage(),
					condition: () => Boolean(pageStore.activePage?.published),
					icon: 'lucide-cloud-off',
				},
			]"
			size="sm"
			class="flex-1 [&>div>div>div]:w-full"
			placement="right">
			<template v-slot="{ open }">
				<Button
					variant="solid"
					@click="open"
					:disabled="Boolean(pageStore.activePage?.is_template)"
					icon="lucide-chevron-down"
					class="!w-6 justify-start rounded-bl-none rounded-tl-none border-0 pr-0 text-xs"></Button>
			</template>
		</Dropdown>
		<VersionHistory v-model="showVersionHistory" />
	</div>
</template>
<script lang="ts" setup>
import VersionHistory from "@/components/VersionHistory.vue";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { Dropdown } from "frappe-ui";
import { computed, ref } from "vue";

defineProps<{
	disabled?: boolean;
}>();

const pageStore = usePageStore();
const canvasStore = useCanvasStore();

const publishing = ref(false);
const showVersionHistory = ref(false);
const showDropdown = computed(() => {
	// Always available (so Version History is reachable); individual items
	// (Revert / Unpublish) remain gated by their own `condition`.
	return canvasStore.editingMode !== "fragment" && !pageStore.activePage?.is_template;
});

const publishButtonLabel = computed(() => {
	if (
		(pageStore.activePage?.draft_blocks && !pageStore.activePage?.published) ||
		!pageStore.activePage?.draft_blocks
	) {
		return "Publish";
	} else {
		return "Publish Changes";
	}
});
</script>
