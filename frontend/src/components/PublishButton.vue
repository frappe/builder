<template>
	<div class="flex items-center">
		<Button
			variant="solid"
			:disabled="disabled"
			@click="publish(false)"
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
					label: __('Publish to Staging'),
					onClick: () => publish(true),
					condition: () => canPublishToStaging,
					icon: 'lucide-flask-conical',
				},
				{
					label: __('Version History'),
					onClick: () => {
						builderStore.showRightPanel = true;
						builderStore.showVersionHistory = true;
					},
					icon: 'lucide-history',
				},
				{
					label: __('Unpublish'),
					onClick: () => pageStore.unpublishPage(),
					condition: () => Boolean(pageStore.activePage?.published || pageStore.activePage?.staging),
					icon: 'lucide-cloud-off',
				},
			]"
			size="sm"
			class="flex-1 [&>div>div>div]:w-full"
			placement="right">
			<Button
				variant="solid"
				:disabled="Boolean(pageStore.activePage?.is_template) || builderStore.readOnlyMode"
				icon="lucide-chevron-down"
				class="!w-6 justify-start rounded-bl-none rounded-tl-none border-0 pr-0 text-xs"></Button>
		</Dropdown>
	</div>
</template>
<script lang="ts" setup>
import { __ } from "@/translation";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { Dropdown } from "frappe-ui";
import { computed, ref } from "vue";

defineProps<{
	disabled?: boolean;
}>();

const pageStore = usePageStore();
const canvasStore = useCanvasStore();
const builderStore = useBuilderStore();

const publishing = ref(false);
const showDropdown = computed(() => {
	return canvasStore.editingMode !== "fragment" && !pageStore.activePage?.is_template;
});

// a live page leaves staging behind; a staging page needs new changes to push there
const canPublishToStaging = computed(() => {
	const page = pageStore.activePage;
	if (page?.published) {
		return false;
	}
	return !page?.staging || Boolean(page?.draft_blocks);
});

const publishButtonLabel = computed(() => {
	const page = pageStore.activePage;
	if (page?.staging) {
		return __("Go Live");
	}
	return page?.published && page?.draft_blocks ? __("Publish Changes") : __("Publish");
});

const publish = (staging: boolean) => {
	publishing.value = true;
	pageStore.publishPage(true, staging).finally(() => (publishing.value = false));
};
</script>
