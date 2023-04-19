import useStore from "../store";

interface Styles {
	[key: string]: string | number;
}

interface BlockOptions {
	blockId?: string | undefined;
	element: string;
	originalElement?: string;
	styles?: Styles;
	mobileStyles?: Styles;
	tabletStyles?: Styles;
	editorStyles?: Styles;
	attributes?: Styles;
	classes?: Array<string>;
	children?: Array<Block>;
	resizable?: boolean;
	draggable?: boolean;
	innerText?: string;
	computedStyles?: ProxyHandler<Styles>;
}

class Block implements BlockOptions {
	blockId: string;
	element: string;
	editorStyles: Styles;
	children: Array<Block>;
	draggable?: boolean;
	styles: Styles;
	mobileStyles: { [key: string]: string | number };
	tabletStyles: Styles;
	attributes: Styles;
	classes: Array<string>;
	resizable?: boolean;
	computedStyles: ProxyHandler<Styles>;
	originalElement?: string | undefined;
	constructor(options: BlockOptions) {
		delete options.computedStyles;
		this.element = options.element;
		this.draggable = options.draggable;
		if (this.isRoot()) {
			this.blockId = "root";
			this.editorStyles = {
				height: "fit-content",
				minHeight: "100%",
				width: "inherit",
				position: "absolute",
				overflow: "hidden",
				top: 0,
				left: 0,
				bottom: 0,
				right: 0,
			};
			this.draggable = false;
		}
		this.blockId = options.blockId || this.generateId();
		this.children = (options.children || []).map((child: BlockOptions) => new Block(child));

		this.styles = options.styles || {};
		this.mobileStyles = options.mobileStyles || {};
		this.tabletStyles = options.tabletStyles || {};
		this.editorStyles = options.editorStyles || {};
		this.attributes = options.attributes || {};
		this.classes = options.classes || [];

		this.computedStyles = new Proxy(this.styles, {
			set: (target, prop: string, value) => {
				this.setStyle(prop, value);
				return true;
			},
			get: (target, prop: string) => {
				return this.getStyle(prop);
			}
		})
	}
	isImage() {
		return this.element === "img";
	}
	isButton() {
		return this.element === "button";
	}
	isLink() {
		return this.element === "a";
	}
	isText() {
		return ["span", "h1", "p", "b", "h2", "h3", "h4", "h5", "h6", "a"].includes(this.element);
	}
	isContainer() {
		return this.element === "section";
	}
	setStyle(style: string, value: number | string) {
		const store = useStore();
		if (store.builderState.activeBreakpoint === "mobile") {
			this.mobileStyles[style] = value;
			return;
		} else if (store.builderState.activeBreakpoint === "tablet") {
			this.tabletStyles[style] = value;
			return;
		}
		this.styles[style] = value;
	}
	getStyle(style: string) {
		const store = useStore();
		if (store.builderState.activeBreakpoint === "mobile") {
			return this.mobileStyles[style] || this.styles[style];
		} else if (store.builderState.activeBreakpoint === "tablet") {
			return this.tabletStyles[style] || this.styles[style];
		}
		return this.styles[style];
	}
	generateId() {
		return Math.random().toString(36).substr(2, 9);
	}
	getIcon() {
		return this.isText() ? 'type': this.isImage() ? 'image': this.isContainer() ? 'square': this.isLink() ? 'link': this.isRoot() ? 'hash': 'square';
	}
	isRoot() {
		return this.originalElement === "body";
	}
	getTag() {
		return this.element === 'button' ? 'div' : this.element;
	}
	isDiv() {
		return this.element === 'div';
	}
	getStylesCopy() {
		return {
			styles: Object.assign({}, this.styles),
			mobileStyles: Object.assign({}, this.mobileStyles),
			tabletStyles: Object.assign({}, this.tabletStyles),
		}
	}
}

export default Block;

export {
	Styles,
	BlockOptions,
}