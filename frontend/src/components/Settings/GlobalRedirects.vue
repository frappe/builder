<template>
	<div class="flex-1 overflow-y-hidden">
		<form @submit.prevent="addRedirect" class="mb-2">
			<div class="flex gap-2 px-[2px] py-2">
				<HighlightInput v-model="redirectMap.from" placeholder="From" />
				<HighlightInput v-model="redirectMap.to" placeholder="To" />
			</div>
			<div class="mr-1 justify-self-end py-1">
				<Button type="submit" label="Add Redirect" variant="ghost" iconLeft="lucide-plus" />
			</div>
		</form>
		<p class="mb-4 flex flex-wrap items-center gap-x-1.5 px-[2px] text-xs text-ink-gray-5">
			<span class="text-ink-gray-6">From</span>
			is matched as a regex, reuse captured groups in
			<span class="text-ink-gray-6">To</span>
			with
			<code class="rounded bg-surface-gray-2 px-1 py-0.5" v-html="highlight('\\1')" />
			— e.g.
			<code class="rounded bg-surface-gray-2 px-1 py-0.5" v-html="highlight('/blog/(.*)')" />
			<span class="lucide-arrow-right size-3 text-ink-gray-4" aria-hidden="true" />
			<code class="rounded bg-surface-gray-2 px-1 py-0.5" v-html="highlight('/news/\\1')" />
		</p>
		<div
			v-if="!rows.length && !searchQuery.from && !searchQuery.to"
			class="flex h-full flex-col items-center justify-center">
			<div class="h-28 text-base text-ink-gray-4">No redirects set</div>
		</div>
		<div v-else class="h-full text-sm">
			<div
				class="sticky top-0 flex gap-2 rounded-t-md border-b border-outline-gray-1 bg-surface-gray-1 px-[2px] text-ink-gray-5">
				<BuilderInput v-model="searchQuery.from" placeholder="From URL" />
				<BuilderInput v-model="searchQuery.to" placeholder="To URL" />
			</div>
			<div class="h-[calc(100%-115px)] overflow-y-auto">
				<div
					v-for="row in rows"
					:key="row.id"
					class="group flex items-center rounded-sm border-b border-outline-gray-1 px-2 py-2 text-sm text-ink-gray-7 hover:bg-surface-gray-2">
					<div class="w-[calc(50%-.5rem)]">
						<HighlightInput
							v-if="editingRedirect === row.id"
							v-model="editForm.from"
							@keyup.enter="saveRedirect(row.id)"
							@keyup.escape="cancelEdit" />
						<code
							v-else
							class="block cursor-pointer truncate rounded px-1 py-1 pr-2 hover:bg-surface-gray-1"
							@click="startEdit(row.id, row.from, row.to)"
							v-html="highlight(row.from)" />
					</div>
					<div class="w-[calc(50%-.5rem)] pl-3 pr-2">
						<HighlightInput
							v-if="editingRedirect === row.id"
							v-model="editForm.to"
							@keyup.enter="saveRedirect(row.id)"
							@keyup.escape="cancelEdit" />
						<code
							v-else
							class="block cursor-pointer truncate rounded px-1 py-1 hover:bg-surface-gray-1"
							@click="startEdit(row.id, row.from, row.to)"
							v-html="highlight(row.to)" />
					</div>
					<div class="flex gap-1">
						<template v-if="editingRedirect === row.id">
							<span
								class="lucide-check size-3 cursor-pointer text-ink-gray-5 hover:text-ink-gray-9"
								aria-hidden="true"
								@click="saveRedirect(row.id)" />
							<span
								class="lucide-x size-3 cursor-pointer text-ink-gray-5 hover:text-ink-gray-9"
								aria-hidden="true"
								@click="cancelEdit" />
						</template>
						<span
							v-else
							class="lucide-trash size-3 cursor-pointer text-ink-gray-5 hover:text-ink-gray-9"
							aria-hidden="true"
							@click="deleteRedirect(row.id)" />
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import HighlightInput from "@/components/Settings/HighlightInput.vue";
import routeRedirects from "@/data/routeRedirects";
import { confirm } from "@/utils/helpers";
import { highlightRedirectSyntax as highlight } from "@/utils/redirectSyntax";
import { toast } from "frappe-ui";
import { computed, onMounted, ref } from "vue";

const redirectMap = ref({ from: "", to: "" });
const searchQuery = ref({ from: "", to: "" });
const editingRedirect = ref<string | null>(null);
const editForm = ref({ from: "", to: "" });

onMounted(() => routeRedirects.fetch());

const rows = computed(() =>
	(routeRedirects.data || [])
		.map((redirect: { source: string; target: string; name: string }) => ({
			from: redirect.source,
			to: redirect.target,
			id: redirect.name,
		}))
		.filter(
			(row: { from: string; to: string; id: string }) =>
				row.from.toLowerCase().includes(searchQuery.value.from.toLowerCase()) &&
				row.to.toLowerCase().includes(searchQuery.value.to.toLowerCase()),
		),
);

const performOptimisticUpdate = (
	operation: () => Promise<any>,
	optimistic: () => void,
	revert: () => void,
	messages: { loading: string; success: string; error: string },
) => {
	optimistic();
	toast.promise(operation(), {
		loading: messages.loading,
		success: () => (routeRedirects.fetch(), messages.success),
		error: (err: any) => (revert(), `${messages.error}: ${err}`),
	});
};

const addRedirect = () => {
	const { from, to } = redirectMap.value;
	if (!from || !to) return;

	const tempId = `temp_${Date.now()}`;
	performOptimisticUpdate(
		() =>
			routeRedirects.insert.submit({
				source: from,
				target: to,
				parenttype: "Website Settings",
				parentfield: "route_redirects",
				parent: "Website Settings",
			}),
		() => {
			if (!routeRedirects.data) routeRedirects.data = [];
			routeRedirects.data.unshift({ source: from, target: to, name: tempId });
			redirectMap.value = { from: "", to: "" };
		},
		() => {
			const index = routeRedirects.data.findIndex((r: any) => r.name === tempId);
			if (index !== -1) routeRedirects.data.splice(index, 1);
		},
		{ loading: "Adding redirect...", success: "Redirect added", error: "Error adding redirect" },
	);
};

const deleteRedirect = async (id: string) => {
	const redirect = rows.value.find((row: any) => row.id === id);
	const message = redirect
		? `Are you sure you want to delete the redirect from "${redirect.from}" to "${redirect.to}"?`
		: "Are you sure you want to delete this redirect?";

	if (await confirm(message)) {
		const index = routeRedirects.data.findIndex((r: any) => r.name === id);
		const backup = index !== -1 ? { ...routeRedirects.data[index] } : null;

		performOptimisticUpdate(
			() => routeRedirects.delete.submit(id),
			() => index !== -1 && routeRedirects.data.splice(index, 1),
			() => backup && index !== -1 && routeRedirects.data.splice(index, 0, backup),
			{ loading: "Deleting redirect...", success: "Redirect deleted", error: "Error deleting redirect" },
		);
	}
};

const updateRedirect = (id: string, from: string, to: string) => {
	const index = routeRedirects.data.findIndex((r: any) => r.name === id);
	performOptimisticUpdate(
		() => routeRedirects.setValue.submit({ name: id, source: from, target: to }),
		() => index !== -1 && Object.assign(routeRedirects.data[index], { source: from, target: to }),
		() => routeRedirects.fetch(),
		{ loading: "Updating redirect...", success: "Redirect updated", error: "Error updating redirect" },
	);
};

const startEdit = (id: string, from: string, to: string) => (
	(editingRedirect.value = id), (editForm.value = { from, to })
);

const cancelEdit = () => ((editingRedirect.value = null), (editForm.value = { from: "", to: "" }));
const saveRedirect = (id: string) => {
	if (editForm.value.from && editForm.value.to) {
		updateRedirect(id, editForm.value.from, editForm.value.to);
		cancelEdit();
	}
};
</script>
