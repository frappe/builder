<template>
	<PageClientScriptManager :page="page" ref="pageClientScriptManager" />
</template>

<script setup lang="ts">
import PageClientScriptManager from "./PageClientScriptManager.vue";
import usePageStore from "@/stores/pageStore";
import type { BuilderPage } from "@/types/doctypes";
import { computed, ref } from "vue";

const props = defineProps<{
	parentDoctype: "Builder Page";
	parentName: string;
}>();

const pageStore = usePageStore();

const page = computed(() => {
	if (pageStore.activePage?.name === props.parentName) {
		return pageStore.activePage;
	}
	return { name: props.parentName } as BuilderPage;
});

const pageClientScriptManager = ref<InstanceType<typeof PageClientScriptManager> | null>(null);

defineExpose({
	get scriptEditor() {
		return pageClientScriptManager.value?.scriptEditor;
	},
});
</script>
