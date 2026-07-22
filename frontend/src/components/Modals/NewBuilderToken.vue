<template>
	<Dialog
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
		:title="dialogMode === 'edit' ? 'Edit Variable' : 'New Variable'"
		size="sm"
		:actions="[
			{
				label: dialogMode === 'edit' ? 'Update' : 'Create',
				variant: 'solid',
				onClick: handleSave,
			},
		]">
		<template #default>
			<div class="flex flex-col gap-4">
				<BuilderInput
					type="text"
					v-model="activeBuilderToken.token_name"
					@input="(val: string) => (activeBuilderToken.token_name = val)"
					label="Variable Name"
					required
					:autofocus="true"
					placeholder="e.g., primary, accent, background"
					:hideClearButton="true" />
				<div v-if="activeBuilderToken.type === 'Color'" class="flex flex-col gap-3">
					<div class="flex flex-col gap-1.5">
						<InputLabel>Light Mode Color</InputLabel>
						<ColorInput
							v-model="activeBuilderToken.value"
							class="relative"
							:show-color-variable-options="false" />
					</div>
					<div class="flex flex-col gap-1.5">
						<InputLabel>Dark Mode Color</InputLabel>
						<ColorInput
							:modelValue="activeBuilderToken.dark_value || activeBuilderToken.value"
							:show-color-variable-options="false"
							@update:modelValue="activeBuilderToken.dark_value = $event"
							class="relative" />
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import ColorInput from "@/components/Controls/ColorInput.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import { BuilderToken } from "@/types/doctypes";
import { defaultBuilderToken, useBuilderToken } from "@/utils/useBuilderToken";
import { Dialog } from "frappe-ui";
import { computed, ref, watch } from "vue";
import { toast } from "frappe-ui";

const props = defineProps<{
	modelValue: boolean;
	variable?: Partial<BuilderToken> | null;
}>();

const emit = defineEmits(["update:modelValue", "success"]);

const { createVariable, updateVariable } = useBuilderToken();

const dialogMode = computed(() => (props.variable?.name ? "edit" : "add"));
const activeBuilderToken = ref<Partial<BuilderToken>>({ ...defaultBuilderToken });

watch(
	() => props.modelValue,
	(newValue) => {
		if (newValue) {
			if (props.variable) {
				activeBuilderToken.value = { ...props.variable };
			} else {
				activeBuilderToken.value = { ...defaultBuilderToken };
			}
		}
	},
	{
		immediate: true,
	},
);

const handleSave = async () => {
	try {
		let savedVariable;
		if (dialogMode.value === "edit") {
			savedVariable = await updateVariable(activeBuilderToken.value);
			toast.success("Variable updated");
		} else {
			savedVariable = await createVariable(activeBuilderToken.value);
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
