<template>
	<Tooltip :text="status.tooltip" :hoverDelay="500">
		<span class="size-1.5 shrink-0 rounded-full" :class="status.dotClass" />
	</Tooltip>
</template>
<script setup lang="ts">
import { BuilderPage } from "@/types/doctypes";
import { getPageStatus } from "@/utils/pageStatus";
import { Tooltip } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{
	page: BuilderPage;
}>();

const status = computed(() => getPageStatus(props.page));
</script>
