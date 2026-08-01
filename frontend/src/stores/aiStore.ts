import type Block from "@/block";
import type AIPageGeneratorModal from "@/components/AIPageGeneratorModal.vue";
import { getBlockObject } from "@/utils/helpers";
import { defineStore } from "pinia";

const useAIStore = defineStore("aiStore", {
	state: () => ({
		// the modal owns executeDirect, so runDirectAI needs the instance
		generatorModal: <InstanceType<typeof AIPageGeneratorModal> | null>null,
		showGeneratorDialog: false,
		mode: <"generate" | "modify">"generate",
		modifyBlockContext: <Record<string, any> | null>null,
		modifyBlockId: <string | null>null,
	}),
	actions: {
		showGenerator() {
			this.endModify();
			this.showGeneratorDialog = true;
		},

		editWithAI(block: Block) {
			this.startModify(block);
			this.showGeneratorDialog = true;
		},

		runDirectAI(block: Block, type: "rewrite_text" | "replace_image", customPrompt?: string) {
			const blockObject = this.startModify(block);
			this.generatorModal?.executeDirect(blockObject, type, customPrompt);
		},

		startModify(block: Block) {
			const blockObject = getBlockObject(block);
			this.mode = "modify";
			this.modifyBlockContext = blockObject;
			this.modifyBlockId = block.blockId;
			return blockObject;
		},

		endModify() {
			this.mode = "generate";
			this.modifyBlockContext = null;
			this.modifyBlockId = null;
		},
	},
});

export default useAIStore;
