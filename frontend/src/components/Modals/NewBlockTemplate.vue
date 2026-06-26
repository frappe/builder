<template>
	<Dialog
		title="Save as Template"
		size="sm"
		:actions="[
			{
				label: 'Save',
				variant: 'solid',
				onClick: async (close: () => void) => {
					await saveTemplateComponent(block);
					close();
				},
			},
		]"
		v-model="showBlockTemplateDialog">
		<template #default>
			<div class="flex flex-col gap-3">
				<BuilderInput
					type="text"
					v-model="blockTemplateProperties.templateName"
					label="Template Name"
					required
					:hideClearButton="true" />
				<BuilderInput
					type="text"
					v-model="blockTemplateProperties.category"
					label="Category"
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
								<Button size="sm" @click="openFileSelector" class="text-sm">Upload</Button>
							</div>
						</template>
					</FileUploader>
				</div>
				<div class="grid grid-cols-2 gap-3">
					<BuilderInput
						type="number"
						v-model="blockTemplateProperties.previewWidth"
						label="Preview Width"
						min="1"
						max="2"
						:hideClearButton="true" />
					<BuilderInput
						type="number"
						v-model="blockTemplateProperties.previewHeight"
						label="Preview Height"
						min="1"
						max="2"
						:hideClearButton="true" />
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import type Block from "@/block";
import Dialog from "@/components/Controls/Dialog.vue";
import webComponent, { builderComponentCategories, standardComponent } from "@/data/webComponent";
import { getBlockString } from "@/utils/helpers";
import { FileUploader, toast } from "frappe-ui";
import { ref } from "vue";

const showBlockTemplateDialog = ref(false);
defineProps<{
	block: Block;
}>();

const blockTemplateProperties = ref({
	templateName: "",
	category: "Basic",
	previewImage: "",
	previewWidth: 1,
	previewHeight: 1,
});

const getTemplateComponentId = (templateName: string) => {
	const slug = templateName
		.trim()
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "_")
		.replace(/^_+|_+$/g, "");
	if (!slug) {
		throw new Error("Template name is required");
	}
	return `builder_template_${slug}`;
};

const getPreviewSize = (value: string | number) => {
	const size = Number(value) || 1;
	return Math.min(Math.max(size, 1), 2);
};

const saveTemplateComponent = async (block: Block) => {
	const componentId = getTemplateComponentId(blockTemplateProperties.value.templateName);
	const args = {
		name: componentId,
		component_id: componentId,
		component_name: blockTemplateProperties.value.templateName,
		is_standard: 1,
		category: blockTemplateProperties.value.category,
		preview: blockTemplateProperties.value.previewImage,
		preview_width: getPreviewSize(blockTemplateProperties.value.previewWidth),
		preview_height: getPreviewSize(blockTemplateProperties.value.previewHeight),
		block: getBlockString(block),
	};

	if (standardComponent.getRow(componentId)) {
		await standardComponent.setValue.submit(args);
	} else {
		await standardComponent.insert.submit(args).catch(async (e: { response?: { status?: number } }) => {
			if (e?.response?.status !== 409) {
				throw e;
			}
			await standardComponent.setValue.submit(args);
		});
	}
	await standardComponent.reload();
	await builderComponentCategories.reload();
	await webComponent.reload();
	toast.success("Template saved!");
};
</script>
