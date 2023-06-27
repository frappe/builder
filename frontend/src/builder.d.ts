// Learn: Why "declare" keyword is needed, everything works without it.

// declare all types in ./types folder

declare interface BlockStyleMap {
	[key: string]: string | number;
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
	editorStyles?: BlockStyleMap;
	attributes?: BlockAttributeMap;
	classes?: Array<string>;
	children?: Array<Block | BlockOptions>;
	resizable?: boolean;
	draggable?: boolean;
	innerText?: string;
	parentBlockId?: string;
	computedStyles?: ProxyHandler<BlockStyleMap>;
	[key: string]: any;
}

declare interface BlockComponent {
	name?: string;
	component_name: string;
	icon: string;
	is_dynamic: boolean;
	block: BlockOptions;
	scale: number;
}

declare interface PageMap {
	[key: string]: Page;
}

declare interface Style {
	styles: BlockStyleMap;
	mobileStyles?: BlockStyleMap;
	tabletStyles?: BlockStyleMap;
}

declare interface StyleCopy {
	blockId: string;
	style: Style;
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

declare type LeftSidebarTabOption = 'Components' | 'Layers';

declare type BuilderMode = 'select' | 'text' | 'container' | 'image';