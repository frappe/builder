<template>
	<div class="flex h-full flex-col">
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
				v-if="!searchQuery.trim()"
				class="flex w-full items-center gap-2 border-b border-outline-gray-1 px-2 py-2 text-sm text-ink-gray-5 hover:bg-surface-gray-1 hover:text-ink-gray-8"
				@click="openAdd">
				<span class="lucide-plus size-4" aria-hidden="true" />
				Add Redirect
			</button>

			<!-- Existing rows: text by default, one cell editable on double-click -->
			<div
				v-for="row in rows"
				:key="row.id"
				data-row
				:data-row-id="row.id"
				class="group/row border-b border-outline-gray-1 py-1 hover:bg-surface-gray-1"
				:class="rowGridClass">
				<div
					v-for="(field, i) in fields"
					:key="field"
					class="min-w-0"
					:class="i === 1 && cellDividerClass"
					@dblclick="startEdit(row, field)">
					<HighlightInput
						v-if="isEditing(row, field)"
						v-model="editValue"
						:kind="kindOf(field)"
						:ref="focusEditInput"
						@blur="commitEdit(row, field)"
						@keydown.enter.prevent="commitEdit(row, field)"
						@keydown.esc.stop.prevent="cancelEdit"
						@keydown.tab="onTab(row, field, $event)" />
					<div
						v-else
						:class="[cellBoxClass, 'cursor-default truncate text-ink-gray-8']"
						v-html="highlight(field, row[field])" />
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

		<Dialog
			v-model="showAddDialog"
			title="Add Redirect"
			:actions="[{ label: 'Add Redirect', variant: 'solid', onClick: commitAdd }]">
			<template #default>
				<div class="flex flex-col gap-3">
					<HighlightInput
						v-for="field in fields"
						:key="field"
						v-model="draft[field]"
						:label="field"
						:kind="kindOf(field)"
						:placeholder="placeholders[field]"
						:data-add-from="field === 'from' || undefined"
						@keydown.enter.prevent="commitAdd" />

					<!-- Supported syntax -->
					<div class="mt-1 text-xs">
						<p class="mb-2 text-ink-gray-5">Examples</p>
						<div class="grid w-fit grid-cols-[auto_auto_auto_1fr] items-center gap-x-3 gap-y-1.5">
							<template v-for="example in examples" :key="example.label">
								<code class="font-mono text-ink-gray-7" v-html="highlight('from', example.from)" />
								<span class="lucide-arrow-right size-3 text-ink-gray-4" aria-hidden="true" />
								<code class="font-mono text-ink-gray-7" v-html="highlight('to', example.to)" />
								<span class="pl-4 text-ink-gray-5">{{ example.label }}</span>
							</template>
						</div>
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>
<script setup lang="ts">
import HighlightInput from "@/components/Settings/HighlightInput.vue";
import routeRedirects from "@/data/routeRedirects";
import { cellBoxClass } from "@/utils/editableTable";
import { confirm } from "@/utils/helpers";
import { highlightSource, highlightTarget } from "@/utils/redirectSyntax";
import { Dialog, toast } from "frappe-ui";
import { computed, nextTick, onMounted, ref, type ComponentPublicInstance } from "vue";

type Field = "from" | "to";
type RedirectRow = { id: string; from: string; to: string };

// shared column template so the header and every row stay aligned
const rowGridClass = "grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_28px] items-center gap-x-2 px-1";
const cellDividerClass = "border-l border-outline-gray-1 pl-2";
const fields = ["from", "to"] as const;
const placeholders: Record<Field, string> = { from: "/old-path", to: "/new-path" };

// From is a regex (highlight metacharacters); To is a replacement string (highlight \1 backrefs)
const kindOf = (field: Field) => (field === "to" ? "target" : "source");
const highlight = (field: Field, value: string) =>
	field === "to" ? highlightTarget(value) : highlightSource(value);

const examples = [
	{ from: "/old-page", to: "/new-page", label: "Exact path" },
	{ from: "/docs", to: "https://example.com/docs", label: "External URL" },
	{ from: "/blog/(.*)", to: "/news/\\1", label: "Regex capture" },
];

const searchQuery = ref("");
const showAddDialog = ref(false);
const draft = ref<Record<Field, string>>({ from: "", to: "" });

onMounted(() => routeRedirects.fetch());

const findIndex = (id: string) => routeRedirects.data.findIndex((r: any) => r.name === id);

const rows = computed<RedirectRow[]>(() => {
	const query = searchQuery.value.toLowerCase().trim();
	return (routeRedirects.data || [])
		.map((r: any): RedirectRow => ({ id: r.name, from: r.source, to: r.target }))
		.filter(
			(row) => !query || row.from.toLowerCase().includes(query) || row.to.toLowerCase().includes(query),
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

// --- create: "Add Redirect" opens a modal carrying the From/To inputs and the docs ---
const openAdd = async () => {
	draft.value = { from: "", to: "" };
	showAddDialog.value = true;
	await nextTick();
	document.querySelector<HTMLInputElement>("input[data-add-from]")?.focus();
};

const commitAdd = () => {
	const { from, to } = draft.value;
	if (!from || !to) return;
	showAddDialog.value = false;

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
		},
		() => findIndex(tempId) !== -1 && routeRedirects.data.splice(findIndex(tempId), 1),
		{ loading: "Adding redirect...", success: "Redirect added", error: "Error adding redirect" },
	);
};

// --- inline edit: double-click a cell, Enter/blur commits, Esc cancels, Tab moves From -> To ---
const editing = ref<{ id: string; field: Field } | null>(null);
const editValue = ref("");

const isEditing = (row: RedirectRow, field: Field) =>
	editing.value?.id === row.id && editing.value?.field === field;

const startEdit = (row: RedirectRow, field: Field) => {
	editing.value = { id: row.id, field };
	editValue.value = row[field];
};

const focusEditInput = (el: Element | ComponentPublicInstance | null) =>
	(el as { focus?: () => void } | null)?.focus?.();

const cancelEdit = () => (editing.value = null);

const commitEdit = (row: RedirectRow, field: Field) => {
	if (!isEditing(row, field)) return;
	const value = editValue.value.trim();
	editing.value = null;
	if (value && value !== row[field]) {
		const next = { ...row, [field]: value };
		updateRedirect(row.id, next.from, next.to);
	}
};

const onTab = (row: RedirectRow, field: Field, e: KeyboardEvent) => {
	if (field !== "from") return;
	e.preventDefault();
	commitEdit(row, field);
	startEdit(row, "to");
};

const updateRedirect = (id: string, from: string, to: string) => {
	const index = findIndex(id);
	const backup = index !== -1 ? { ...routeRedirects.data[index] } : null;
	performOptimisticUpdate(
		() => routeRedirects.setValue.submit({ name: id, source: from, target: to }),
		() => index !== -1 && Object.assign(routeRedirects.data[index], { source: from, target: to }),
		() => backup && Object.assign(routeRedirects.data[index], backup),
		{ loading: "Updating redirect...", success: "Redirect updated", error: "Error updating redirect" },
	);
};

const deleteRedirect = async (id: string) => {
	const row = rows.value.find((r) => r.id === id);
	const message = row
		? `Are you sure you want to delete the redirect from "${row.from}" to "${row.to}"?`
		: "Are you sure you want to delete this redirect?";
	if (!(await confirm(message))) return;

	const index = findIndex(id);
	const backup = index !== -1 ? { ...routeRedirects.data[index] } : null;
	performOptimisticUpdate(
		() => routeRedirects.delete.submit(id),
		() => index !== -1 && routeRedirects.data.splice(index, 1),
		() => backup && routeRedirects.data.splice(index, 0, backup),
		{ loading: "Deleting redirect...", success: "Redirect deleted", error: "Error deleting redirect" },
	);
};
</script>
