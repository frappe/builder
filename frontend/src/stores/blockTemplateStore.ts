import type Block from "@/block";
import builderBlockTemplate from "@/data/builderBlockTemplate";
import { BlockTemplate } from "@/types/Builder/BlockTemplate";
import { getBlockInstance, getBlockString } from "@/utils/helpers";
import { createDocumentResource } from "frappe-ui";
import { defineStore } from "pinia";
import { toast } from "vue-sonner";
import useCanvasStore from "./canvasStore";

const useBlockTemplateStore = defineStore("blockTemplateStore", {
	state: () => ({
		blockTemplateMap: <Map<string, BlockTemplate>>new Map(),
		blockTemplateCategoryOptions: [
			"Basic",
			"Structure",
			"Typography",
			"Basic Forms",
			"Form parts",
			"Media",
			"Advanced",
		] as BlockTemplate["category"][],
	}),
	actions: {
		getBlockTemplate(blockTemplateName: string) {
			return this.blockTemplateMap.get(blockTemplateName) as BlockTemplate;
		},

		async editBlockTemplate(blockTemplateName: string) {
			await this.fetchBlockTemplate(blockTemplateName);
			const blockTemplate = this.getBlockTemplate(blockTemplateName);
			const blockTemplateBlock = this.getBlockTemplateBlock(blockTemplateName);
			const canvasStore = useCanvasStore();

			canvasStore.editOnCanvas(
				blockTemplateBlock,
				(block: Block) => {
					this.saveBlockTemplate(block, blockTemplateName);
				},
				"Save Template",
				blockTemplate.template_name,
			);
		},

		getBlockTemplateBlock(blockTemplateName: string) {
			return getBlockInstance(this.getBlockTemplate(blockTemplateName).block);
		},

		async fetchBlockTemplate(blockTemplateName: string) {
			const blockTemplate = this.getBlockTemplate(blockTemplateName);
			if (!blockTemplate) {
				const webBlockTemplate = await createDocumentResource({
					doctype: "Block Template",
					name: blockTemplateName,
					auto: true,
				});
				await webBlockTemplate.get.promise;
				const blockTemplate = webBlockTemplate.doc as BlockTemplate;
				this.blockTemplateMap.set(blockTemplateName, blockTemplate);
			}
		},

		async saveBlockTemplate(
			block: Block,
			templateName: string,
			category: BlockTemplate["category"] = "Basic",
			previewImage: string = "",
		) {
			const blockString = getBlockString(block);
			const args = {
				name: templateName,
				template_name: templateName,
				block: blockString,
			} as BlockTemplate;

			if (builderBlockTemplate.getRow(templateName)) {
				await builderBlockTemplate.setValue.submit(args);
			} else {
				args["category"] = category;
				args["preview"] = previewImage;
				await builderBlockTemplate.insert.submit(args);
			}

			toast.success("Block template saved!");
		},
	},
});

export default useBlockTemplateStore;
