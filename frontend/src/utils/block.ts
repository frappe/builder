import useStore from "@/store";
import { addPxToNumber, getNumberFromPx } from "./helpers";
import { CSSProperties, reactive } from "vue";

type styleProperty = keyof CSSProperties;

class Block implements BlockOptions {
	blockId: string;
	blockName?: string;
	element: string;
	children: Array<Block>;
	draggable?: boolean;
	baseStyles: BlockStyleMap;
	rawStyles: BlockStyleMap;
	mobileStyles: BlockStyleMap;
	tabletStyles: BlockStyleMap;
	attributes: BlockAttributeMap;
	classes: Array<string>;
	resizable?: boolean;
	innerText?: string;
	componentData: ComponentData;
	isComponent?: boolean;
	originalElement?: string | undefined;
	parentBlockId?: string;
	constructor(options: BlockOptions) {
		this.element = options.element;
		this.draggable = options.draggable;
		this.innerText = options.innerText;
		this.originalElement = options.originalElement;
		this.blockId = options.blockId || this.generateId();
		this.parentBlockId = options.parentBlockId;
		this.children = (options.children || []).map((child: BlockOptions) => {
			child.parentBlockId = this.blockId;
			return new Block(child);
		});

		this.baseStyles = reactive(options.styles || options.baseStyles || {});
		this.rawStyles = reactive(options.rawStyles || {});
		this.mobileStyles = reactive(options.mobileStyles || {});
		this.tabletStyles = reactive(options.tabletStyles || {});
		this.attributes = reactive(options.attributes || {});

		this.blockName = options.blockName;
		delete this.attributes.style;
		this.classes = options.classes || [];
		this.isComponent = options.isComponent;

		this.componentData = {
			name: options.blockName,
			isDynamic: false,
		};

		if (this.isRoot()) {
			this.draggable = false;
		}
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
		return ["span", "h1", "p", "b", "h2", "h3", "h4", "h5", "h6", "a", "label"].includes(this.element);
	}
	isContainer() {
		return ["section", "div"].includes(this.element);
	}
	isInput() {
		return this.originalElement || this.element === "input";
	}
	setStyle(style: styleProperty, value: number | string | null) {
		const store = useStore();
		let styleObj = this.baseStyles;
		if (store.builderState.activeBreakpoint === "mobile") {
			styleObj = this.mobileStyles;
		} else if (store.builderState.activeBreakpoint === "tablet") {
			styleObj = this.tabletStyles;
		}
		if (value === null || value === "") {
			delete styleObj[style];
			return;
		}
		styleObj[style] = value;
	}
	setAttribute(attribute: string, value: string) {
		this.attributes[attribute] = value;
	}
	getAttribute(attribute: string) {
		return this.attributes[attribute];
	}
	removeStyle(style: styleProperty) {
		delete this.baseStyles[style];
		delete this.mobileStyles[style];
		delete this.tabletStyles[style];
	}
	setBaseStyle(style: styleProperty, value: string | number) {
		this.baseStyles[style] = value;
	}
	getStyle(style: styleProperty) {
		const store = useStore();
		if (store.builderState.activeBreakpoint === "mobile") {
			return this.mobileStyles[style] || this.baseStyles[style];
		} else if (store.builderState.activeBreakpoint === "tablet") {
			return this.tabletStyles[style] || this.baseStyles[style];
		}
		return this.baseStyles[style];
	}
	generateId() {
		return Math.random().toString(36).substr(2, 9);
	}
	getIcon() {
		return this.isRoot()
			? "hash"
			: this.isText()
			? "type"
			: this.isImage()
			? "image"
			: this.isContainer()
			? "square"
			: this.isLink()
			? "link"
			: "square";
	}
	isRoot() {
		return this.originalElement === "body";
	}
	getTag() {
		return this.element;
	}
	isDiv() {
		return this.element === "div";
	}
	getStylesCopy() {
		return {
			styles: Object.assign({}, this.baseStyles),
			mobileStyles: Object.assign({}, this.mobileStyles),
			tabletStyles: Object.assign({}, this.tabletStyles),
		};
	}
	getFontFamily() {
		return (
			this.baseStyles.fontFamily || this.mobileStyles.fontFamily || this.tabletStyles.fontFamily || "Inter"
		);
	}
	isHovered(): boolean {
		const store = useStore();
		return store.hoveredBlock === this.blockId;
	}
	isSelected(): boolean {
		const store = useStore();
		return Boolean(store.builderState.selectedBlock) && store.builderState.selectedBlock?.blockId === this.blockId;
	}
	isMovable(): boolean {
		return this.getStyle("position") === "absolute";
	}
	move(direction: "up" | "left" | "down" | "right") {
		if (!this.isMovable()) {
			return;
		}
		let top = getNumberFromPx(this.getStyle("top")) || 0;
		let left = getNumberFromPx(this.getStyle("left")) || 0;
		if (direction === "up") {
			top -= 1;
			this.setStyle("top", addPxToNumber(top));
		} else if (direction === "down") {
			top += 1;
			this.setStyle("top", addPxToNumber(top));
		} else if (direction === "left") {
			left -= 1;
			this.setStyle("left", addPxToNumber(left));
		} else if (direction === "right") {
			left += 1;
			this.setStyle("left", addPxToNumber(left));
		}
	}
	addChild(child: BlockOptions) {
		child.parentBlockId = this.blockId;
		const childBlock = new Block(child);
		this.children.push(childBlock);
		return childBlock;
	}
	getEditorStyles() {
		const styles = reactive({} as BlockStyleMap) ;
		if (this.isButton()) {
			styles.display = "inline-block";
		}

		if (this.isRoot()) {
			this.blockId = "root";
			styles.width = "inherit";
			styles.overflowX = "hidden";
		}

		if (this.isImage() && !this.attributes.src) {
			styles.background = `repeating-linear-gradient(45deg, rgba(180, 180, 180, 0.8) 0px, rgba(180, 180, 180, 0.8) 1px, rgba(255, 255, 255, 0.2) 0px, rgba(255, 255, 255, 0.2) 50%)`;
			styles.backgroundSize = "16px 16px";
		}

		return styles;
	}
	selectBlock() {
		const store = useStore();
		store.builderState.selectedBlock = this;
	}
	getParentBlock(): Block | null {
		const store = useStore();
		return store.findBlock(this.parentBlockId || "root");
	}
	canHaveChildren(): boolean {
		return this.isContainer() || this.isRoot() || this.isDiv();
	}
}

export default Block;
