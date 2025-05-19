<template>
	<Dialog
		style="z-index: 40"
		:options="{
			title: 'Save as Block Template',
			size: 'sm',
			actions: [
				{
					label: 'Save',
					variant: 'solid',
					onClick: (close: () => void) => {
						blockTemplateStore.saveBlockTemplate(
							block,
							blockTemplateProperties.templateName,
							blockTemplateProperties.category,
							blockTemplateProperties.previewImage,
						);
						close();
					},
				},
			],
		}"
		v-model="showBlockTemplateDialog">
		<template #body-content>
			<div class="flex flex-col gap-3">
				<BuilderInput
					type="text"
					v-model="blockTemplateProperties.templateName"
					label="Template Name"
					required
					:hideClearButton="true" />
				<BuilderInput
					type="select"
					v-model="blockTemplateProperties.category"
					label="Category"
					:options="blockTemplateStore.blockTemplateCategoryOptions"
					:hideClearButton="true" />
				<div class="relative">
					<BuilderInput
						type="text"
						v-model="blockTemplateProperties.previewImage"
						label="Preview Image"
						:hideClearButton="true" />
					<FileUploader
						file-types="image/*"
						@success="
							(file: FileDoc) => {
								blockTemplateProperties.previewImage = file.file_url;
							}
						">
						<template v-slot="{ openFileSelector }">
							<div class="absolute bottom-0 right-0 place-items-center">
								<BuilderButton size="sm" @click="openFileSelector" class="text-sm">Upload</BuilderButton>
							</div>
						</template>
					</FileUploader>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import type Block from "@/block";
import Dialog from "@/components/Controls/Dialog.vue";
import useBlockTemplateStore from "@/stores/blockTemplateStore";
import { FileUploader } from "frappe-ui";
import { ref } from "vue";

const showBlockTemplateDialog = ref(false);
defineProps<{
	block: Block;
}>();

const blockTemplateStore = useBlockTemplateStore();
const blockTemplateProperties = ref({
	templateName: "",
	category: "" as (typeof blockTemplateStore.blockTemplateCategoryOptions)[number],
	previewImage: "",
});
</script>
