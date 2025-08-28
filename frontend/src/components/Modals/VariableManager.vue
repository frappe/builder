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
		:placement-offset="20"
		action-label="Add Variable"
		:action-handler="addNewVariable"
		placement="top-left">
		<template #header><h2 class="py-2 text-lg font-semibold">Manage Variables</h2></template>
		<template #content>
			<div>
				<ListView
					:columns="columns"
					:rows="listViewRows"
					row-key="id"
					:options="listViewOptions"
					class="max-h-[60vh] w-full"
					@click="stopEditing">
					<template #cell="{ column, row }">
						<div v-if="column.key === 'variable_name'" class="flex cursor-pointer items-center gap-2">
							<Tooltip
								v-if="row.is_standard"
								text="This is a standard variable. It cannot be modified or deleted."
								placement="top">
								<FeatherIcon name="info" class="h-4 w-4 text-ink-gray-5" />
							</Tooltip>
							<BuilderInput
								v-if="isEditing('name', row.id) || row.isNew"
								:modelValue="row.variable_name"
								@update:modelValue="
									(val: string) => {
										if (!row.isNew) {
											updateVariable({
												name: row.name,
												variable_name: val,
											});
											stopEditing();
										} else {
											row.variable_name = val;
										}
									}
								"
								type="text"
								placeholder="Enter variable name"
								@click.stop
								class="w-[130px]"
								autofocus />

							<span
								v-else
								class="rounded px-2 py-1 text-sm"
								:class="getNameDisplayClasses(row)"
								@click.stop="startEditing('name', row.id, row.is_standard)"
								:title="getNameTooltip(row)">
								{{ row.variable_name || "Enter variable name" }}
							</span>
						</div>

						<!-- Light Color Column -->
						<div v-else-if="column.key === 'light_color'" class="flex items-center gap-3">
							<ColorInput
								v-if="isEditing('light', row.id)"
								:show-picker-on-mount="true"
								:modelValue="row.value || '#ffffff'"
								@update:modelValue="(value) => updateColor(row, value, 'light')"
								:show-color-variable-options="false"
								@keyup.enter="stopEditing"
								@click.stop
								class="w-[120px]" />

							<template v-else>
								<div
									v-if="!row.is_standard"
									class="h-5 w-5 cursor-pointer rounded-full border border-outline-gray-2"
									:style="{ backgroundColor: resolveVariableValue(row.value || '') }"
									@click.stop="startEditing('light', row.id, row.is_standard)"
									:title="'Click to open color picker or edit'"></div>
								<div
									v-else
									class="h-5 w-5 rounded-full border border-outline-gray-2"
									:style="{ backgroundColor: resolveVariableValue(row.value || '') }"
									:title="'Standard variable (read-only)'"></div>
								<span
									class="cursor-pointer rounded py-1 text-sm text-ink-gray-7"
									:class="{ 'cursor-not-allowed opacity-60': row.is_standard }"
									@click.stop="startEditing('light', row.id, row.is_standard)"
									:title="row.is_standard ? 'Standard variable (read-only)' : 'Click to edit'">
									{{ row.value || "#ffffff" }}
								</span>
							</template>
						</div>

						<!-- Dark Color Column -->
						<div v-else-if="column.key === 'dark_color'" class="flex items-center gap-3">
							<ColorInput
								v-if="isEditing('dark', row.id)"
								:show-picker-on-mount="true"
								:modelValue="row.dark_value || row.value || '#000000'"
								@update:modelValue="(value) => updateColor(row, value, 'dark')"
								:show-color-variable-options="false"
								@keyup.enter="stopEditing"
								@click.stop
								class="w-[120px]" />

							<template v-else>
								<div
									v-if="!row.is_standard"
									class="h-5 w-5 cursor-pointer rounded-full border border-outline-gray-2"
									:style="{ backgroundColor: resolveVariableValue(row.dark_value || row.value || '') }"
									@click.stop="startEditing('dark', row.id, row.is_standard)"
									:title="'Click to open color picker or edit'"></div>

								<div
									v-else
									class="h-5 w-5 rounded-full border border-outline-gray-2"
									:style="{ backgroundColor: resolveVariableValue(row.dark_value || row.value || '') }"
									:title="'Standard variable (read-only)'"></div>

								<span
									class="cursor-pointer rounded py-1 text-sm text-ink-gray-7"
									:class="{ 'cursor-not-allowed opacity-60': row.is_standard }"
									@click.stop="startEditing('dark', row.id, row.is_standard)"
									:title="row.is_standard ? 'Standard variable (read-only)' : 'Click to edit'">
									{{ row.dark_value || row.value || "#000000" }}
								</span>
							</template>
						</div>

						<!-- Actions Column -->
						<div v-else-if="column.key === 'actions'" class="flex items-center justify-center gap-1">
							<template v-if="!row.is_standard">
								<BuilderButton
									v-if="row.isNew"
									variant="ghost"
									class="text-ink-gray-6"
									@click="createVariable(row)"
									title="Create Variable">
									<FeatherIcon name="check" class="h-3 w-3" />
								</BuilderButton>
								<BuilderButton
									variant="ghost"
									class="text-ink-gray-6 hover:text-red-600"
									@click="deleteVariableRow(row)"
									title="Delete Variable">
									<FeatherIcon name="trash-2" class="h-3 w-3" />
								</BuilderButton>
							</template>
						</div>
					</template>
				</ListView>
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
import BuilderButton from "@/components/Controls/BuilderButton.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import DraggablePopup from "@/components/Controls/DraggablePopup.vue";
import { BuilderVariable } from "@/types/Builder/BuilderVariable";
import { confirm } from "@/utils/helpers";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { useDebounceFn } from "@vueuse/core";
import { Button, FeatherIcon, ListView, Tooltip } from "frappe-ui";
import { computed, nextTick, ref } from "vue";
import { toast } from "vue-sonner";

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
const editingCell = ref<string | null>(null);
const nextNewId = ref(1);
const newVariable = ref<Partial<BuilderVariable> | null>(null);

const columns = [
	{ label: "Variable Name", key: "variable_name" },
	{ label: "Light Mode", key: "light_color" },
	{ label: "Dark Mode", key: "dark_color" },
	{ label: "", key: "actions", width: "40px" },
];

type ListViewRow = Partial<BuilderVariable> & { id: string; isNew: Boolean };

const listViewRows = computed(() => {
	const rows: ListViewRow[] = variables.value.map((variable) => ({
		...variable,
		id: variable.name || `new-${nextNewId.value}`,
		isNew: false,
	}));
	if (newVariable.value) {
		rows.unshift({
			...newVariable.value,
			id: `new-${nextNewId.value}`,
			isNew: true,
		});
	}

	return rows;
});

const listViewOptions = {
	selectable: false,
	showTooltip: false,
	resizeColumn: false,
	emptyState: {
		title: "No Variables",
		description: "No variables found. Click 'Add Variable' to create your first one.",
	},
};

// Editing helpers
const isEditing = (type: string, id: string) => editingCell.value === `${type}-${id}`;
const stopEditing = () => (editingCell.value = null);
const startEditing = (type: string, id: string, isStandard: boolean) => {
	if (!isStandard) editingCell.value = `${type}-${id}`;
};

const getNameDisplayClasses = (row: BuilderVariable) => ({
	"opacity-60": row.is_standard,
	"cursor-not-allowed": row.is_standard,
});

const getNameTooltip = (row: BuilderVariable) =>
	row.is_standard ? "Standard variable (read-only)" : "Click to edit";

const addNewVariable = async () => {
	nextNewId.value++;
	newVariable.value = {
		variable_name: "",
		value: "#ffffff",
		dark_value: "",
		type: "Color",
	};
	await nextTick();
};

const updateColor = async (row: ListViewRow, value: string | null, mode: "light" | "dark") => {
	if (mode === "light") {
		row.value = value || "";
	} else {
		row.dark_value = value || "";
	}

	if (row.name && !row.isNew) {
		debouncedSaveVariable(row);
	}
};

const debouncedSaveVariable = useDebounceFn(async (row: ListViewRow) => {
	try {
		await saveVariable(row);
	} catch (error) {
		console.error("Failed to update variable:", error);
	}
}, 300);

const createVariable = async (variable: BuilderVariable) => {
	if (!variable.variable_name?.trim()) {
		toast.error("Variable name is required");
		return;
	}

	try {
		await createVar({
			variable_name: variable.variable_name!,
			value: variable.value!,
			dark_value: variable.dark_value || undefined,
			type: variable.type || "Color",
		});
		newVariable.value = null;
		toast.success("Variable created successfully");
	} catch (error) {
		toast.error((error as Error).message || "Failed to create variable");
	}
};

const saveVariable = async (row: ListViewRow) => {
	if (!row.name) return;

	try {
		await updateVariable({
			name: row.name,
			variable_name: row.variable_name!,
			value: row.value!,
			dark_value: row.dark_value || undefined,
			type: row.type || "Color",
		});
		toast.success("Variable updated successfully");
	} catch (error) {
		toast.error((error as Error).message || "Failed to update variable");
	}
};

const deleteVariableRow = async (row: ListViewRow) => {
	console.log("delete", row);
	if (row.isNew) {
		newVariable.value = null;
		return;
	}

	if (!row.name) return;

	const confirmed = await confirm(`Are you sure you want to delete the variable "${row.variable_name}"?`);
	if (!confirmed) return;

	try {
		await deleteVariable(row.name);
		toast.success("Variable deleted successfully");
	} catch (error) {
		toast.error((error as Error).message || "Failed to delete variable");
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

	if (nameIndex === -1 || lightIndex === -1) {
		toast.error("CSV must contain 'Variable Name' and 'Light Mode' columns");
		return;
	}

	const newVariables: Partial<BuilderVariable>[] = [];
	const updateVariables: Partial<BuilderVariable & { name?: string }>[] = [];
	let invalidCount = 0;

	for (let i = 1; i < lines.length; i++) {
		const values = lines[i].split(",").map((v) => v.trim().replace(/"/g, ""));
		const variableName = values[nameIndex];
		const lightValue = values[lightIndex];
		const darkValue = darkIndex !== -1 ? values[darkIndex] : "";

		if (variableName && lightValue) {
			const existing = variables.value.find((v) => v.variable_name === variableName);
			if (!existing) {
				newVariables.push({
					variable_name: variableName,
					value: lightValue,
					dark_value: darkValue,
					type: "Color",
				});
			} else {
				updateVariables.push({
					name: existing.name,
					variable_name: variableName,
					value: lightValue,
					dark_value: darkValue,
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
	const confirmed = await confirm(
		`Create ${newVariables.length} new variable(s) and update ${
			updateVariables.length
		} existing variable(s)?${
			invalidCount > 0 ? ` (${invalidCount} invalid entries skipped)` : ""
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
				type: variable.type || "Color",
			});
			createdCount++;
		} catch (error) {
			console.error("Failed to create variable:", variable.variable_name, error);
			createErrors++;
		}
	}

	if (createdCount > 0) toast.success(`Successfully created ${createdCount} variable(s)`);
	if (updatedCount > 0) toast.success(`Successfully updated ${updatedCount} variable(s)`);
	if (createErrors > 0) toast.error(`Failed to create ${createErrors} variable(s)`);
	if (updateErrors > 0) toast.error(`Failed to update ${updateErrors} variable(s)`);
	if (invalidCount > 0) toast.warning(`Skipped ${invalidCount} invalid entries`);

	if (csvFileInput.value) csvFileInput.value.value = "";
};

const downloadSampleCSV = () => {
	const sampleData = [
		["Variable Name", "Light Mode", "Dark Mode"],
		["primary-color", "#3b82f6", "#60a5fa"],
		["secondary-color", "#10b981", "#34d399"],
		["background-color", "#ffffff", "#1f2937"],
		["text-color", "#111827", "#f9fafb"],
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
