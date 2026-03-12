import { defineStore } from "pinia";

type BlockData = Record<string, any>;

const useBlockDataStore = defineStore("blockDataStore", {
	state: () => ({
		blockDataMapping: <Record<string, { ownData: BlockData; passedDownData: BlockData }>>{},
		pageDataMapping: <Record<string, any>>{},
	}),
	actions: {
		setPageData(blockUid: string, pageData: any) {
			this.pageDataMapping[blockUid] = pageData;
		},
		getPageData(blockUid: string): any {
			return this.pageDataMapping[blockUid];
		},
		clearPageData(blockUid: string) {
			delete this.pageDataMapping[blockUid];
		},
		setBlockData(blockUid: string, blockData: BlockData, type: "own" | "passedDown" = "own") {
			if(!this.blockDataMapping[blockUid]) {
                this.blockDataMapping[blockUid] = { ownData: {}, passedDownData: {} };
            }
			if (type === "own") {
				this.blockDataMapping[blockUid].ownData = blockData;
			} else {
				this.blockDataMapping[blockUid].passedDownData = blockData;
			}
		},
		getBlockData(blockUid: string, filter: "all" | "own" | "passedDown" = "all"): BlockData | null {
			const blockData = this.blockDataMapping[blockUid];
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
		clearBlockData(blockUid: string) {
			delete this.blockDataMapping[blockUid];
		},
	},
});

export default useBlockDataStore;
