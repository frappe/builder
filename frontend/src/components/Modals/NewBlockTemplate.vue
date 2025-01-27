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
						store.saveBlockTemplate(
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
					:options="store.blockTemplateCategoryOptions"
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
import useStore from "@/store";
import Block from "@/utils/block";
import { FileUploader } from "frappe-ui";
import Dialog from "@/components/Controls/Dialog.vue";
import { ref } from "vue";

const showBlockTemplateDialog = ref(false);
defineProps<{
	block: Block;
}>();

const store = useStore();
const blockTemplateProperties = ref({
	templateName: "",
	category: "" as (typeof store.blockTemplateCategoryOptions)[number],
	previewImage: "",
});
</script>
