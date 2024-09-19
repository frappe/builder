<template>
	<div>
		<div class="flex flex-col justify-between gap-5">
			<div class="flex flex-col justify-between text-sm">
				<div class="flex border-b border-outline-gray-1 py-2 text-text-icons-gray-5">
					<span class="w-1/2">From URL</span>
					<span class="w-1/2 pl-2">To URL</span>
				</div>
				<div
					class="group flex items-center rounded-sm border-b border-outline-gray-1 px-2 py-2 text-base text-text-icons-gray-6 hover:bg-surface-gray-2"
					v-for="row in rows">
					<span class="w-1/2">{{ row.from }}</span>
					<span class="ml-3 w-1/2 pl-2">{{ row.to }}</span>
					<FeatherIcon
						name="trash"
						class="size-3 cursor-pointer text-text-icons-gray-5"
						@click="deleteRedirect(row.id)" />
				</div>
				<div class="flex gap-4 py-2">
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
				<div
					class="flex cursor-pointer items-center gap-2 py-1 text-base text-text-icons-gray-5"
					@click="addRedirect">
					<FeatherIcon name="plus" class="size-4" />
					<span>Add Redirect</span>
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
