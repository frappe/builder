<template>
	<Dialog
		v-model="isOpen"
		:options="{ title: 'Variables', size: '6xl' }"
		:disable-outside-click-to-close="true">
		<template #body-content>
			<div>
				<div class="mb-6 flex items-center justify-between">
					<div>
						<h2>Manage Variables</h2>
					</div>
					<div class="flex items-center gap-2">
						<Button @click="addNewVariable" variant="solid" theme="gray" size="sm" icon-left="plus">
							Add Variable
						</Button>
					</div>
				</div>

				<ListView
					:columns="columns"
					:rows="listViewRows"
					row-key="id"
					:options="listViewOptions"
					class="max-h-[60vh]"
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
								v-model="row.variable_name"
								type="text"
								placeholder="Enter variable name"
								@blur="stopEditing"
								@keyup.enter="stopEditing"
								@click.stop
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
								@blur="stopEditing"
								@keyup.enter="stopEditing"
								@click.stop
								class="w-full" />

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
								@blur="stopEditing"
								@keyup.enter="stopEditing"
								@click.stop
								class="w-full" />

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
									variant="subtle"
									class="text-ink-gray-6"
									@click="createVariable(row)"
									title="Create Variable">
									<FeatherIcon name="check" class="h-3 w-3" />
								</BuilderButton>
								<BuilderButton
									variant="subtle"
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
	</Dialog>
</template>

<script setup lang="ts">
import BuilderButton from "@/components/Controls/BuilderButton.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import { BuilderVariable } from "@/types/Builder/BuilderVariable";
import { confirm } from "@/utils/helpers";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { useDebounceFn } from "@vueuse/core";
import { Button, Dialog, FeatherIcon, ListView, Tooltip } from "frappe-ui";
import { computed, nextTick, ref, watch } from "vue";
import { toast } from "vue-sonner";

interface EditableVariable extends Partial<BuilderVariable> {
	isNew?: boolean;
}

const props = defineProps<{
	modelValue: boolean;
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

const isOpen = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

const editableVariables = ref<EditableVariable[]>([]);
const csvFileInput = ref<HTMLInputElement>();
const editingCell = ref<string | null>(null);
const nextNewId = ref(1);

// ListView configuration
const columns = [
	{ label: "Variable Name", key: "variable_name" },
	{ label: "Light Mode", key: "light_color" },
	{ label: "Dark Mode", key: "dark_color" },
	{ label: "Actions", key: "actions", width: "80px" },
];

const listViewRows = computed(() =>
	editableVariables.value.map((variable) => ({
		...variable,
		id: variable.name || variable.id || `new-${nextNewId.value}`,
	})),
);

const listViewOptions = {
	selectable: false,
	showTooltip: false,
	resizeColumn: false,
	emptyState: {
		title: "No Variables",
		description: "No variables found. Click 'Add Variable' to create your first one.",
	},
};

// Initialize variables when dialog opens
watch(
	isOpen,
	(open) => {
		if (open) {
			editableVariables.value = [
				...variables.value.map((variable: BuilderVariable) => ({
					...variable,
					isNew: false,
				})),
			];
		}
	},
	{ immediate: true },
);

// Watch for changes in the original variables and sync
watch(
	variables,
	(newVariables) => {
		if (isOpen.value) {
			// Merge existing variables with new ones, preserving any unsaved new variables
			const existingNewVars = editableVariables.value.filter((v) => v.isNew);
			const syncedVars = newVariables.map((variable: BuilderVariable) => ({
				...variable,
				isNew: false,
			}));
			editableVariables.value = [...existingNewVars, ...syncedVars];
		}
	},
	{ deep: true },
);

// Editing helpers
const isEditing = (type: string, id: string) => editingCell.value === `${type}-${id}`;
const stopEditing = () => (editingCell.value = null);
const startEditing = (type: string, id: string, isStandard: boolean) => {
	if (!isStandard) editingCell.value = `${type}-${id}`;
};

const getNameDisplayClasses = (row: EditableVariable) => ({
	"opacity-60": row.is_standard,
	"cursor-not-allowed": row.is_standard,
});

const getNameTooltip = (row: EditableVariable) =>
	row.is_standard ? "Standard variable (read-only)" : "Click to edit";

const addNewVariable = async () => {
	const newId = `new-${nextNewId.value}`;
	nextNewId.value++;

	const newVariable: EditableVariable = {
		id: newId,
		variable_name: "",
		value: "#ffffff",
		dark_value: "",
		type: "Color",
		isNew: true,
	};

	editableVariables.value.unshift(newVariable);

	// Auto-focus on the new variable name field
	await nextTick();
	editingCell.value = `name-${newId}`;
};

const updateColor = useDebounceFn(
	async (variable: EditableVariable, value: string | null, mode: "light" | "dark") => {
		if (mode === "light") {
			variable.value = value || "";
		} else {
			variable.dark_value = value || "";
		}

		// Auto-save for existing variables
		if (variable.name && !variable.isNew) {
			try {
				await saveVariable(variable);
			} catch (error) {
				console.error("Failed to update variable:", error);
			}
		}
	},
	300,
);

const createVariable = async (variable: EditableVariable) => {
	if (!variable.variable_name?.trim()) {
		toast.error("Variable name is required");
		return;
	}

	try {
		const newVar = await createVar({
			variable_name: variable.variable_name!,
			value: variable.value!,
			dark_value: variable.dark_value || undefined,
			type: variable.type || "Color",
		});

		// Find the variable in our list and update it
		const index = editableVariables.value.findIndex((v) => v.id === variable.id);
		if (index !== -1) {
			editableVariables.value[index] = { ...newVar, isNew: false };
		}

		toast.success("Variable created successfully");
	} catch (error) {
		toast.error((error as Error).message || "Failed to create variable");
	}
};

const saveVariable = async (variable: EditableVariable) => {
	if (!variable.name) return;

	try {
		await updateVariable({
			name: variable.name,
			variable_name: variable.variable_name!,
			value: variable.value!,
			dark_value: variable.dark_value || undefined,
			type: variable.type || "Color",
		});
		toast.success("Variable updated successfully");
	} catch (error) {
		toast.error((error as Error).message || "Failed to update variable");
	}
};

const deleteVariableRow = async (variable: EditableVariable) => {
	if (variable.isNew) {
		const index = editableVariables.value.findIndex((v) => v.id === variable.id);
		if (index !== -1) {
			editableVariables.value.splice(index, 1);
		}
		return;
	}

	if (!variable.name) return;

	const confirmed = await confirm(
		`Are you sure you want to delete the variable "${variable.variable_name}"?`,
	);
	if (!confirmed) return;

	try {
		await deleteVariable(variable.name);
		const index = editableVariables.value.findIndex((v) => v.id === variable.id || v.name === variable.name);
		if (index !== -1) {
			editableVariables.value.splice(index, 1);
		}
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

	const newVariables: EditableVariable[] = [];
	let duplicateCount = 0;
	let invalidCount = 0;

	for (let i = 1; i < lines.length; i++) {
		const values = lines[i].split(",").map((v) => v.trim().replace(/"/g, ""));
		const variableName = values[nameIndex];
		const lightValue = values[lightIndex];
		const darkValue = darkIndex !== -1 ? values[darkIndex] : "";

		if (variableName && lightValue) {
			const exists = editableVariables.value.some((v) => v.variable_name === variableName);
			if (!exists) {
				newVariables.push({
					id: `csv-${nextNewId.value++}`,
					variable_name: variableName,
					value: lightValue,
					dark_value: darkValue,
					type: "Color",
				});
			} else {
				duplicateCount++;
			}
		} else {
			invalidCount++;
		}
	}

	if (newVariables.length === 0) {
		if (duplicateCount > 0) toast.warning(`All ${duplicateCount} variables already exist`);
		if (invalidCount > 0) toast.error(`${invalidCount} entries were invalid`);
		if (csvFileInput.value) csvFileInput.value.value = "";
		return;
	}

	const confirmed = await confirm(
		`Create ${newVariables.length} new variable(s)?${
			duplicateCount > 0 ? ` (${duplicateCount} duplicates skipped)` : ""
		}${invalidCount > 0 ? ` (${invalidCount} invalid entries skipped)` : ""}`,
	);

	if (!confirmed) {
		if (csvFileInput.value) csvFileInput.value.value = "";
		return;
	}

	let successCount = 0;
	let errorCount = 0;

	for (const variable of newVariables) {
		try {
			const newVar = await createVar({
				variable_name: variable.variable_name!,
				value: variable.value!,
				dark_value: variable.dark_value || undefined,
				type: variable.type || "Color",
			});

			// Add to our editable variables list
			editableVariables.value.push({ ...newVar, isNew: false });
			successCount++;
		} catch (error) {
			console.error("Failed to create variable:", variable.variable_name, error);
			errorCount++;
		}
	}

	// Show results
	if (successCount > 0) toast.success(`Successfully created ${successCount} variables`);
	if (errorCount > 0) toast.error(`Failed to create ${errorCount} variables`);
	if (duplicateCount > 0) toast.warning(`Skipped ${duplicateCount} duplicate entries`);
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
