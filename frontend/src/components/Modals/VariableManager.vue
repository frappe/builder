<!-- TODO: Refactor; split into manageable smaller files -->
<template>
	<DraggablePopup
		:modelValue="modelValue"
		@update:modelValue="
			(val) => {
				emit('update:modelValue', val);
			}
		"
		:width="520"
		:container="container"
		v-if="modelValue"
		:placement-offset-top="8"
		:placement-offset-left="65"
		action-label="Add Variable"
		:action-handler="addNewVariable"
		placement="top-left">
		<template #header><h2 class="text-xl-semibold py-2">Manage Variables</h2></template>
		<template #content>
			<div @keydown.esc="clearSelection">
				<div class="mb-3">
					<BuilderInput
						:modelValue="searchQuery"
						@input="(val: string) => (searchQuery = val)"
						@update:modelValue="(val: string) => (searchQuery = val)"
						type="text"
						placeholder="Search variables"
						class="w-full"
						icon-left="search" />
				</div>

				<div class="max-h-[60vh] overflow-y-auto">
					<!-- Header row -->
					<div
						class="sticky top-0 z-10 border-b border-outline-gray-1 bg-surface-base pb-2 pt-1 text-sm text-ink-gray-5"
						:class="rowGridClass">
						<div class="pl-2">Name</div>
						<div class="border-l border-outline-gray-1 pl-2">Light</div>
						<div class="border-l border-outline-gray-1 pl-2">Dark</div>
					</div>

					<template v-for="group in displayGroups" :key="group.group ?? '__flat__'">
						<!-- Group header -->
						<div
							v-if="group.group !== null"
							data-group-header
							class="text-sm-medium sticky top-7 z-10 border-b border-outline-gray-1 bg-surface-base px-3 pb-2 pt-5 text-ink-gray-5">
							{{ group.group }}
						</div>

						<div>
							<!-- New variable row: every cell is a live input until it is created -->
							<template v-for="row in group.rows" :key="row.id">
								<div
									v-if="row.isNew"
									data-row
									class="rounded py-2"
									:class="rowGridClass"
									@focusout="(e) => handleNewRowFocusOut(e, row)">
									<input
										type="text"
										:value="row.variable_name"
										placeholder="Variable name"
										:class="[cellBoxClass, editableInputClass]"
										data-new-name
										@mousedown.stop
										@input="(e) => (row.variable_name = inputValue(e))"
										@keydown.enter.prevent="() => createVariable(row)"
										@keydown.esc.stop.prevent="() => (newVariable = null)" />
									<div
										:class="[
											colorCellBoxClass,
											'rounded-l-none border-l border-outline-gray-1 bg-surface-base ring-2 ring-outline-gray-3',
										]">
										<ColorPicker
											class="!w-auto shrink-0"
											:modelValue="(row.value as any) || null"
											placement="bottom-start"
											@update:modelValue="(value: string | null) => updateColor(row, value, 'light')">
											<template #target="{ togglePopover }">
												<button
													class="h-4 w-4 shrink-0 rounded-full border border-outline-gray-2"
													:style="{ backgroundColor: resolveVariableValue(row.value || '') }"
													title="Pick color"
													@mousedown.stop
													@click="togglePopover"></button>
											</template>
										</ColorPicker>
										<input
											type="text"
											:value="row.value"
											placeholder="#ffffff"
											:class="colorValueInputClass"
											@mousedown.stop
											@input="(e) => updateColor(row, inputValue(e), 'light')" />
									</div>
									<div
										:class="[
											colorCellBoxClass,
											'rounded-l-none border-l border-outline-gray-1 bg-surface-base ring-2 ring-outline-gray-3',
										]">
										<ColorPicker
											class="!w-auto shrink-0"
											:modelValue="((row.dark_value || row.value) as any) || null"
											placement="bottom-start"
											@update:modelValue="(value: string | null) => updateColor(row, value, 'dark')">
											<template #target="{ togglePopover }">
												<button
													class="h-4 w-4 shrink-0 rounded-full border border-outline-gray-2"
													:style="{
														backgroundColor: resolveVariableValue(row.dark_value || row.value || ''),
													}"
													title="Pick color"
													@mousedown.stop
													@click="togglePopover"></button>
											</template>
										</ColorPicker>
										<input
											type="text"
											:value="row.dark_value"
											:placeholder="row.value || '#000000'"
											:class="colorValueInputClass"
											@mousedown.stop
											@input="(e) => updateColor(row, inputValue(e), 'dark')" />
									</div>
								</div>

								<!-- Existing variable row: text by default, one cell editable on double-click -->
								<div
									v-else
									data-row
									:data-row-id="row.id"
									tabindex="-1"
									class="group/row select-none border-b border-outline-gray-1 py-1 outline-none"
									:class="[
										rowGridClass,
										{
											'opacity-60': row.is_standard,
											'bg-surface-gray-2': selectedIds.has(row.id),
											'hover:bg-surface-gray-1': !selectedIds.has(row.id),
										},
									]"
									@mousedown="(e) => handleRowMouseDown(e, row)"
									@contextmenu="(e) => handleRowContextMenu(e, row)">
									<!-- Name -->
									<div class="flex min-w-0 items-center gap-1.5">
										<Tooltip
											v-if="row.is_standard"
											text="This is a standard variable. It cannot be modified or deleted."
											placement="top">
											<span
												class="lucide-info ml-1 h-3.5 w-3.5 shrink-0 text-ink-gray-5"
												aria-hidden="true" />
										</Tooltip>
										<input
											v-if="isEditing(row, 'variable_name')"
											type="text"
											:value="row.variable_name"
											:class="[cellBoxClass, editableInputClass]"
											:ref="focusEditInput"
											@mousedown.stop
											@blur="(e) => commitEdit(row, 'variable_name', e)"
											@keydown.enter.prevent="(e) => commitEdit(row, 'variable_name', e)"
											@keydown.esc.stop.prevent="() => cancelEdit(row)"
											@keydown.tab.prevent="(e) => commitAndEditNext(row, 'variable_name', e)" />
										<div
											v-else
											:class="[cellBoxClass, cellTextClass(row), row.variable_name ? '' : 'text-ink-gray-4']"
											@dblclick="startEdit(row, 'variable_name')">
											{{ row.variable_name || "unnamed" }}
										</div>
									</div>
									<!-- Light -->
									<div
										:class="[
											colorCellBoxClass,
											'rounded-l-none border-l border-outline-gray-1',
											isEditing(row, 'value')
												? 'bg-surface-base ring-2 ring-outline-gray-3'
												: cellTextClass(row),
										]"
										@dblclick="startEdit(row, 'value')">
										<ColorPicker
											v-if="!row.is_standard"
											class="!w-auto shrink-0"
											:modelValue="(row.value as any) || null"
											placement="bottom-start"
											@update:modelValue="(value: string | null) => updateColor(row, value, 'light')">
											<template #target="{ togglePopover }">
												<button
													class="h-4 w-4 shrink-0 rounded-full border border-outline-gray-2"
													:style="{ backgroundColor: resolveVariableValue(row.value || '') }"
													title="Pick color"
													@mousedown.stop
													@dblclick.stop
													@click="togglePopover"></button>
											</template>
										</ColorPicker>
										<div
											v-else
											class="h-4 w-4 shrink-0 rounded-full border border-outline-gray-2"
											:style="{ backgroundColor: resolveVariableValue(row.value || '') }"></div>
										<input
											v-if="isEditing(row, 'value')"
											type="text"
											:value="row.value"
											:class="colorValueInputClass"
											:ref="focusEditInput"
											@mousedown.stop
											@blur="(e) => commitEdit(row, 'value', e)"
											@keydown.enter.prevent="(e) => commitEdit(row, 'value', e)"
											@keydown.esc.stop.prevent="() => cancelEdit(row)"
											@keydown.tab.prevent="(e) => commitAndEditNext(row, 'value', e)" />
										<span v-else class="truncate">{{ row.value }}</span>
									</div>
									<!-- Dark -->
									<div
										:class="[
											colorCellBoxClass,
											'rounded-l-none border-l border-outline-gray-1',
											isEditing(row, 'dark_value')
												? 'bg-surface-base ring-2 ring-outline-gray-3'
												: cellTextClass(row),
										]"
										@dblclick="startEdit(row, 'dark_value')">
										<ColorPicker
											v-if="!row.is_standard"
											class="!w-auto shrink-0"
											:modelValue="((row.dark_value || row.value) as any) || null"
											placement="bottom-start"
											@update:modelValue="(value: string | null) => updateColor(row, value, 'dark')">
											<template #target="{ togglePopover }">
												<button
													class="h-4 w-4 shrink-0 rounded-full border border-outline-gray-2"
													:style="{
														backgroundColor: resolveVariableValue(row.dark_value || row.value || ''),
													}"
													title="Pick color"
													@mousedown.stop
													@dblclick.stop
													@click="togglePopover"></button>
											</template>
										</ColorPicker>
										<div
											v-else
											class="h-4 w-4 shrink-0 rounded-full border border-outline-gray-2"
											:style="{
												backgroundColor: resolveVariableValue(row.dark_value || row.value || ''),
											}"></div>
										<input
											v-if="isEditing(row, 'dark_value')"
											type="text"
											:value="row.dark_value"
											:placeholder="row.value || '#000000'"
											:class="colorValueInputClass"
											:ref="focusEditInput"
											@mousedown.stop
											@blur="(e) => commitEdit(row, 'dark_value', e)"
											@keydown.enter.prevent="(e) => commitEdit(row, 'dark_value', e)"
											@keydown.esc.stop.prevent="() => cancelEdit(row)"
											@keydown.tab.prevent="(e) => commitAndEditNext(row, 'dark_value', e)" />
										<span v-else class="truncate" :class="{ 'text-ink-gray-4': !row.dark_value }">
											{{ row.dark_value || row.value }}
										</span>
									</div>
								</div>
							</template>
						</div>
					</template>
					<div v-if="!hasRows" class="py-10 text-center">
						<div class="text-base-medium text-ink-gray-7">
							{{ searchQuery.trim() ? "No Variables Found" : "No Variables" }}
						</div>
						<div class="mt-1 text-sm text-ink-gray-5">
							{{
								searchQuery.trim()
									? `No variables match "${searchQuery}". Try a different search term.`
									: "No variables found. Click 'Add Variable' to create your first one."
							}}
						</div>
					</div>
				</div>

				<ContextMenu ref="contextMenu" :options="contextMenuOptions" />

				<Dialog
					v-model="showGroupDialog"
					title="Move to group"
					size="sm"
					:actions="[{ label: 'Move', variant: 'solid', onClick: confirmGroupDialog }]">
					<template #default>
						<Autocomplete
							:modelValue="moveTargetGroup"
							:options="groupOptions"
							placeholder="Select or type a group name"
							@update:modelValue="(val: string | null) => (moveTargetGroup = val || '')" />
					</template>
				</Dialog>

				<div class="flex items-center pt-4">
					<input ref="csvFileInput" type="file" accept=".csv" @change="handleCSVUpload" class="hidden" />
					<Button @click="triggerCSVUpload" variant="outline" theme="gray" size="sm" icon-left="upload">
						Upload CSV
					</Button>
					<button
						@click="downloadSampleCSV"
						variant="subtle"
						class="ml-2 text-xs text-blue-600 underline hover:text-blue-700">
						Download sample
					</button>
				</div>
			</div>
		</template>
	</DraggablePopup>
</template>

<script setup lang="ts">
import ContextMenu from "@/components/ContextMenu.vue";
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import ColorPicker from "@/components/Controls/ColorPicker.vue";
import DraggablePopup from "@/components/Controls/DraggablePopup.vue";
import { BuilderVariable } from "@/types/doctypes";
import { cellBoxClass } from "@/utils/editableTable";
import { confirm } from "@/utils/helpers";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { useDebounceFn } from "@vueuse/core";
import { Button, Dialog, toast, Tooltip } from "frappe-ui";
import { computed, nextTick, reactive, ref, type ComponentPublicInstance } from "vue";

defineProps<{
	modelValue: boolean;
	container?: HTMLElement | null;
}>();

const emit = defineEmits<{
	"update:modelValue": [value: boolean];
}>();

const {
	resolveVariableValue,
	createVariable: createVar,
	updateVariable,
	deleteVariable,
	variables,
} = useBuilderVariable();

const csvFileInput = ref<HTMLInputElement>();
const contextMenu = ref<InstanceType<typeof ContextMenu> | null>(null);
const nextNewId = ref(1);
const newVariable = ref<Row | null>(null);
const searchQuery = ref("");
const isCreating = ref(false);

// shared column template so the header and every row stay aligned
const rowGridClass = "grid grid-cols-[minmax(0,1fr)_128px_128px] items-center gap-x-2 px-1";

const cellBoxClass = "w-full min-w-0 rounded-sm px-2 py-1 text-sm";
// the focus: variants out-rank @tailwindcss/forms' blue [type='text']:focus ring/border
const editableInputClass =
	"border-none bg-surface-base text-ink-gray-8 outline-none ring-2 ring-outline-gray-3 placeholder:text-ink-gray-4 focus:outline-none focus:ring-2 focus:ring-outline-gray-3";
const cellTextClass = (row: Row) =>
	row.is_standard ? "truncate text-ink-gray-8" : "cursor-default truncate text-ink-gray-8";
// color cells render the swatch and the value as a single unit
const colorCellBoxClass = "flex w-full min-w-0 items-center gap-1.5 rounded-sm px-2 py-1 text-sm";
const colorValueInputClass =
	"w-full min-w-0 border-none bg-transparent p-0 text-sm text-ink-gray-8 outline-none placeholder:text-ink-gray-4 focus:outline-none focus:ring-0";

type Row = Partial<BuilderVariable> & { id: string; isNew: boolean };
type RowGroup = { group: string | null; open: boolean; rows: Row[] };
type EditableField = "variable_name" | "group" | "value" | "dark_value";

const UNGROUPED_LABEL = "Ungrouped";

// row objects are reused across recomputes so that an open cell editor is never
// rebuilt or stomped by a save round-trip
const rowObjects = new Map<string, Row>();
const getRowObject = (variable: BuilderVariable) => {
	let row = rowObjects.get(variable.name);
	if (!row) {
		row = reactive({ ...variable, id: variable.name, isNew: false });
		rowObjects.set(variable.name, row);
	}
	return row;
};
// drop local row state so fresh store values flow in (used after bulk external changes like CSV import)
const resetRowObjects = () => rowObjects.clear();

// group objects are reused across recomputes so that the open state survives edits
const groupObjects = new Map<string, RowGroup>();
const getGroupObject = (groupName: string) => {
	if (!groupObjects.has(groupName)) {
		groupObjects.set(groupName, reactive({ group: groupName, open: true, rows: [] }));
	}
	return groupObjects.get(groupName) as RowGroup;
};
const flatGroup = reactive({ group: null, open: true, rows: [] }) as RowGroup;

const displayGroups = computed<RowGroup[]>(() => {
	let filteredVariables = variables.value;
	if (searchQuery.value.trim()) {
		const query = searchQuery.value.toLowerCase().trim();
		filteredVariables = variables.value.filter(
			(variable) =>
				variable.variable_name?.toLowerCase().includes(query) ||
				variable.group?.toLowerCase().includes(query),
		);
	}

	const rows: Row[] = filteredVariables.map(getRowObject);
	if (newVariable.value) {
		rows.unshift(newVariable.value);
	}

	// keep the flat list when no variable uses groups; the new row is ignored so that
	// typing a group for it doesn't restructure the list (and unmount its inputs) mid-typing
	const hasGroups = rows.some((row) => !row.isNew && row.group);
	if (!hasGroups) {
		flatGroup.rows = rows;
		return rows.length ? [flatGroup] : [];
	}

	const grouped = new Map<string, Row[]>();
	for (const row of rows) {
		// the row being created always stays on top, outside any group
		const groupName = row.isNew ? UNGROUPED_LABEL : row.group || UNGROUPED_LABEL;
		if (!grouped.has(groupName)) grouped.set(groupName, []);
		grouped.get(groupName)?.push(row);
	}

	const groupNames = [...grouped.keys()].sort((a, b) => {
		// ungrouped variables stay on top, named groups follow alphabetically
		if (a === UNGROUPED_LABEL) return -1;
		if (b === UNGROUPED_LABEL) return 1;
		return a.localeCompare(b);
	});

	return groupNames.map((groupName) => {
		const groupObject = getGroupObject(groupName);
		groupObject.rows = grouped.get(groupName) || [];
		return groupObject;
	});
});

const hasRows = computed(() => displayGroups.value.some((group) => group.rows.length));

const inputValue = (e: Event) => (e.target as HTMLInputElement).value;

// --- cell editing: double-click to edit, Enter/blur commits, Esc cancels ---
const EDIT_ORDER: EditableField[] = ["variable_name", "group", "value", "dark_value"];
const editingCell = ref<{ rowId: string; field: EditableField } | null>(null);

const isEditing = (row: Row, field: EditableField) =>
	editingCell.value?.rowId === row.id && editingCell.value?.field === field;

const startEdit = (row: Row, field: EditableField) => {
	if (row.is_standard || row.isNew) return;
	editingCell.value = { rowId: row.id, field };
};

const focusEditInput = (el: Element | ComponentPublicInstance | null) => {
	if (el instanceof HTMLInputElement) {
		el.focus();
		el.select();
	}
};

const exitEdit = (row: Row) => {
	editingCell.value = null;
	// hand focus back to the row so keyboard interactions (Esc etc.) keep working
	nextTick(() => {
		if (editingCell.value) return; // a follow-up edit (Tab) took over
		document.querySelector<HTMLElement>(`[data-row-id="${CSS.escape(row.id)}"]`)?.focus();
	});
};

const commitEdit = (row: Row, field: EditableField, e: Event) => {
	// Esc already closed this editor; ignore the trailing blur
	if (!isEditing(row, field)) return;
	const value = inputValue(e).trim();
	exitEdit(row);
	if ((row[field] || "") === value) return;
	row[field] = value;
	if (field === "value" || field === "dark_value") {
		syncStoreColors(row);
	}
	saveVariable(row);
};

const cancelEdit = (row: Row) => {
	if (!editingCell.value) return;
	exitEdit(row);
};

const commitAndEditNext = (row: Row, field: EditableField, e: KeyboardEvent) => {
	// bounded: tab moves name -> group -> light -> dark, then exits
	const next = e.shiftKey ? undefined : EDIT_ORDER[EDIT_ORDER.indexOf(field) + 1];
	commitEdit(row, field, e);
	if (next) {
		editingCell.value = { rowId: row.id, field: next };
	}
};

// create the variable once focus leaves the new row entirely (Tab-ing between its cells is fine)
const handleNewRowFocusOut = (e: FocusEvent, row: Row) => {
	const rowEl = e.currentTarget as HTMLElement;
	if (e.relatedTarget && rowEl.contains(e.relatedTarget as Node)) return;
	createVariable(row);
};

// --- selection (click / shift+click / cmd+click) ---
const selectedIds = ref(new Set<string>());
const anchorId = ref<string | null>(null);

// rows that can take part in a selection, in visual order (collapsed groups excluded)
const visibleSelectableRows = computed(() =>
	displayGroups.value.flatMap((group) =>
		group.open ? group.rows.filter((row) => !row.is_standard && !row.isNew) : [],
	),
);

const clearSelection = () => {
	selectedIds.value = new Set();
	anchorId.value = null;
};

const selectedRows = () => visibleSelectableRows.value.filter((row) => selectedIds.value.has(row.id));

const handleRowMouseDown = (e: MouseEvent, row: Row) => {
	// right/middle clicks are handled by the context menu handler
	if (e.button !== 0) return;
	if (row.is_standard) return;

	if (e.shiftKey) {
		// range select from the anchor; prevent text caret/selection
		e.preventDefault();
		const rows = visibleSelectableRows.value;
		const from = rows.findIndex((r) => r.id === (anchorId.value ?? row.id));
		const to = rows.findIndex((r) => r.id === row.id);
		if (from === -1 || to === -1) return;
		const [start, end] = from < to ? [from, to] : [to, from];
		selectedIds.value = new Set(rows.slice(start, end + 1).map((r) => r.id));
	} else if (e.metaKey || e.ctrlKey) {
		e.preventDefault();
		const next = new Set(selectedIds.value);
		next.has(row.id) ? next.delete(row.id) : next.add(row.id);
		selectedIds.value = next;
		anchorId.value = row.id;
	} else {
		selectedIds.value = new Set([row.id]);
		anchorId.value = row.id;
	}
};

const handleRowContextMenu = (e: MouseEvent, row: Row) => {
	if (row.isNew || row.is_standard) return;
	if (!selectedIds.value.has(row.id)) {
		selectedIds.value = new Set([row.id]);
		anchorId.value = row.id;
	}
	contextMenu.value?.show(e);
};

// --- context menu actions ---
const existingGroups = computed(() => {
	const groups = new Set<string>();
	for (const variable of variables.value) {
		if (variable.group) groups.add(variable.group);
	}
	return [...groups].sort((a, b) => a.localeCompare(b));
});

// "Move to group…" dialog: pick an existing group or type a new name
const showGroupDialog = ref(false);
const moveTargetGroup = ref("");

const groupOptions = computed(() => existingGroups.value.map((group) => ({ label: group, value: group })));

const openGroupDialog = () => {
	moveTargetGroup.value = "";
	showGroupDialog.value = true;
};

const confirmGroupDialog = async () => {
	const group = moveTargetGroup.value.trim();
	if (!group) return;
	showGroupDialog.value = false;
	await moveSelectedToGroup(group);
};

const moveSelectedToGroup = async (group: string) => {
	const rows = selectedRows();
	if (!rows.length) return;
	for (const row of rows) {
		row.group = group;
		await saveVariable(row);
	}
	toast.success(
		group ? `Moved ${rows.length} variable(s) to "${group}"` : `Ungrouped ${rows.length} variable(s)`,
	);
};

const uniqueCopyName = (name: string) => {
	const names = new Set(variables.value.map((variable) => variable.variable_name));
	let copyName = `${name} copy`;
	let counter = 2;
	while (names.has(copyName)) copyName = `${name} copy ${counter++}`;
	return copyName;
};

const deleteSelected = async () => {
	const rows = selectedRows();
	if (!rows.length) return;
	const confirmed = await confirm(`Are you sure you want to delete ${rows.length} variable(s)?`);
	if (!confirmed) return;

	let deleted = 0;
	for (const row of rows) {
		try {
			await deleteVariable(row.name!);
			rowObjects.delete(row.name!);
			deleted++;
		} catch (error) {
			toast.error(`Failed to delete "${row.variable_name}"`);
		}
	}
	if (deleted) toast.success(`Deleted ${deleted} variable(s)`);
	clearSelection();
};

const contextMenuOptions = computed(() => {
	const count = selectedIds.value.size;
	const suffix = count > 1 ? ` ${count} variables` : " variable";
	return [
		{ label: "Move to group", action: openGroupDialog },
		{
			label: "Remove from group",
			action: () => moveSelectedToGroup(""),
			condition: () => selectedRows().some((row) => row.group),
		},
		{ label: `Delete${suffix}`, action: deleteSelected },
	];
});

// --- create / save ---
const addNewVariable = async () => {
	nextNewId.value++;
	newVariable.value = reactive({
		id: `new-${nextNewId.value}`,
		isNew: true,
		variable_name: "",
		value: "#ffffff",
		dark_value: "",
		group: "",
		type: "Color" as const,
	});
	await nextTick();
	document.querySelector<HTMLInputElement>("input[data-new-name]")?.focus();
};

// keep the store in sync so the canvas reflects color edits live
const syncStoreColors = (row: Row) => {
	variables.value = variables.value.map((v) =>
		v.name === row.name ? { ...v, value: row.value || "", dark_value: row.dark_value || "" } : v,
	);
};

// live color updates from the pickers (and the new row's inputs)
const updateColor = async (row: Row, value: string | null, mode: "light" | "dark") => {
	if (mode === "light") {
		row.value = value || "";
	} else {
		row.dark_value = value || "";
	}
	syncStoreColors(row);

	if (row.isNew) {
		if (row.variable_name?.trim()) {
			debouncedSaveVariable(row);
		}
	} else if (row.name) {
		debouncedSaveVariable(row);
	}
};

const debouncedSaveVariable = useDebounceFn(async (row: Row) => {
	try {
		if (row.isNew) {
			await createVariable(row);
		} else {
			await saveVariable(row);
		}
	} catch (error) {
		console.error("Failed to update variable:", error);
	}
}, 300);

const createVariable = async (row: Row) => {
	if (!row.isNew || !row.variable_name?.trim() || isCreating.value) return;

	isCreating.value = true;
	try {
		const createdVariable = await createVar({
			variable_name: row.variable_name!,
			value: row.value || "#ffffff",
			dark_value: row.dark_value || undefined,
			group: row.group || undefined,
			type: row.type || "Color",
		});
		newVariable.value = null;
		await nextTick();
		toast.success("Variable created successfully");
		return createdVariable;
	} catch (error) {
		toast.error((error as Error).message || "Failed to create variable");
	} finally {
		isCreating.value = false;
	}
};

const saveVariable = async (row: Row) => {
	if (!row.name) return;

	try {
		await updateVariable({
			name: row.name,
			variable_name: row.variable_name!,
			value: row.value!,
			dark_value: row.dark_value || undefined,
			group: row.group || "",
			type: row.type || "Color",
		});
	} catch (error) {
		toast.error((error as Error).message || "Failed to update variable");
	}
};

// CSV handling
const triggerCSVUpload = () => csvFileInput.value?.click();

const handleCSVUpload = (event: Event) => {
	const file = (event.target as HTMLInputElement).files?.[0];
	if (!file) return;

	const reader = new FileReader();
	reader.onload = (e) => {
		try {
			const csvText = e.target?.result as string;
			parseCSVAndAddVariables(csvText);
		} catch (error) {
			toast.error("Failed to read CSV file");
		}
	};
	reader.readAsText(file);
};

const parseCSVAndAddVariables = async (csvText: string) => {
	const lines = csvText.trim().split("\n");
	if (lines.length < 2) {
		toast.error("CSV must have at least a header row and one data row");
		return;
	}

	const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
	const nameIndex = headers.findIndex((h) => h.includes("name") || h.includes("variable"));
	const lightIndex = headers.findIndex((h) => h.includes("light") || h.includes("value"));
	const darkIndex = headers.findIndex((h) => h.includes("dark"));
	const groupIndex = headers.findIndex((h) => h.includes("group"));

	if (nameIndex === -1 || lightIndex === -1) {
		toast.error("CSV must contain 'Variable Name' and 'Light Mode' columns");
		return;
	}

	const newVariables: Partial<BuilderVariable>[] = [];
	const updateVariables: Partial<BuilderVariable & { name?: string }>[] = [];
	let invalidCount = 0;
	let standardCount = 0;

	for (let i = 1; i < lines.length; i++) {
		const values = lines[i].split(",").map((v) => v.trim().replace(/"/g, ""));
		const variableName = values[nameIndex];
		const lightValue = values[lightIndex];
		const darkValue = darkIndex !== -1 ? values[darkIndex] : "";
		// undefined when the CSV has no Group column, so existing groups are preserved on update;
		// a present-but-blank cell clears the group explicitly
		const groupValue = groupIndex !== -1 ? values[groupIndex] : undefined;

		if (variableName && lightValue) {
			const existing = variables.value.find((v) => v.variable_name === variableName);
			if (!existing) {
				newVariables.push({
					variable_name: variableName,
					value: lightValue,
					dark_value: darkValue,
					group: groupValue,
					type: "Color",
				});
			} else if (existing.is_standard) {
				// standard variables are read-only in the manager; skip them here too
				standardCount++;
			} else {
				updateVariables.push({
					name: existing.name,
					variable_name: variableName,
					value: lightValue,
					dark_value: darkValue,
					group: groupValue,
					type: existing.type || "Color",
				});
			}
		} else {
			invalidCount++;
		}
	}

	if (newVariables.length === 0 && updateVariables.length === 0) {
		if (invalidCount > 0) toast.error(`${invalidCount} entries were invalid`);
		if (csvFileInput.value) csvFileInput.value.value = "";
		return;
	}

	// Warn user that existing variables will be updated
	const skippedNotes = [
		invalidCount > 0 ? `${invalidCount} invalid entries skipped` : "",
		standardCount > 0 ? `${standardCount} standard variable(s) skipped` : "",
	]
		.filter(Boolean)
		.join(", ");
	const confirmed = await confirm(
		`Create ${newVariables.length} new variable(s) and update ${
			updateVariables.length
		} existing variable(s)?${
			skippedNotes ? ` (${skippedNotes})` : ""
		}\n\nWARNING: Updating will overwrite the existing values for the listed variables.`,
	);

	if (!confirmed) {
		if (csvFileInput.value) csvFileInput.value.value = "";
		return;
	}

	let createdCount = 0;
	let updatedCount = 0;
	let createErrors = 0;
	let updateErrors = 0;

	for (const variable of updateVariables) {
		try {
			await updateVariable({
				name: variable.name!,
				variable_name: variable.variable_name!,
				value: variable.value!,
				dark_value: variable.dark_value || undefined,
				group: variable.group,
				type: variable.type || "Color",
			});
			updatedCount++;
		} catch (error) {
			console.error("Failed to update variable:", variable.variable_name, error);
			updateErrors++;
		}
	}

	for (const variable of newVariables) {
		try {
			await createVar({
				variable_name: variable.variable_name!,
				value: variable.value!,
				dark_value: variable.dark_value || undefined,
				group: variable.group || undefined,
				type: variable.type || "Color",
			});
			createdCount++;
		} catch (error) {
			console.error("Failed to create variable:", variable.variable_name, error);
			createErrors++;
		}
	}

	// CSV import mutates variables outside the table; rebuild rows from fresh store data
	resetRowObjects();

	if (createdCount > 0) toast.success(`Successfully created ${createdCount} variable(s)`);
	if (updatedCount > 0) toast.success(`Successfully updated ${updatedCount} variable(s)`);
	if (createErrors > 0) toast.error(`Failed to create ${createErrors} variable(s)`);
	if (updateErrors > 0) toast.error(`Failed to update ${updateErrors} variable(s)`);
	if (invalidCount > 0) toast.warning(`Skipped ${invalidCount} invalid entries`);
	if (standardCount > 0) toast.warning(`Skipped ${standardCount} standard variable(s) (read-only)`);

	if (csvFileInput.value) csvFileInput.value.value = "";
};

const downloadSampleCSV = () => {
	const sampleData = [
		["Variable Name", "Light Mode", "Dark Mode", "Group"],
		["primary-color", "#3b82f6", "#60a5fa", "Brand"],
		["secondary-color", "#10b981", "#34d399", "Brand"],
		["background-color", "#ffffff", "#1f2937", "Surface"],
		["text-color", "#111827", "#f9fafb", ""],
	];

	const csvContent = sampleData.map((row) => row.join(",")).join("\n");
	const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
	const link = document.createElement("a");
	const url = URL.createObjectURL(blob);

	link.setAttribute("href", url);
	link.setAttribute("download", "sample-variables.csv");
	link.style.visibility = "hidden";
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
	toast.success("Sample CSV downloaded");
};
</script>
