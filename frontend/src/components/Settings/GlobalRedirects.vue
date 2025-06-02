<template>
	<div class="flex-1 overflow-y-hidden">
		<div class="mb-5">
			<form onsubmit="return false;">
				<div class="flex gap-2 px-[2px] py-2">
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
					type="submit"
					class="flex w-fit cursor-pointer items-center gap-2 justify-self-end px-[2px] py-1 text-base text-ink-gray-5 hover:text-ink-gray-9"
					@click="addRedirect">
					<FeatherIcon name="plus" class="size-4" />
					<span>Add Redirect</span>
				</button>
			</form>
		</div>
		<div
			class="flex h-full flex-col items-center justify-center text-ink-gray-5"
			v-if="rows.length == 0 && !searchQuery.from && !searchQuery.to">
			<div class="flex h-28 align-top text-base text-ink-gray-4">No redirects set</div>
		</div>
		<div class="h-full text-sm" v-else>
			<div
				class="sticky top-0 flex gap-2 rounded-t-md border-b border-outline-gray-1 bg-surface-gray-1 px-[2px] text-ink-gray-5">
				<span class="w-1/2">
					<BuilderInput
						type="text"
						v-model="searchQuery.from"
						@input="(val: string) => (searchQuery.from = val)"
						placeholder="From URL" />
				</span>
				<span class="w-1/2">
					<BuilderInput
						type="text"
						v-model="searchQuery.to"
						@input="(val: string) => (searchQuery.to = val)"
						placeholder="To URL" />
				</span>
			</div>

			<div class="h-[calc(100%-115px)] overflow-y-auto">
				<div
					class="group flex items-center rounded-sm border-b border-outline-gray-1 px-2 py-2 text-sm text-ink-gray-7 hover:bg-surface-gray-2"
					v-for="row in rows">
					<code class="w-1/2 truncate">{{ row.from }}</code>
					<code class="ml-3 w-1/2 truncate pl-2">{{ row.to }}</code>
					<FeatherIcon
						name="trash"
						class="size-3 cursor-pointer text-ink-gray-5 hover:text-ink-gray-9"
						@click="deleteRedirect(row.id)" />
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import routeRedirects from "@/data/routeRedirects";
import { computed, onMounted, ref } from "vue";
import { toast } from "vue-sonner";

const redirectMap = ref({
	from: "",
	to: "",
});

const searchQuery = ref({
	from: "",
	to: "",
});

onMounted(() => {
	routeRedirects.fetch();
});

const rows = computed(() => {
	return (routeRedirects.data || [])
		.map((redirect: { source: string; target: string; name: string }) => {
			return {
				from: redirect.source,
				to: redirect.target,
				id: redirect.name,
			};
		})
		.filter((row: { from: string; to: string; id: string }) => {
			return (
				row.from.toLowerCase().includes(searchQuery.value.from.toLowerCase()) &&
				row.to.toLowerCase().includes(searchQuery.value.to.toLowerCase())
			);
		});
});

const addRedirect = () => {
	if (!redirectMap.value.from || !redirectMap.value.to) {
		return;
	}
	toast.promise(
		routeRedirects.insert.submit({
			source: redirectMap.value.from,
			target: redirectMap.value.to,
			parenttype: "Website Settings",
			parentfield: "route_redirects",
			parent: "Website Settings",
		}),
		{
			loading: "Adding redirect...",
			success: () => {
				redirectMap.value = { from: "", to: "" };
				return "Redirect added";
			},
			error: (err) => {
				return `Error adding redirect: ${err}`;
			},
		},
	);
};

const deleteRedirect = (id: string) => {
	toast.promise(routeRedirects.delete.submit(id), {
		loading: "Deleting redirect...",
		success: () => {
			return "Redirect deleted";
		},
		error: (err) => {
			return `Error deleting redirect: ${err}`;
		},
	});
};
</script>
