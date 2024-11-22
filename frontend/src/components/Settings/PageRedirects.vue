<template>
	<div>
		<div class="flex flex-col justify-between gap-5">
			<div class="flex items-end gap-4">
				<BuilderInput type="text" label="From URL" v-model="redirectMap.from" :hideClearButton="true" />
				<FeatherIcon name="arrow-right" class="mb-1 size-4 text-ink-gray-5" />
				<BuilderInput type="text" label="To URL" v-model="redirectMap.to" :hideClearButton="true" />
			</div>
			<div class="flex cursor-pointer items-center gap-2 text-base text-ink-gray-5" @click="addRedirect">
				<FeatherIcon name="plus" class="size-4" />
				<span>Add Redirect</span>
			</div>
			<div class="flex flex-col justify-between gap-3">
				<ListView
					class="h-[150px]"
					:columns="[
						{
							label: 'From',
							key: 'from',
						},
						{
							label: 'To',
							key: 'to',
						},
					]"
					rowKey="from"
					:rows="rows" />
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import routeRedirects from "@/data/routeRedirects";
import { ListView } from "frappe-ui";
import { computed, ref } from "vue";

const redirectMap = ref({
	from: "",
	to: "",
});

const rows = computed(() => {
	return routeRedirects.data.map((redirect: { source: string; target: string }) => {
		return {
			from: redirect.source,
			to: redirect.target,
		};
	});
});

const addRedirect = () => {
	routeRedirects.insert
		.submit({
			source: redirectMap.value.from,
			target: redirectMap.value.to,
			parenttype: "Website Settings",
			parentfield: "route_redirects",
			parent: "Website Settings",
		})
		.then(() => {
			redirectMap.value = { from: "", to: "" };
		});
};
</script>
