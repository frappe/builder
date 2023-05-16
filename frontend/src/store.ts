import { defineStore } from "pinia";
import Block from "./utils/block";


const useStore = defineStore("store", {
	state: () => ({
		builderState: {
			selectedPage: <string | null>null,
			selectedBlock: <Block | null>null,
			selectedBlocks: <Block[]>[],
			editableBlock: <Block | null>null,
			activeBreakpoint: "desktop",
			blocks: <Block[]>[
				new Block({
					element: "div",
					originalElement: "body",
					blockId: "root",
					resizable: false,
				}),
			],
		},
		hoveredBlock: <string | null>null,
		hoveredBreakpoint: <string | null>null,
		builderLayout: {
			rightPanelWidth: 270,
			leftPanelWidth: 280,
		},
		widgets: [
			{
				name: "Container",
				element: "section",
				icon: "square",
				children: [],
				styles: {
					display: "flex",
					flexDirection: "column",
					justifyContent: "center",
					alignItems: "center",
					height: "auto",
					width: "100%",
					minHeight: "200px",
					margin: "0 auto",
				},
				editorStyles: {
					userSelect: "none",
				},
				classes: ["bg-blue-100"],
				attributes: {},
			},
			{
				name: "Text",
				element: "p",
				icon: "type",
				innerText: "Text",
				styles: {
					fontSize: "40px",
					width: "fit-content",
					"line-height": "1",
				},
			},
			{
				name: "Link",
				element: "a",
				icon: "link",
				innerText: "Link",
				styles: {
					width: "auto",
					"font-size": "20px",
					"line-height": "1",
				},
				attributes: {
					href: "/#",
				},
			},
			{
				name: "Image",
				element: "img",
				icon: "image",
				styles: {
					width: "auto",
					height: "auto",
				},
				attributes: {
					// src: "https://picsum.photos/500/200"
					src: "https://user-images.githubusercontent.com/13928957/212847544-5773795d-2fd6-48d1-8423-b78ecc92522b.png",
				},
			},
		],
		flow: [
			{
				name: "Row",
				styleKey: "flexDirection",
				styleValue: "row",
				icon: "columns",
			},
			{
				name: "Column",
				styleKey: "flexDirection",
				styleValue: "column",
				icon: "credit-card",
			},
		],
		alignments: [
			{
				name: "Left",
				styleKey: "justifyContent",
				styleValue: "flex-start",
				icon: "align-left",
			},
			{
				name: "Center",
				styleKey: "justifyContent",
				styleValue: "center",
				icon: "align-center",
			},
			{
				name: "Right",
				styleKey: "justifyContent",
				styleValue: "flex-end",
				icon: "align-right",
			},
			{
				name: "Justify",
				styleKey: "justifyContent",
				styleValue: "space-between",
				icon: "align-justify",
			},
		],
		verticalAlignments: [
			{
				name: "Top",
				styleKey: "alignItems",
				styleValue: "flex-start",
				icon: "arrow-up",
			},
			{
				name: "Middle",
				styleKey: "alignItems",
				styleValue: "center",
				icon: "minus",
			},
			{
				name: "Bottom",
				styleKey: "alignItems",
				styleValue: "flex-end",
				icon: "arrow-down",
			},
		],
		pageName: "Home",
		route: "/",
		pages: <PageMap>{},
		pastelCssColors: [
			"#FFFFFF",
			"#F5FFFA",
			"#F8F8FF",
			"#F0F8FF",
			"#F5F5DC",
			"#FFE4C4",
			"#FFEBCD",
			"#FFDEAD",
			"#FFC1C1",
			"#FFB6C1",
			"#FFA07A",
			"#FF8C00",
			"#FF7F50",
			"#FF69B4",
			"#FF6347",
			"#FDB813",
			"#FDAB9F",
			"#FDA50F",
			"#F49AC2",
			"#FFB347",
			"#FFD700",
			"#ADFF2F",
			"#87CEFA",
			"#00BFFF",
			"#ADD8E6",
			"#B0E0E6",
			"#5F9EA0",
			"#FDD5B1",
			"#FCCDE3",
			"#FCC2D9",
			"#FCB4D5",
			"#FBB5A3",
			"#FBB917",
			"#FBB972",
			"#FBB9AC",
			"#FBCEB1",
			"linear-gradient(120deg, #f093fb 0%, #f5576c 100%)",
			"linear-gradient(to top, #a18cd1 0%, #fbc2eb 100%)",
			"linear-gradient(to top, #a8edea 0%, #fed6e3 100%)",
			"linear-gradient(to top, #96fbc4 0%, #f9f586 100%)",
			"linear-gradient(to top, #9795f0 0%, #fbc8d4 100%)",
			"linear-gradient(-60deg, #16a085 0%, #f4d03f 100%)",
			"linear-gradient( 135deg, #81FFEF 10%, #F067B4 100%)",
			"black",
			"transparent",
		],
		guides: {
			showX: false,
			showY: false,
			x: 0,
			y: 0,
		},
		textColors: [
			"#000000",
			"#424242",
			"#636363",
			"#808080",
			"#9C9C94",
			"#C0C0C0",
			"#CEC6CE",
			"#EFEFEF",
			"#F7F7F7",
			"#FFFFFF",
		],
		deviceBreakpoints: [
			{
				icon: "monitor",
				device: "desktop",
				width: 1400,
				visible: true,
			},
			{
				icon: "tablet",
				device: "tablet",
				width: 768,
				visible: false,
			},
			{
				icon: "smartphone",
				device: "mobile",
				width: 425,
				visible: false,
			},
		],
		sidebarActiveTab: "Widgets",
		canvas: {
			initialScale: 1,
			initialTranslateY: 0,
			initialTranslateX: 0,
			scale: 1,
			translateX: 0,
			translateY: 0,
			startX: 0,
			startY: 0,
			background: ''
		},
		copiedStyle: <StyleCopy | null>null,
		components: <BlockComponent[]>[],
		overlayElement: <any>null,
	}),
	actions: {
		clearBlocks() {
			this.builderState.blocks = [];
			this.builderState.blocks.push(this.getRootBlock());
		},
		pushBlocks(blocks: BlockOptions[]) {
			let firstBlock = new Block(blocks[0]);
			if (firstBlock.isRoot()) {
				this.builderState.blocks = [firstBlock];
			} else {
				for (let block of blocks) {
					this.builderState.blocks[0].children.push(new Block(block));
				}
			}
		},
		getBlockCopy(block: BlockOptions | Block, retainId = false): Block {
			let b = JSON.parse(JSON.stringify(block));
			if (!retainId) {
				const deleteBlockId = (block: BlockOptions) => {
					delete block.blockId;
					for (let child of block.children || []) {
						deleteBlockId(child)
					}
				}
				deleteBlockId(b);
			}
			return new Block(b);
		},
		getRootBlock() {
			return new Block({
				element: "div",
				originalElement: "body",
				blockId: "root",
				resizable: false,
			});
		},
		getPageData() { },
		setPage(page: Page) {
			if (!page) return;
			// clear blocks
			this.clearBlocks();
			this.pushBlocks(page.blocks);
			this.pageName = page.page_name;
			this.route = page.route;
			this.builderState.selectedPage = page.name;
			// localStorage.setItem("selectedPage", page.name);
		}
	},
});

export default useStore;
