import Block from "@/block";
import { defineStore } from "pinia";

type BlockData = Record<string, any>;

const useBlockDataStore = defineStore("blockDataStore", {
	state: () => ({
		blockDataMap: <
			Record<string, { ownData: BlockData; passedDownData: BlockData }>
		>{},
		pageDataMap: <Record<string, any>>{},
		defaultPropsMap: <Record<string, BlockProps>>{},
	}),
	actions: {
		setPageData(blockUid: string, pageData: any) {
			this.pageDataMap[blockUid] = pageData;
		},
		getPageData(blockUid: string): any {
			return this.pageDataMap[blockUid];
		},
		clearPageData(blockUid: string) {
			delete this.pageDataMap[blockUid];
		},
		setBlockData(
			blockUid: string,
			blockData: BlockData,
			type: "own" | "passedDown" = "own",
		) {
			if (!this.blockDataMap[blockUid]) {
				this.blockDataMap[blockUid] = { ownData: {}, passedDownData: {} };
			}
			if (type === "own") {
				this.blockDataMap[blockUid].ownData = blockData;
			} else {
				this.blockDataMap[blockUid].passedDownData = blockData;
			}
		},
		getBlockData(
			blockUid: string,
			filter: "all" | "own" | "passedDown" = "all",
		): BlockData | null {
			const blockData = this.blockDataMap[blockUid];
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
			delete this.blockDataMap[blockUid];
		},
		setBlockDefaultProps(blockUid: string, props: BlockProps) {
			this.defaultPropsMap[blockUid] = props;
		},
		getDefaultProps(blockUid: string): BlockProps | null {
			const defaultProps = this.defaultPropsMap[blockUid];
			if (!defaultProps) {
				return null;
			}
			return defaultProps;
		},
		clearDefaultProps(blockUid: string) {
			delete this.defaultPropsMap[blockUid];
		},
	},
});

const useBlockUidStore = defineStore("blockUidStore", {
	state: () => ({
		blockUidToBlockMap: <Record<string, Block>>{},
		blockUidToParentUidMap: <Record<string, string>>{},
	}),
	actions: {
		registerBlockUid(uid: string, block: Block) {
			this.blockUidToBlockMap[uid] = block;
		},
		getBlockFromUid(uid: string): Block | null {
			return this.blockUidToBlockMap[uid] || null;
		},
		unregisterBlockUid(uid: string) {
			delete this.blockUidToBlockMap[uid];
		},
		setParentUid(uid: string, parentUid: string) {
			this.blockUidToParentUidMap[uid] = parentUid;
		},
		getParentUid(uid: string): string | null {
			return this.blockUidToParentUidMap[uid] || null;
		},
		clearParentUid(uid: string) {
			delete this.blockUidToParentUidMap[uid];
		},
	},
});

export { useBlockDataStore, useBlockUidStore };
