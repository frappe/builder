import { defineStore } from "pinia";

type BlockData = Record<string, any>;

const useBlockDataStore = defineStore("blockDataStore", {
	state: () => ({
		blockDataMapping: <Record<string, { ownData: BlockData; passedDownData: BlockData }>>{},
	}),
	actions: {
		setBlockData(blockId: string, blockData: BlockData, type: "own" | "passedDown" = "own") {
			if(!this.blockDataMapping[blockId]) {
                this.blockDataMapping[blockId] = { ownData: {}, passedDownData: {} };
            }
			if (type === "own") {
				this.blockDataMapping[blockId].ownData = blockData;
			} else {
				this.blockDataMapping[blockId].passedDownData = blockData;
			}
		},
		getBlockData(blockId: string, filter: "all" | "own" | "passedDown" = "all"): BlockData | null {
			const blockData = this.blockDataMapping[blockId];
			if (!blockData) {
				return null;
			}
			if (filter === "own") {
				return blockData.ownData;
			} else if (filter === "passedDown") {
				return blockData.passedDownData;
			}
			return { ...blockData.ownData, ...blockData.passedDownData };
		},
		clearBlockData(blockId: string) {
			delete this.blockDataMapping[blockId];
		},
	},
});

export default useBlockDataStore;
