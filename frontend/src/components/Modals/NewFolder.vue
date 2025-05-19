<template>
	<Dialog
		class="overscroll-none"
		v-model="showModel"
		:options="{
			title: 'Create New Folder',
			size: 'sm',
			actions: [
				{
					label: 'Create Folder',
					variant: 'solid',
					loading: builderProjectFolder.loading,
					onClick: createFolder,
				},
			],
		}">
		<template #body-content>
			<BuilderInput
				@input="folderName = $event"
				:modelValue="folderName"
				type="Input"
				:autofocus="true"
				label="Folder Name"
				:required="true"></BuilderInput>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import builderProjectFolder from "@/data/builderProjectFolder";
import { useVModel } from "@vueuse/core";
import { ref } from "vue";

const folderName = ref("");
const props = defineProps<{
	modelValue: boolean;
}>();
const emit = defineEmits(["update:modelValue"]);
const showModel = useVModel(props, "modelValue", emit);

const createFolder = () => {
	if (!folderName.value) {
		return;
	}
	builderProjectFolder.insert
		.submit({
			folder_name: folderName.value,
		})
		.then(() => {
			folderName.value = "";
			showModel.value = false;
		});
};
</script>
