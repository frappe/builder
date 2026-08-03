<template>
	<Dialog
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
		:title="dialogMode === 'edit' ? '编辑变量' : '新建变量'"
		size="sm"
		:actions="[
			{
				label: dialogMode === 'edit' ? '更新' : '创建',
				variant: 'solid',
				onClick: handleSave,
			},
		]">
		<template #default>
			<div class="flex flex-col gap-4">
				<BuilderInput
					type="text"
					v-model="activeBuilderVariable.variable_name"
					@input="(val: string) => (activeBuilderVariable.variable_name = val)"
					label="变量名称"
					required
					:autofocus="true"
					placeholder="e.g., primary, accent, background"
					:hideClearButton="true" />
				<div v-if="activeBuilderVariable.type === 'Color'" class="flex flex-col gap-3">
					<div class="flex flex-col gap-1.5">
						<InputLabel>浅色模式颜色</InputLabel>
						<ColorInput
							v-model="activeBuilderVariable.value"
							class="relative"
							:show-color-variable-options="false" />
					</div>
					<div class="flex flex-col gap-1.5">
						<InputLabel>深色模式颜色</InputLabel>
						<ColorInput
							:modelValue="activeBuilderVariable.dark_value || activeBuilderVariable.value"
							:show-color-variable-options="false"
							@update:modelValue="activeBuilderVariable.dark_value = $event"
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
import { BuilderVariable } from "@/types/doctypes";
import { defaultBuilderVariable, useBuilderVariable } from "@/utils/useBuilderVariable";
import { Dialog } from "frappe-ui";
import { computed, ref, watch } from "vue";
import { toast } from "frappe-ui";

const props = defineProps<{
	modelValue: boolean;
	variable?: Partial<BuilderVariable> | null;
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
	try {
		let savedVariable;
		if (dialogMode.value === "edit") {
			savedVariable = await updateVariable(activeBuilderVariable.value);
			toast.success("变量已更新");
		} else {
			savedVariable = await createVariable(activeBuilderVariable.value);
			toast.success("已创建新变量");
		}
		emit("success", savedVariable);
		emit("update:modelValue", false);
	} catch (error) {
		console.error("Failed to save variable:", error);
		toast.error((error as Error).message || (dialogMode.value === "edit" ? "更新变量失败" : "创建变量失败"));
	}
};
</script>
