<template>
	<div>
		<BuilderButton
			@click="
				logs = [];
				brokenLinkScannerResource.fetch();
			"
			:loading-text="brokenLinkScannerResource.loading ? 'Scanning...' : 'Scan For Broken Links'"
			:loading="brokenLinkScannerResource.loading">
			Scan For Broken Links
		</BuilderButton>
		<div
			class="mt-2 flex max-h-[60vh] flex-col gap-1.5 overflow-auto rounded-md bg-surface-gray-1 p-2 text-sm text-ink-gray-5">
			<span v-for="log in logs">{{ log }}</span>
			<!-- live feed -->
		</div>
	</div>
</template>
<script setup lang="ts">
import useStore from "@/store";
import { createResource } from "frappe-ui";
import { onMounted, onUnmounted, Ref, ref } from "vue";

const store = useStore();
const logs = ref([]) as Ref<string[]>;

const brokenLinkScannerResource = createResource({
	method: "GET",
	url: "builder.api.scan_for_broken_links",
});

onMounted(() => {
	store.realtime.on("link_scan_status", (data: string) => {
		logs.value.push(data);
	});
});

onUnmounted(() => {
	store.realtime.off("link_scan_status");
});
</script>
