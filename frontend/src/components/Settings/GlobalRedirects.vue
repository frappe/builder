<template>
	<div class="flex h-full flex-col" @keydown.esc="cancelNew">
		<div class="mb-3">
			<BuilderInput
				:modelValue="searchQuery"
				@input="(val: string) => (searchQuery = val)"
				@update:modelValue="(val: string) => (searchQuery = val)"
				type="text"
				placeholder="Search redirects"
				class="w-full"
				icon-left="search" />
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto">
			<!-- Header row -->
			<div
				class="sticky top-0 z-10 border-b border-outline-gray-1 bg-surface-base pb-2 pt-1 text-sm text-ink-gray-5"
				:class="rowGridClass">
				<div class="pl-2">From</div>
				<div class="border-l border-outline-gray-1 pl-2">To</div>
				<div></div>
			</div>

			<!-- Add row, sits at the top of the table -->
			<button
				v-if="!searchQuery.trim() && !newRow"
				class="flex w-full items-center gap-2 border-b border-outline-gray-1 px-2 py-2 text-sm text-ink-gray-5 hover:bg-surface-gray-1 hover:text-ink-gray-8"
				@click="addNewRow">
				<span class="lucide-plus size-4" aria-hidden="true" />
				Add Redirect
			</button>

			<!-- New redirect row: live inputs until it is created -->
			<div
				v-if="newRow"
				data-row
				class="border-b border-outline-gray-1 py-1"
				:class="rowGridClass"
				@focusout="handleNewRowFocusOut">
				<HighlightInput
					v-model="newRow.from"
					placeholder="/blog/(.*)"
					data-new-from
					@keydown.enter.prevent="createNew"
					@keydown.esc.stop.prevent="cancelNew" />
				<div class="border-l border-outline-gray-1 pl-2">
					<HighlightInput
						v-model="newRow.to"
						kind="target"
						placeholder="/news/\1"
						@keydown.enter.prevent="createNew"
						@keydown.esc.stop.prevent="cancelNew" />
				</div>
				<div></div>
			</div>

			<!-- Existing rows: text by default, one cell editable on double-click -->
			<div
				v-for="row in rows"
				:key="row.id"
				data-row
				:data-row-id="row.id"
				class="group/row border-b border-outline-gray-1 py-1 hover:bg-surface-gray-1"
				:class="rowGridClass">
				<div class="min-w-0" @dblclick="startEdit(row, 'from')">
					<HighlightInput
						v-if="isEditing(row, 'from')"
						v-model="editValue"
						:ref="focusEditInput"
						@blur="commitEdit(row, 'from')"
						@keydown.enter.prevent="commitEdit(row, 'from')"
						@keydown.esc.stop.prevent="cancelEdit"
						@keydown.tab.prevent="commitAndEditNext(row, 'from')" />
					<div
						v-else
						:class="[cellBoxClass, 'cursor-default truncate text-ink-gray-8']"
						v-html="highlightSource(row.from)" />
				</div>
				<div class="min-w-0 border-l border-outline-gray-1 pl-2" @dblclick="startEdit(row, 'to')">
					<HighlightInput
						v-if="isEditing(row, 'to')"
						v-model="editValue"
						kind="target"
						:ref="focusEditInput"
						@blur="commitEdit(row, 'to')"
						@keydown.enter.prevent="commitEdit(row, 'to')"
						@keydown.esc.stop.prevent="cancelEdit" />
					<div
						v-else
						:class="[cellBoxClass, 'cursor-default truncate text-ink-gray-8']"
						v-html="highlightTarget(row.to)" />
				</div>
				<div class="flex justify-end">
					<span
						class="lucide-trash size-3.5 cursor-pointer text-ink-gray-5 opacity-0 hover:text-ink-gray-8 group-hover/row:opacity-100"
						aria-hidden="true"
						@click="deleteRedirect(row.id)" />
				</div>
			</div>

			<div v-if="searchQuery.trim() && !rows.length" class="px-2 py-6 text-center text-sm text-ink-gray-5">
				No redirects match "{{ searchQuery }}"
			</div>
		</div>

		<!-- Supported syntax -->
		<div class="mt-3 border-t border-outline-gray-1 pt-3 text-xs">
			<p class="mb-2 text-ink-gray-5">Examples</p>
			<div class="grid w-fit grid-cols-[auto_auto_auto_1fr] items-center gap-x-3 gap-y-1.5">
				<template v-for="example in examples" :key="example.label">
					<code class="font-mono text-ink-gray-7" v-html="highlightSource(example.from)" />
					<span class="lucide-arrow-right size-3 text-ink-gray-4" aria-hidden="true" />
					<code class="font-mono text-ink-gray-7" v-html="highlightTarget(example.to)" />
					<span class="pl-4 text-ink-gray-5">{{ example.label }}</span>
				</template>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import HighlightInput from "@/components/Settings/HighlightInput.vue";
import routeRedirects from "@/data/routeRedirects";
import { cellBoxClass } from "@/utils/editableTable";
import { confirm } from "@/utils/helpers";
import { highlightSource, highlightTarget } from "@/utils/redirectSyntax";
import { toast } from "frappe-ui";
import { computed, nextTick, onMounted, ref, type ComponentPublicInstance } from "vue";

type RedirectRow = { id: string; from: string; to: string };

// shared column template so the header and every row stay aligned
const rowGridClass = "grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_28px] items-center gap-x-2 px-1";

const examples = [
	{ from: "/old-page", to: "/new-page", label: "Exact path" },
	{ from: "/docs", to: "https://example.com/docs", label: "External URL" },
	{ from: "/blog/(.*)", to: "/news/\\1", label: "Regex capture" },
];

const searchQuery = ref("");
const newRow = ref<{ from: string; to: string } | null>(null);

onMounted(() => routeRedirects.fetch());

const rows = computed<RedirectRow[]>(() => {
	const query = searchQuery.value.toLowerCase().trim();
	return (routeRedirects.data || [])
		.map((redirect: { source: string; target: string; name: string }) => ({
			id: redirect.name,
			from: redirect.source,
			to: redirect.target,
		}))
		.filter(
			(row: RedirectRow) =>
				!query || row.from.toLowerCase().includes(query) || row.to.toLowerCase().includes(query),
		);
});

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

// --- create: "Add Redirect" inserts a live row at the top ---
const addNewRow = async () => {
	newRow.value = { from: "", to: "" };
	await nextTick();
	document.querySelector<HTMLInputElement>("input[data-new-from]")?.focus();
};

const cancelNew = () => (newRow.value = null);

// create once focus leaves the new row entirely (tabbing between its cells is fine)
const handleNewRowFocusOut = (e: FocusEvent) => {
	const rowEl = e.currentTarget as HTMLElement;
	if (e.relatedTarget && rowEl.contains(e.relatedTarget as Node)) return;
	createNew();
};

const createNew = () => {
	if (!newRow.value) return;
	const { from, to } = newRow.value;
	if (!from || !to) return (newRow.value = null);

	const tempId = `temp_${Date.now()}`;
	newRow.value = null;
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
		},
		() => {
			const index = routeRedirects.data.findIndex((r: any) => r.name === tempId);
			if (index !== -1) routeRedirects.data.splice(index, 1);
		},
		{ loading: "Adding redirect...", success: "Redirect added", error: "Error adding redirect" },
	);
};

// --- inline edit: double-click a cell, Enter/blur commits, Esc cancels, Tab moves From -> To ---
const editing = ref<{ id: string; field: "from" | "to" } | null>(null);
const editValue = ref("");

const isEditing = (row: RedirectRow, field: "from" | "to") =>
	editing.value?.id === row.id && editing.value?.field === field;

const startEdit = (row: RedirectRow, field: "from" | "to") => {
	editing.value = { id: row.id, field };
	editValue.value = row[field];
};

const focusEditInput = (el: Element | ComponentPublicInstance | null) =>
	(el as { focus?: () => void } | null)?.focus?.();

const cancelEdit = () => (editing.value = null);

const commitEdit = (row: RedirectRow, field: "from" | "to") => {
	if (!isEditing(row, field)) return;
	const value = editValue.value.trim();
	editing.value = null;
	if (value && value !== row[field]) {
		updateRedirect(row.id, field === "from" ? value : row.from, field === "to" ? value : row.to);
	}
};

const commitAndEditNext = (row: RedirectRow, field: "from" | "to") => {
	commitEdit(row, field);
	if (field === "from") startEdit({ ...row, from: editValue.value.trim() || row.from }, "to");
};

const updateRedirect = (id: string, from: string, to: string) => {
	const index = routeRedirects.data.findIndex((r: any) => r.name === id);
	const backup = index !== -1 ? { ...routeRedirects.data[index] } : null;
	performOptimisticUpdate(
		() => routeRedirects.setValue.submit({ name: id, source: from, target: to }),
		() => index !== -1 && Object.assign(routeRedirects.data[index], { source: from, target: to }),
		() => backup && index !== -1 && Object.assign(routeRedirects.data[index], backup),
		{ loading: "Updating redirect...", success: "Redirect updated", error: "Error updating redirect" },
	);
};

const deleteRedirect = async (id: string) => {
	const row = rows.value.find((r) => r.id === id);
	const message = row
		? `Are you sure you want to delete the redirect from "${row.from}" to "${row.to}"?`
		: "Are you sure you want to delete this redirect?";
	if (!(await confirm(message))) return;

	const index = routeRedirects.data.findIndex((r: any) => r.name === id);
	const backup = index !== -1 ? { ...routeRedirects.data[index] } : null;
	performOptimisticUpdate(
		() => routeRedirects.delete.submit(id),
		() => index !== -1 && routeRedirects.data.splice(index, 1),
		() => backup && index !== -1 && routeRedirects.data.splice(index, 0, backup),
		{ loading: "Deleting redirect...", success: "Redirect deleted", error: "Error deleting redirect" },
	);
};
</script>
