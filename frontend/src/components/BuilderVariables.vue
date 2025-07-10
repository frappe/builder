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
				class="group flex cursor-pointer items-center justify-between rounded py-1">
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
								@click.stop="() => (!variable.is_standard ? togglePopover() : null)"></div>
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
					<template v-if="!variable.is_standard">
						<button
							class="text-ink-gray-7 hover:text-ink-gray-9"
							@click.stop="openDialog(variable)"
							title="Edit Variable">
							<FeatherIcon name="edit" class="size-3" />
						</button>
						<button
							class="text-ink-gray-7 hover:text-red-600"
							@click.stop="handleDelete(variable)"
							title="Delete Variable">
							<FeatherIcon name="trash" class="size-3" />
						</button>
					</template>
				</div>
			</div>
		</div>

		<NewBuilderVariable v-model="showDialog" :variable="activeBuilderVariable" />
	</div>
</template>

<script setup lang="ts">
import ColorPicker from "@/components/Controls/ColorPicker.vue";
import NewBuilderVariable from "@/components/Modals/NewBuilderVariable.vue";
import { BuilderVariable } from "@/types/Builder/BuilderVariable";
import { confirm } from "@/utils/helpers";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { useDebounceFn } from "@vueuse/core";
import { FeatherIcon } from "frappe-ui";
import { ref } from "vue";
import { toast } from "vue-sonner";

const { resolveVariableValue, updateVariable, deleteVariable, variables } = useBuilderVariable();

const showDialog = ref(false);
const activeBuilderVariable = ref<Partial<BuilderVariable> | null>(null);

const openDialog = (builderVariable?: BuilderVariable) => {
	activeBuilderVariable.value = builderVariable || null;
	showDialog.value = true;
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
