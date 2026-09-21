<template>
	<div class="flex items-center">
		<Button
			variant="solid"
			:size="size"
			:disabled="disabled"
			:label="publishButtonLabel"
			:icon="iconOnly ? 'lucide-cloud-upload' : undefined"
			:tooltip="iconOnly ? publishButtonLabel : undefined"
			@click="publish(Boolean(pageStore.activePage?.staging))"
			class="border-0"
			:class="{
				'rounded-br-none rounded-tr-none': showDropdown,
				'!rounded-full': iconOnly,
			}"
			:loading="publishing" />
		<Dropdown
			v-if="showDropdown"
			:options="[
				{
					label: __('Publish to Staging'),
					onClick: () => publish(true),
					condition: () => isDraft,
					icon: 'lucide-flask-conical',
				},
				{
					label: __('Go Live'),
					onClick: () => publish(false),
					condition: () => Boolean(pageStore.activePage?.staging),
					icon: 'lucide-rocket',
				},
				{
					label: __('Mark as Staging'),
					onClick: () => pageStore.markAsStaging(),
					condition: () => Boolean(pageStore.activePage?.published),
					icon: 'lucide-flask-conical',
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

const props = defineProps<{
	disabled?: boolean;
	size?: "sm" | "md";
	// drops the label and the menu: one round icon button, for the floating toolbar
	iconOnly?: boolean;
}>();

const pageStore = usePageStore();
const canvasStore = useCanvasStore();
const builderStore = useBuilderStore();

const publishing = ref(false);
const showDropdown = computed(() => {
	return !props.iconOnly && canvasStore.editingMode !== "fragment" && !pageStore.activePage?.is_template;
});

// the main button keeps a live or staging page where it is; the menu moves it
const isDraft = computed(() => !pageStore.activePage?.published && !pageStore.activePage?.staging);

const publishButtonLabel = computed(() => {
	const page = pageStore.activePage;
	return (page?.published || page?.staging) && page?.draft_blocks ? __("Publish Changes") : __("Publish");
});

const publish = (staging: boolean) => {
	publishing.value = true;
	pageStore.publishPage(true, staging).finally(() => (publishing.value = false));
};
</script>
