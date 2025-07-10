<template>
	<Dialog
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
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
					@input="(val: string) => (activeBuilderVariable.variable_name = val)"
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
</template>

<script setup lang="ts">
import ColorInput from "@/components/Controls/ColorInput.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import { BuilderVariable } from "@/types/Builder/BuilderVariable";
import { defaultBuilderVariable, useBuilderVariable } from "@/utils/useBuilderVariable";
import { Dialog } from "frappe-ui";
import { computed, ref, watch } from "vue";
import { toast } from "vue-sonner";

const props = defineProps<{
	modelValue: boolean;
	variable?: BuilderVariable | null;
}>();

const emit = defineEmits(["update:modelValue", "success"]);

const { createVariable, updateVariable } = useBuilderVariable();

const dialogMode = computed(() => (props.variable?.name ? "edit" : "add"));
const activeBuilderVariable = ref<Partial<BuilderVariable>>({ ...defaultBuilderVariable });

watch(
	() => props.modelValue,
	(newValue) => {
		if (newValue) {
			if (props.variable) {
				activeBuilderVariable.value = { ...props.variable };
			} else {
				activeBuilderVariable.value = { ...defaultBuilderVariable };
			}
		}
	},
	{
		immediate: true,
	},
);

const handleSave = async () => {
	debugger;
	try {
		let savedVariable;
		if (dialogMode.value === "edit") {
			savedVariable = await updateVariable(activeBuilderVariable.value);
			toast.success("Variable updated");
		} else {
			savedVariable = await createVariable(activeBuilderVariable.value);
			toast.success("New Variable created");
		}
		emit("success", savedVariable);
		emit("update:modelValue", false);
	} catch (error) {
		console.error("Failed to save variable:", error);
		toast.error((error as Error).message || `Failed to ${dialogMode.value} Variable`);
	}
};
</script>
