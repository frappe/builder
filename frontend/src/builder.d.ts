declare type StyleValue = string | number | null | undefined;

declare type styleProperty = keyof CSSProperties | `__${string}`;

declare interface BlockStyleMap {
	[key: styleProperty]: StyleValue;
}

declare interface BlockAttributeMap {
	[key: string]: string | number | null | undefined;
}

declare interface BlockOptions {
	blockId?: string | undefined;
	element?: string;
	originalElement?: string;
	baseStyles?: BlockStyleMap;
	mobileStyles?: BlockStyleMap;
	tabletStyles?: BlockStyleMap;
	attributes?: BlockAttributeMap;
	classes?: Array<string>;
	children?: Array<Block | BlockOptions>;
	dynamicValues?: Array<BlockDataKey>;
	draggable?: boolean;
	[key: string]: any;
}

declare interface BlockComponent {
	name: string;
	component_name: string;
	component_id: string;
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
	disabled?: () => boolean;
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

declare type LeftSidebarTabOption = "Blocks" | "Layers" | "Assets" | "Code" | "variables";
declare type RightSidebarTabOption = "Properties" | "Script" | "Options";

declare type BuilderMode = "select" | "text" | "container" | "image" | "repeater" | "move";

declare interface Breakpoint {
	icon: string;
	device: string;
	displayName: string;
	width: number;
	visible: boolean;
}

declare interface CanvasProps {
	scale: number;
	translateX: number;
	translateY: number;
	scaling: boolean;
	panning: boolean;
	background: string;
	settingCanvas: boolean;
	overlayElement: HTMLElement | null;
	breakpoints: Breakpoint[];
}

declare type EditingMode = "page" | "fragment";

declare type UserInfo = { user: string; fullname: string; image: string };

declare type FileDoc = {
	file_url: string;
};

declare interface BlockDataKey {
	key?: string;
	type?: BlockDataKeyType;
	property?: string;
}

declare type BlockDataKeyType = "key" | "attribute" | "style";

declare type CSSVariableName = string | `var(--${string})`;
