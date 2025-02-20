<template>
	<div class="flex items-center">
		<BuilderButton
			variant="solid"
			:disabled="store.editingMode === 'fragment'"
			@click="
				() => {
					publishing = true;
					store.publishPage().finally(() => (publishing = false));
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
					onClick: () => store.revertChanges(),
					condition: () => store.activePage?.draft_blocks,
					icon: 'refresh-cw',
				},
				{
					label: 'Unpublish',
					onClick: () => store.unpublishPage(),
					condition: () => store.activePage?.published,
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
					:disabled="Boolean(store.activePage?.is_template)"
					icon="chevron-down"
					class="!w-6 justify-start rounded-bl-none rounded-tl-none border-0 pr-0 text-xs"></BuilderButton>
			</template>
		</Dropdown>
	</div>
</template>
<script lang="ts" setup>
import useStore from "@/store";
import { Dropdown } from "frappe-ui";
import { computed, ref } from "vue";

const store = useStore();
const publishing = ref(false);
const showDropdown = computed(() => {
	return Boolean(store.activePage?.published) && store.editingMode !== "fragment";
});

const publishButtonLabel = computed(() => {
	if ((store.activePage?.draft_blocks && !store.activePage?.published) || !store.activePage?.draft_blocks) {
		return "Publish";
	} else {
		return "Publish Changes";
	}
});
</script>
