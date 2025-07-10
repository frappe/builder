<template>
	<div class="flex flex-col gap-3">
		<div class="flex items-center justify-between">
			<h3 class="text-base font-medium text-ink-gray-9">Variables</h3>
			<button class="text-sm text-ink-gray-7 hover:text-ink-gray-9" @click="openDialog()">
				<FeatherIcon name="plus" class="size-4" />
			</button>
		</div>
		<div v-if="!variables.length" class="py-2 text-sm italic text-ink-gray-6">No Variables found</div>
		<div v-else class="flex flex-col">
			<div
				v-for="variable in variables"
				:key="variable.name"
				class="group flex cursor-pointer items-center justify-between rounded py-1"
				@click="openDialog(variable)">
				<div class="flex items-center gap-2">
					<ColorPicker
						v-model="variable.value"
						placement="bottom-end"
						:showInput="true"
						popoverClass="!ml-2"
						@update:modelValue="
							(value) => {
								variable.value = value;
								debounceUpdate(value, variable);
							}
						">
						<template #target="{ togglePopover }">
							<div
								class="size-4 cursor-pointer rounded-full border border-outline-gray-2"
								:style="{ backgroundColor: resolveVariableValue(variable.value || '') }"
								@click.stop="togglePopover"></div>
						</template>
					</ColorPicker>
					<div class="flex flex-col">
						<span class="text-p-sm font-medium text-ink-gray-9">
							{{ variable.variable_name }}
						</span>
						<span class="text-xs text-ink-gray-6">
							{{ variable.value }}
						</span>
					</div>
				</div>
				<div class="flex gap-2 opacity-0 group-hover:opacity-100">
					<button
						v-if="!variable.is_standard"
						class="text-ink-gray-7 hover:text-red-600"
						@click.stop="handleDelete(variable)">
						<FeatherIcon name="trash" class="size-3" />
					</button>
				</div>
			</div>
		</div>

		<Dialog
			v-model="showDialog"
			:options="{
				title: dialogMode === 'edit' ? 'Edit Variable' : 'New Variable',
				size: 'sm',
				actions: [
					{
						label: dialogMode === 'edit' ? 'Update' : 'Create',
						variant: 'solid',
						onClick: handleSave,
					},
				],
			}">
			<template #body-content>
				<div class="flex flex-col gap-4">
					<BuilderInput
						type="text"
						v-model="activeBuilderVariable.variable_name"
						label="Variable Name"
						required
						:autofocus="true"
						placeholder="e.g., primary, accent, background"
						:hideClearButton="true" />
					<div class="flex flex-col gap-1.5">
						<InputLabel>Color Value</InputLabel>
						<ColorInput v-model="activeBuilderVariable.value" class="relative" />
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import ColorPicker from "@/components/Controls/ColorPicker.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import { BuilderVariable } from "@/types/Builder/BuilderVariable";
import { confirm } from "@/utils/helpers";
import { defaultBuilderVariable, useBuilderVariable } from "@/utils/useBuilderVariable";
import { useDebounceFn } from "@vueuse/core";
import { Dialog, FeatherIcon } from "frappe-ui";
import { ref } from "vue";
import { toast } from "vue-sonner";
import ColorInput from "./Controls/ColorInput.vue";

const { resolveVariableValue, createVariable, updateVariable, deleteVariable, variables } =
	useBuilderVariable();

const showDialog = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const activeBuilderVariable = ref<Partial<BuilderVariable>>({ ...defaultBuilderVariable });

const openDialog = (builderVariable?: BuilderVariable) => {
	if (builderVariable) {
		dialogMode.value = "edit";
		activeBuilderVariable.value = { ...builderVariable };
	} else {
		dialogMode.value = "add";
		activeBuilderVariable.value = { ...defaultBuilderVariable };
	}
	showDialog.value = true;
};

const handleSave = async () => {
	try {
		if (dialogMode.value === "edit") {
			await updateVariable(activeBuilderVariable.value);
			toast.success("Variable updated");
		} else {
			await createVariable(activeBuilderVariable.value);
			toast.success("New Variable created");
		}
		showDialog.value = false;
		activeBuilderVariable.value = { ...defaultBuilderVariable };
	} catch (error) {
		toast.error((error as Error).message || `Failed to ${dialogMode.value} Variable`);
	}
};

const handleDelete = async (builderVariable: BuilderVariable) => {
	const confirmed = await confirm("Are you sure you want to delete this Variable?");
	if (!confirmed) return;

	try {
		await deleteVariable(builderVariable.name as string);
		toast.success("Variable deleted");
	} catch (error) {
		toast.error((error as Error).message || "Failed to delete Variable");
	}
};

const debounceUpdate = useDebounceFn(async (value: `#${string}`, variable: BuilderVariable) => {
	try {
		await updateVariable({ ...variable, value });
	} catch (error) {
		console.error("Failed to update variable:", error);
	}
}, 300);
</script>
