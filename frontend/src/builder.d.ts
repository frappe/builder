declare type StyleValue = string | number;

declare interface BlockStyleMap {
	[key: string]: StyleValue;
}

declare interface BlockAttributeMap {
	[key: string]: string;
}

declare interface BlockOptions {
	blockId?: string | undefined;
	element: string;
	originalElement?: string;
	baseStyles?: BlockStyleMap;
	mobileStyles?: BlockStyleMap;
	tabletStyles?: BlockStyleMap;
	attributes?: BlockAttributeMap;
	classes?: Array<string>;
	children?: Array<Block | BlockOptions>;
	draggable?: boolean;
	innerText?: string;
	parentBlockId?: string;
	[key: string]: any;
}

declare interface BlockComponent {
	name: string;
	component_name: string;
	icon: string;
	is_dynamic: boolean;
	block: BlockOptions;
	scale: number;
}

declare interface PageMap {
	[key: string]: Page;
}

declare interface BlockStyleObjects {
	baseStyles: BlockStyleMap;
	mobileStyles?: BlockStyleMap;
	tabletStyles?: BlockStyleMap;
}

declare interface StyleCopy {
	blockId: string;
	style: BlockStyleObjects;
}

declare interface ContextMenuOption {
	label: string;
	action: CallableFunction;
	condition?: () => boolean;
}

declare interface ComponentData {
	name: string;
	doctype?: string;
	isDynamic: boolean;
	mappings?: {
		[key: string]: string;
	};
}

declare type HashString = `#${string}`;

declare type RGBString = `rgb(${number}, ${number}, ${number})`;

declare type LeftSidebarTabOption = "Components" | "Layers";

declare type BuilderMode = "select" | "text" | "container" | "image" | "html";

declare interface CanvasProps {
	scale: number;
	translateX: number;
	translateY: number;
	scaling: boolean;
	panning: boolean;
	background: string;
	settingCanvas: boolean;
}
