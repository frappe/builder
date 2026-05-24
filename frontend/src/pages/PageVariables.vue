<template>
	<div class="flex h-screen flex-col bg-surface-white">
		<header class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-2">
			<router-link
				:to="{ name: 'builder', params: { pageId: route.params.pageId || 'new' } }"
				class="flex items-center text-sm text-ink-gray-7 hover:text-ink-gray-9">
				<span class="lucide-arrow-left mr-2 h-4 w-4" aria-hidden="true" />
				Back to builder
			</router-link>
			<h1 class="text-sm font-semibold text-ink-gray-9">Variables</h1>
			<div class="flex items-center gap-2">
				<BuilderInput
					:modelValue="searchQuery"
					@update:modelValue="(val: string) => (searchQuery = val)"
					type="text"
					placeholder="Search variables"
					class="w-56"
					icon-left="search" />
				<Button @click="addNewVariable" variant="solid" icon-left="plus">New variable</Button>
			</div>
		</header>

		<div class="flex flex-1 overflow-hidden">
			<aside class="w-56 shrink-0 overflow-y-auto border-r border-outline-gray-1 p-3">
				<div class="mb-2 text-xs font-medium uppercase text-ink-gray-5">Groups</div>
				<ul class="text-sm">
					<li>
						<button
							class="w-full rounded px-2 py-1 text-left"
							:class="
								selectedGroup === null
									? 'bg-surface-gray-2 text-ink-gray-9'
									: 'text-ink-gray-7 hover:bg-surface-gray-1'
							"
							@click="selectedGroup = null">
							All variables
							<span class="float-right text-xs text-ink-gray-5">{{ variables.length }}</span>
						</button>
					</li>
					<GroupNode
						v-for="node in groupTree"
						:key="node.path"
						:node="node"
						:depth="0"
						:selected="selectedGroup"
						@select="(g) => (selectedGroup = g)" />
				</ul>
			</aside>

			<section class="flex-1 overflow-y-auto p-4" @click="stopEditing">
				<ListView :columns="columns" :rows="rows" row-key="id" :options="listViewOptions" class="w-full">
					<template #cell="{ column, row }">
						<div v-if="column.key === 'variable_name'" class="flex items-center gap-2">
							<Tooltip v-if="row.is_standard" text="Standard variable (read-only)" placement="top">
								<span class="lucide-info h-4 w-4 text-ink-gray-5" aria-hidden="true" />
							</Tooltip>
							<BuilderInput
								v-if="isEditing('name', row.id) || row.isNew"
								:modelValue="row.variable_name"
								@update:modelValue="(v: string) => onLabelEdit(row, v)"
								@blur="() => (row.isNew ? createFromRow(row) : stopEditing())"
								@keydown.enter.prevent="() => (row.isNew ? createFromRow(row) : stopEditing())"
								type="text"
								placeholder="Variable name"
								@click.stop
								class="w-full"
								autofocus />
							<span
								v-else
								class="cursor-pointer rounded px-2 py-1 text-sm text-ink-gray-9"
								:class="{ 'cursor-not-allowed opacity-60': row.is_standard }"
								@click.stop="startEditing('name', row.id, row.is_standard)">
								{{ row.variable_name || "Enter name" }}
							</span>
						</div>

						<div v-else-if="column.key === 'group'" class="text-sm text-ink-gray-7">
							<BuilderInput
								v-if="isEditing('group', row.id) || row.isNew"
								:modelValue="row.group || ''"
								@update:modelValue="(v: string) => onGroupEdit(row, v)"
								@blur="stopEditing"
								@keydown.enter.prevent="stopEditing"
								type="text"
								placeholder="e.g. brand/semantic"
								@click.stop
								class="w-full" />
							<span
								v-else
								class="cursor-pointer rounded px-2 py-1"
								:class="{ 'cursor-not-allowed opacity-60': row.is_standard }"
								@click.stop="startEditing('group', row.id, row.is_standard)">
								{{ row.group || "—" }}
							</span>
						</div>

						<div v-else-if="column.key === 'type'" class="text-sm text-ink-gray-7">
							<select
								v-if="!row.is_standard"
								:value="row.type || 'Color'"
								@change="
									onTypeChange(row, ($event.target as HTMLSelectElement).value as 'Color' | 'Dimension')
								"
								@click.stop
								class="rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-sm">
								<option value="Color">Color</option>
								<option value="Dimension">Dimension</option>
							</select>
							<span v-else class="opacity-60">{{ row.type }}</span>
						</div>

						<div v-else-if="column.key === 'light'" class="flex items-center gap-2">
							<ColorInput
								v-if="row.type === 'Color' && isEditing('light', row.id)"
								:show-picker-on-mount="true"
								:modelValue="row.value || '#ffffff'"
								@update:modelValue="(v) => updateColor(row, v, 'light')"
								:show-color-variable-options="false"
								@keyup.enter="stopEditing"
								@click.stop
								class="w-[140px]" />
							<template v-else>
								<div
									v-if="row.type === 'Color'"
									class="h-4 w-4 cursor-pointer rounded-full border border-outline-gray-2"
									:style="{ backgroundColor: resolveVariableValue(row.value || '') }"
									@click.stop="!row.is_standard && startEditing('light', row.id, row.is_standard)"></div>
								<BuilderInput
									v-if="row.type === 'Dimension' && isEditing('light', row.id)"
									:modelValue="row.value"
									@update:modelValue="(v: string) => updateColor(row, v, 'light')"
									@blur="stopEditing"
									@keydown.enter.prevent="stopEditing"
									type="text"
									placeholder="e.g. 16px"
									@click.stop
									class="w-[140px]" />
								<span
									v-else
									class="cursor-pointer rounded py-1 font-mono text-sm text-ink-gray-7"
									:class="{ 'cursor-not-allowed opacity-60': row.is_standard }"
									@click.stop="startEditing('light', row.id, row.is_standard)">
									{{ row.value || "—" }}
								</span>
							</template>
						</div>

						<div v-else-if="column.key === 'dark'" class="flex items-center gap-2">
							<template v-if="row.type === 'Color'">
								<ColorInput
									v-if="isEditing('dark', row.id)"
									:show-picker-on-mount="true"
									:modelValue="row.dark_value || row.value || '#000000'"
									@update:modelValue="(v) => updateColor(row, v, 'dark')"
									:show-color-variable-options="false"
									@keyup.enter="stopEditing"
									@click.stop
									class="w-[140px]" />
								<template v-else>
									<div
										class="h-4 w-4 cursor-pointer rounded-full border border-outline-gray-2"
										:style="{ backgroundColor: resolveVariableValue(row.dark_value || row.value || '') }"
										@click.stop="!row.is_standard && startEditing('dark', row.id, row.is_standard)"></div>
									<span
										class="cursor-pointer rounded py-1 font-mono text-sm text-ink-gray-7"
										:class="{ 'cursor-not-allowed opacity-60': row.is_standard }"
										@click.stop="startEditing('dark', row.id, row.is_standard)">
										{{ row.dark_value || "—" }}
									</span>
								</template>
							</template>
							<span v-else class="text-sm text-ink-gray-5">—</span>
						</div>

						<div v-else-if="column.key === 'usage'" class="text-sm text-ink-gray-7">
							<span v-if="row.usage === undefined" class="text-ink-gray-4">…</span>
							<span v-else-if="row.usage === 0" class="text-ink-gray-4">Unused</span>
							<span v-else>{{ row.usage }}</span>
						</div>

						<div v-else-if="column.key === 'ref'" class="font-mono text-sm text-ink-gray-7">
							<button
								v-if="!row.isNew"
								class="rounded px-2 py-1 hover:bg-surface-gray-2"
								@click.stop="copyReference(row)"
								title="Copy CSS reference">
								var(--{{ row.id }})
							</button>
						</div>

						<div v-else-if="column.key === 'actions'" class="flex items-center gap-1">
							<BuilderButton
								v-if="!row.is_standard"
								variant="ghost"
								@click.stop="deleteRow(row)"
								title="Delete">
								<span class="lucide-trash-2 h-3 w-3" aria-hidden="true" />
							</BuilderButton>
						</div>
					</template>
				</ListView>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import BuilderButton from "@/components/Controls/BuilderButton.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import { BuilderVariable } from "@/types/doctypes";
import { confirm } from "@/utils/helpers";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { useDebounceFn } from "@vueuse/core";
import { Button, ListView, Tooltip, createResource, toast } from "frappe-ui";
import { computed, nextTick, ref } from "vue";
import { useRoute } from "vue-router";
import GroupNode from "@/components/VariableGroupNode.vue";

const route = useRoute();
const {
	resolveVariableValue,
	createVariable: createVar,
	updateVariable,
	deleteVariable,
	variables,
} = useBuilderVariable();

const searchQuery = ref("");
const selectedGroup = ref<string | null>(null);
const editingCell = ref<string | null>(null);
const nextNewId = ref(1);
const newRow = ref<Partial<BuilderVariable> | null>(null);
const usageCache = ref<Record<string, number>>({});

type Row = Partial<BuilderVariable> & { id: string; isNew: boolean; usage?: number };

const columns = [
	{ label: "Name", key: "variable_name", width: "200px" },
	{ label: "Group", key: "group", width: "180px" },
	{ label: "Type", key: "type", width: "120px" },
	{ label: "Light", key: "light", width: "160px" },
	{ label: "Dark", key: "dark", width: "160px" },
	{ label: "Reference", key: "ref", width: "200px" },
	{ label: "Used", key: "usage", width: "80px" },
	{ label: "", key: "actions", width: "40px" },
];

const listViewOptions = {
	selectable: false,
	showTooltip: false,
	resizeColumn: false,
	enableActive: false,
	emptyState: {
		title: "No Variables",
		description: "Click 'New variable' to add one.",
	},
};

interface GroupTreeNode {
	name: string;
	path: string;
	count: number;
	children: GroupTreeNode[];
}

const groupTree = computed<GroupTreeNode[]>(() => {
	const root: GroupTreeNode = { name: "", path: "", count: 0, children: [] };
	for (const v of variables.value) {
		const group = (v.group || "").trim();
		if (!group) continue;
		const segments = group
			.split("/")
			.map((s) => s.trim())
			.filter(Boolean);
		let cur = root;
		const acc: string[] = [];
		for (const seg of segments) {
			acc.push(seg);
			const path = acc.join("/");
			let child = cur.children.find((c) => c.name === seg);
			if (!child) {
				child = { name: seg, path, count: 0, children: [] };
				cur.children.push(child);
			}
			child.count++;
			cur = child;
		}
	}
	return root.children;
});

const rows = computed<Row[]>(() => {
	const q = searchQuery.value.trim().toLowerCase();
	let filtered = variables.value as BuilderVariable[];
	if (selectedGroup.value !== null) {
		const prefix = selectedGroup.value;
		filtered = filtered.filter((v) => {
			const g = v.group || "";
			return g === prefix || g.startsWith(prefix + "/");
		});
	}
	if (q) {
		filtered = filtered.filter(
			(v) =>
				v.variable_name?.toLowerCase().includes(q) ||
				v.group?.toLowerCase().includes(q) ||
				v.description?.toLowerCase().includes(q),
		);
	}
	const out: Row[] = filtered.map((v) => ({
		...v,
		id: v.name as string,
		isNew: false,
		usage: usageCache.value[v.name as string],
	}));
	if (newRow.value) {
		out.unshift({ ...newRow.value, id: `new-${nextNewId.value}`, isNew: true });
	}
	return out;
});

const isEditing = (type: string, id: string) => editingCell.value === `${type}-${id}`;
const stopEditing = () => (editingCell.value = null);
const startEditing = (type: string, id: string, isStandard: boolean) => {
	if (!isStandard) editingCell.value = `${type}-${id}`;
};

const addNewVariable = async () => {
	nextNewId.value++;
	newRow.value = {
		variable_name: "",
		value: "#ffffff",
		dark_value: "",
		type: "Color",
		group: selectedGroup.value || "",
	};
	await nextTick();
	editingCell.value = `name-new-${nextNewId.value}`;
};

const onLabelEdit = (row: Row, val: string) => {
	row.variable_name = val;
	if (!row.isNew) debouncedSave(row);
};

const onGroupEdit = (row: Row, val: string) => {
	row.group = val;
	if (!row.isNew) debouncedSave(row);
};

const onTypeChange = (row: Row, val: "Color" | "Dimension") => {
	row.type = val;
	if (val === "Dimension") row.dark_value = "";
	if (!row.isNew) debouncedSave(row);
};

const updateColor = async (row: Row, value: string | null, mode: "light" | "dark") => {
	if (mode === "light") row.value = value || "";
	else row.dark_value = value || "";
	if (row.isNew) {
		await createFromRow(row);
	} else {
		debouncedSave(row);
	}
};

const debouncedSave = useDebounceFn(async (row: Row) => {
	if (!row.name) return;
	try {
		await updateVariable({
			name: row.name,
			variable_name: row.variable_name!,
			value: row.value!,
			dark_value: row.dark_value || undefined,
			type: row.type || "Color",
			group: row.group || undefined,
			description: row.description || undefined,
		});
	} catch (e) {
		toast.error((e as Error).message || "Failed to update variable");
	}
}, 300);

const createFromRow = async (row: Row) => {
	if (!row.isNew || !row.variable_name?.trim()) return;
	try {
		await createVar({
			variable_name: row.variable_name!,
			value: row.value || "#ffffff",
			dark_value: row.dark_value || undefined,
			type: row.type || "Color",
			group: row.group || undefined,
		});
		newRow.value = null;
		toast.success("Variable created");
	} catch (e) {
		toast.error((e as Error).message || "Failed to create variable");
	}
};

const deleteRow = async (row: Row) => {
	if (row.isNew) {
		newRow.value = null;
		return;
	}
	if (!row.name) return;
	const usage = await fetchUsage(row.name);
	const usageNote =
		usage > 0
			? `\n\nThis variable is referenced in ${usage} block JSON(s). Block fallback values (if any) will be used instead.`
			: "";
	const confirmed = await confirm(`Delete "${row.variable_name}"?${usageNote}`);
	if (!confirmed) return;
	try {
		await deleteVariable(row.name);
		delete usageCache.value[row.name];
		toast.success("Variable deleted");
	} catch (e) {
		toast.error((e as Error).message || "Failed to delete variable");
	}
};

const copyReference = (row: Row) => {
	const ref = `var(--${row.id}${row.value ? `, ${row.value}` : ""})`;
	navigator.clipboard.writeText(ref);
	toast.success(`Copied: ${ref}`);
};

const fetchUsage = async (name: string): Promise<number> => {
	if (usageCache.value[name] !== undefined) return usageCache.value[name];
	try {
		const res = await createResource({
			url: "builder.api.get_builder_variable_usage",
			params: { name },
			cache: false,
		}).fetch();
		const total = (res?.pages ?? 0) + (res?.components ?? 0);
		usageCache.value[name] = total;
		return total;
	} catch (e) {
		console.error("usage fetch failed", e);
		return 0;
	}
};

// Lazy-load usage counts after first paint so the table doesn't block.
const primeUsageCounts = useDebounceFn(async () => {
	const targets = variables.value.slice(0, 50);
	for (const v of targets) {
		if (v.name && usageCache.value[v.name] === undefined) {
			await fetchUsage(v.name);
		}
	}
}, 200);

primeUsageCounts();
</script>
