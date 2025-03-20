<template>
	<div class="flex items-center">
		<BuilderButton
			variant="solid"
			:disabled="canvasStore.editingMode === 'fragment'"
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
		</BuilderButton>
		<Dropdown
			v-show="showDropdown"
			:options="[
				{
					label: 'Revert Changes',
					onClick: () => pageStore.revertChanges(),
					condition: () => pageStore.activePage?.draft_blocks,
					icon: 'refresh-cw',
				},
				{
					label: 'Unpublish',
					onClick: () => pageStore.unpublishPage(),
					condition: () => Boolean(pageStore.activePage?.published),
					icon: 'cloud-off',
				},
			]"
			size="sm"
			class="flex-1 [&>div>div>div]:w-full"
			placement="right">
			<template v-slot="{ open }">
				<BuilderButton
					variant="solid"
					@click="open"
					:disabled="Boolean(pageStore.activePage?.is_template)"
					icon="chevron-down"
					class="!w-6 justify-start rounded-bl-none rounded-tl-none border-0 pr-0 text-xs"></BuilderButton>
			</template>
		</Dropdown>
	</div>
</template>
<script lang="ts" setup>
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { Dropdown } from "frappe-ui";
import { computed, ref } from "vue";

const pageStore = usePageStore();
const canvasStore = useCanvasStore();

const publishing = ref(false);
const showDropdown = computed(() => {
	return Boolean(pageStore.activePage?.published) && canvasStore.editingMode !== "fragment";
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
