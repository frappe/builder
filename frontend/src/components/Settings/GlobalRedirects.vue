<template>
	<div class="overflow-hidden">
		<div class="mb-5">
			<div class="flex gap-4 px-[2px] py-2">
				<BuilderInput
					type="text"
					v-model="redirectMap.from"
					:hideClearButton="true"
					required
					placeholder="From" />
				<BuilderInput
					type="text"
					v-model="redirectMap.to"
					:hideClearButton="true"
					required
					placeholder="To" />
			</div>
			<button
				class="flex w-fit cursor-pointer items-center gap-2 px-[2px] py-1 text-base text-ink-gray-5"
				@click="addRedirect">
				<FeatherIcon name="plus" class="size-4" />
				<span>Add Redirect</span>
			</button>
		</div>
		<div class="h-full overflow-hidden text-sm">
			<div
				class="sticky top-0 flex rounded-t-md border-b border-outline-gray-1 bg-surface-gray-1 py-2 text-ink-gray-5">
				<span class="w-1/2 pl-2">From URL</span>
				<span class="w-1/2 pl-2">To URL</span>
			</div>
			<div class="h-[calc(100%-115px)] overflow-y-auto">
				<div
					class="group flex items-center rounded-sm border-b border-outline-gray-1 px-2 py-2 text-sm text-ink-gray-7 hover:bg-surface-gray-2"
					v-for="row in rows">
					<code class="w-1/2 truncate">{{ row.from }}</code>
					<code class="ml-3 w-1/2 truncate pl-2">{{ row.to }}</code>
					<FeatherIcon
						name="trash"
						class="size-3 cursor-pointer text-ink-gray-5"
						@click="deleteRedirect(row.id)" />
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import routeRedirects from "@/data/routeRedirects";
import { computed, onMounted, ref } from "vue";

const redirectMap = ref({
	from: "",
	to: "",
});

onMounted(() => {
	routeRedirects.fetch();
});

const rows = computed(() => {
	return (routeRedirects.data || []).map((redirect: { source: string; target: string; name: string }) => {
		return {
			from: redirect.source,
			to: redirect.target,
			id: redirect.name,
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

const deleteRedirect = (id: string) => {
	routeRedirects.delete.submit(id);
};
</script>
