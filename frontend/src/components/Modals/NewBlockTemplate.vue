<template>
	<Dialog
		title="保存为区块模板"
		size="sm"
		:actions="[
			{
				label: '保存',
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
		]"
		v-model="showBlockTemplateDialog">
		<template #default>
			<div class="flex flex-col gap-3">
				<BuilderInput
					type="text"
					v-model="blockTemplateProperties.templateName"
					label="模板名称"
					required
					:hideClearButton="true" />
				<BuilderInput
					type="select"
					v-model="blockTemplateProperties.category"
					label="分类"
					:options="blockTemplateStore.blockTemplateCategoryOptions"
					:hideClearButton="true" />
				<div class="relative">
					<BuilderInput
						type="text"
						v-model="blockTemplateProperties.previewImage"
						label="预览图片"
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
								<Button size="sm" @click="openFileSelector" class="text-sm">上传</Button>
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
