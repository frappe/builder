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
						<p class="mt-1 text-sm text-ink-gray-6">
							Upload CSV with columns: Variable Name, Light Mode, Dark Mode (optional)
							<button
								@click="downloadSampleCSV"
								variant="subtle"
								class="ml-2 text-xs text-blue-600 underline hover:text-blue-700">
								Download sample
							</button>
						</p>
					</div>
					<div class="flex items-center gap-2">
						<input ref="csvFileInput" type="file" accept=".csv" @change="handleCSVUpload" class="hidden" />
						<Button @click="triggerCSVUpload" variant="outline" theme="gray" size="sm" icon-left="upload">
							Upload CSV
						</Button>
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
					class="max-h-[60vh]">
					<template #cell="{ column, row }">
						<div v-if="column.key === 'variable_name'" class="flex items-center gap-2">
							<Tooltip
								v-if="row._originalVariable.is_standard && !row._originalVariable.isOverride"
								text="This is a standard variable. Create an override to customize it."
								placement="top">
								<FeatherIcon name="info" class="h-4 w-4 text-ink-gray-5" />
							</Tooltip>
							<BuilderInput
								v-model="row._originalVariable.variable_name"
								type="text"
								placeholder="Enter variable name"
								class="w-fit"
								:class="{
									'opacity-60': row._originalVariable.is_standard && !row._originalVariable.isOverride,
								}"
								:hideClearButton="
									Boolean(row._originalVariable.is_standard && !row._originalVariable.isOverride)
								"
								:disabled="Boolean(row._originalVariable.is_standard && !row._originalVariable.isOverride)"
								@input="(value: string) => handleVariableNameChange(row._originalVariable, value)" />
						</div>

						<div v-else-if="column.key === 'light_color'" class="flex items-center gap-3">
							<ColorPicker
								:modelValue="(row._originalVariable.value as HashString) || '#ffffff'"
								placement="bottom-start"
								:showInput="true"
								@update:modelValue="(value) => handleColorUpdate(row._originalVariable, value, 'light')">
								<template #target="{ togglePopover }">
									<div
										class="h-5 w-5 cursor-pointer rounded-full border border-outline-gray-2"
										:style="{ backgroundColor: resolveVariableValue(row._originalVariable.value || '') }"
										@click="togglePopover"
										title="Click to edit light mode color"></div>
								</template>
							</ColorPicker>
							<span class="text-sm text-ink-gray-7">{{ row._originalVariable.value || "#ffffff" }}</span>
						</div>

						<div v-else-if="column.key === 'dark_color'" class="flex items-center gap-3">
							<ColorPicker
								:modelValue="
									(row._originalVariable.dark_value as HashString) ||
									(row._originalVariable.value as HashString) ||
									'#000000'
								"
								placement="bottom-start"
								:showInput="true"
								@update:modelValue="(value) => handleColorUpdate(row._originalVariable, value, 'dark')">
								<template #target="{ togglePopover }">
									<div
										class="h-5 w-5 cursor-pointer rounded-full border border-outline-gray-2"
										:style="{
											backgroundColor: resolveVariableValue(
												row._originalVariable.dark_value || row._originalVariable.value || '',
											),
										}"
										@click="togglePopover"
										title="Click to edit dark mode color"></div>
								</template>
							</ColorPicker>
							<span class="text-sm text-ink-gray-7">
								{{ row._originalVariable.dark_value || row._originalVariable.value || "#000000" }}
							</span>
						</div>

						<div v-else-if="column.key === 'actions'" class="flex items-center justify-center gap-1">
							<template v-if="row._originalVariable.is_standard && !row._originalVariable.isOverride">
								<Tooltip text="Create override to customize this standard variable" placement="top">
									<BuilderButton
										variant="subtle"
										class="text-ink-gray-6 hover:text-ink-gray-9"
										@click="createOverride(row._originalVariable)"
										title="Override Standard Variable">
										<FeatherIcon name="copy" class="h-3 w-3" />
									</BuilderButton>
								</Tooltip>
							</template>
							<template v-else>
								<BuilderButton
									v-if="!row._originalVariable.name"
									variant="subtle"
									class="text-ink-gray-6 hover:text-green-600"
									@click="createVariable(row._originalVariable)"
									:disabled="!canSaveVariable(row._originalVariable)"
									title="Create Variable">
									<FeatherIcon name="plus" class="h-3 w-3" />
								</BuilderButton>
								<BuilderButton
									variant="subtle"
									class="text-ink-gray-6 hover:text-red-600"
									@click="deleteVariableRow(row._originalVariable, row._index)"
									title="Delete Variable">
									<FeatherIcon name="trash-2" class="h-3 w-3" />
								</BuilderButton>
							</template>
						</div>
					</template>
				</ListView>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import BuilderButton from "@/components/Controls/BuilderButton.vue";
import ColorPicker from "@/components/Controls/ColorPicker.vue";
import { BuilderVariable } from "@/types/Builder/BuilderVariable";
import { confirm } from "@/utils/helpers";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { useDebounceFn } from "@vueuse/core";
import { Button, Dialog, FeatherIcon, ListView, Tooltip } from "frappe-ui";
import { computed, ref, watch } from "vue";
import { toast } from "vue-sonner";

interface EditableVariable extends Partial<BuilderVariable> {
	isOverride?: boolean;
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

// ListView configuration
const columns = [
	{
		label: "Variable Name",
		key: "variable_name",
		width: "4fr",
	},
	{
		label: "Light Mode",
		key: "light_color",
		width: "1fr",
	},
	{
		label: "Dark Mode",
		key: "dark_color",
		width: "1fr",
	},
	{
		label: "Actions",
		key: "actions",
		width: "80px",
	},
];

const listViewRows = computed(() => {
	return editableVariables.value.map((variable, index) => ({
		...variable,
		id: variable.name || `new-${index}`,
		_originalVariable: variable,
		_index: index,
	}));
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

// Initialize editable variables when dialog opens
watch(
	isOpen,
	(open) => {
		if (open) {
			initializeVariables();
		}
	},
	{ immediate: true },
);

const initializeVariables = () => {
	editableVariables.value = variables.value.map((variable: BuilderVariable) => ({
		...variable,
		isOverride: false,
		isNew: false,
	}));
};

const addNewVariable = () => {
	// Add new variable at the top of the list
	editableVariables.value.unshift({
		variable_name: "",
		value: "#ffffff",
		dark_value: "",
		type: "Color",
		isNew: true,
	});
};

const triggerCSVUpload = () => {
	csvFileInput.value?.click();
};

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

	// Parse and validate variables first
	const newVariables: EditableVariable[] = [];
	let duplicateCount = 0;
	let invalidCount = 0;

	for (let i = 1; i < lines.length; i++) {
		const values = lines[i].split(",").map((v) => v.trim());
		const variableName = values[nameIndex]?.replace(/"/g, "");
		const lightValue = values[lightIndex]?.replace(/"/g, "");
		const darkValue = darkIndex !== -1 ? values[darkIndex]?.replace(/"/g, "") : "";

		if (variableName && lightValue) {
			// Check if variable already exists
			const exists = editableVariables.value.some((v) => v.variable_name === variableName);
			if (!exists) {
				newVariables.push({
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
		if (duplicateCount > 0) {
			toast.warning(`All ${duplicateCount} variables already exist`);
		}
		if (invalidCount > 0) {
			toast.error(`${invalidCount} entries were invalid (missing name or light mode color)`);
		}
		// Reset file input
		if (csvFileInput.value) {
			csvFileInput.value.value = "";
		}
		return;
	}

	// Show confirmation dialog
	const confirmed = await confirm(
		`Do you want to create ${newVariables.length} new variable(s)?${
			duplicateCount > 0 ? ` (${duplicateCount} duplicates will be skipped)` : ""
		}${invalidCount > 0 ? ` (${invalidCount} invalid entries will be skipped)` : ""}`,
	);

	if (!confirmed) {
		// Reset file input
		if (csvFileInput.value) {
			csvFileInput.value.value = "";
		}
		return;
	}

	// Create variables directly
	let successCount = 0;
	let errorCount = 0;
	const createdVariables: EditableVariable[] = [];

	for (const variable of newVariables) {
		try {
			const newVar = await createVar({
				variable_name: variable.variable_name!,
				value: variable.value!,
				dark_value: variable.dark_value || undefined,
				type: variable.type || "Color",
			});

			createdVariables.push({
				...newVar,
				isNew: false,
			});
			successCount++;
		} catch (error) {
			console.error("Failed to create variable:", variable.variable_name, error);
			errorCount++;
		}
	}

	// Add created variables to the top of the list
	if (createdVariables.length > 0) {
		editableVariables.value = [...createdVariables, ...editableVariables.value];
	}

	// Show results
	if (successCount > 0) {
		toast.success(`Successfully created ${successCount} variables`);
	}
	if (errorCount > 0) {
		toast.error(`Failed to create ${errorCount} variables`);
	}
	if (duplicateCount > 0) {
		toast.warning(`Skipped ${duplicateCount} duplicate entries`);
	}
	if (invalidCount > 0) {
		toast.warning(`Skipped ${invalidCount} invalid entries`);
	}

	// Reset file input
	if (csvFileInput.value) {
		csvFileInput.value.value = "";
	}
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

const createOverride = (standardVariable: EditableVariable) => {
	const override: EditableVariable = {
		variable_name: standardVariable.variable_name,
		value: standardVariable.value,
		dark_value: standardVariable.dark_value || "",
		type: standardVariable.type || "Color",
		isOverride: true,
		isNew: true,
	};

	editableVariables.value.push(override);
	toast.info("Override created. Modify the values and save to customize this standard variable.");
};

const handleVariableNameChange = (variable: EditableVariable, value: string) => {
	variable.variable_name = value;
};

const handleColorUpdate = useDebounceFn(
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

const canSaveVariable = (variable: EditableVariable): boolean => {
	return !!(variable.variable_name?.trim() && variable.value?.trim());
};

const createVariable = async (variable: EditableVariable) => {
	if (!canSaveVariable(variable)) {
		toast.error("Variable name and light mode color are required");
		return;
	}

	try {
		const newVar = await createVar({
			variable_name: variable.variable_name!,
			value: variable.value!,
			dark_value: variable.dark_value || undefined,
			type: variable.type || "Color",
		});

		// Update the local variable with the created data
		Object.assign(variable, newVar, { isNew: false });
		toast.success("Variable created successfully");
	} catch (error) {
		toast.error((error as Error).message || "Failed to create variable");
	}
};

const saveVariable = async (variable: EditableVariable) => {
	if (!variable.name || !canSaveVariable(variable)) {
		toast.error("Cannot save variable: missing required fields");
		return;
	}

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

const deleteVariableRow = async (variable: EditableVariable, index: number) => {
	if (variable.isNew) {
		// Just remove from local array if it's a new unsaved variable
		const actualIndex = editableVariables.value.findIndex((v) => v === variable);
		if (actualIndex !== -1) {
			editableVariables.value.splice(actualIndex, 1);
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
		const actualIndex = editableVariables.value.findIndex((v) => v === variable);
		if (actualIndex !== -1) {
			editableVariables.value.splice(actualIndex, 1);
		}
		toast.success("Variable deleted successfully");
	} catch (error) {
		toast.error((error as Error).message || "Failed to delete variable");
	}
};
</script>
