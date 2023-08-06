import useStore from "@/store";
import { CSSProperties, nextTick, reactive } from "vue";
import { addPxToNumber, getNumberFromPx, getTextContent } from "./helpers";

export type styleProperty = keyof CSSProperties;

class Block implements BlockOptions {
	blockId: string;
	blockName?: string;
	element?: string;
	children: Array<Block>;
	draggable?: boolean;
	baseStyles: BlockStyleMap;
	rawStyles: BlockStyleMap;
	mobileStyles: BlockStyleMap;
	tabletStyles: BlockStyleMap;
	attributes: BlockAttributeMap;
	classes: Array<string>;
	innerText?: string;
	innerHTML?: string;
	extendedFromComponent?: string;
	blockData?: BlockData;
	originalElement?: string | undefined;
	constructor(options: BlockOptions) {
		this.element = options.element;
		this.innerHTML = options.innerHTML;
		this.extendedFromComponent = options.extendedFromComponent;

		this.blockData = options.blockData;

		if (options.innerText) {
			this.innerHTML = options.innerText;
		}

		this.originalElement = options.originalElement;

		if (!options.blockId || options.blockId === "root") {
			this.blockId = this.generateId();
		} else {
			this.blockId = options.blockId;
		}
		this.children = (options.children || []).map((child: BlockOptions) => {
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

		if (this.isRoot()) {
			this.blockId = "root";
			this.draggable = false;
			this.setBaseStyle("minHeight", "100vh");
		}
	}

	getStyles(breakpoint: string = "desktop") {
		if (this.isComponent()) {
			return this.getComponentStyles(breakpoint);
		}
		let styleObj = this.baseStyles;
		if (breakpoint === "mobile") {
			styleObj = { ...styleObj, ...this.mobileStyles };
		} else if (breakpoint === "tablet") {
			styleObj = { ...styleObj, ...this.tabletStyles };
		}
		styleObj = { ...styleObj, ...this.rawStyles };
		return styleObj;
	}
	getComponent() {
		const store = useStore();
		return store.getComponentBlock(this.extendedFromComponent as string);
	}

	getComponentStyles(breakpoint: string): BlockStyleMap {
		return this.getComponent()?.getStyles(breakpoint);
	}

	getAttributes() {
		if (this.isComponent()) {
			return this.getComponentAttributes();
		}
		return this.attributes;
	}
	getComponentAttributes() {
		return this.getComponent()?.attributes || {};
	}

	getClasses() {
		if (this.isComponent()) {
			return this.getComponentClasses();
		}
		return this.classes;
	}

	getComponentClasses() {
		return this.getComponent()?.classes || [];
	}

	getChildren() {
		if (this.isComponent()) {
			return this.getComponentChildren();
		}
		return this.children;
	}

	hasChildren() {
		return this.getChildren().length > 0;
	}

	getComponentChildren() {
		return this.getComponent()?.children || [];
	}

	getBlockDescription() {
		if (this.isComponent()) {
			return this.getComponentBlockDescription();
		}
		if (this.isHTML()) {
			return "raw";
		}
		let description = this.blockName || this.originalElement || this.element;
		if (this.innerHTML && !this.blockName) {
			description += " | " + this.getTextContent();
		}
		return description;
	}
	getComponentBlockDescription() {
		const store = useStore();
		return store.getComponentName(this.extendedFromComponent as string);
	}
	getTextContent() {
		let editor = this.getEditor();
		let text = "";
		if (this.isText() && editor) {
			text = editor.getText();
		}
		return text || getTextContent(this.innerHTML || "");
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
		return ["span", "h1", "p", "b", "h2", "h3", "h4", "h5", "h6", "label"].includes(this.element);
	}
	isContainer() {
		return ["section", "div"].includes(this.element);
	}
	isInput() {
		return this.originalElement === "input" || this.element === "input";
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
		switch (true) {
			case this.isRoot():
				return "hash";
			case this.isRepeater():
				return "database";
			case this.isHTML():
				return "code";
			case this.isText():
				return "type";
			case this.isContainer():
				return "square";
			case this.isImage():
				return "image";
			case this.isLink():
				return "link";
			default:
				return "square";
		}
	}
	isRoot() {
		return this.originalElement === "body";
	}
	getTag() {
		if (this.isComponent()) {
			return this.getComponentTag();
		}
		if (this.isButton() || this.isInput()) {
			return "div";
		}
		return this.element;
	}

	getComponentTag() {
		return this.getComponent()?.element || "div";
	}

	isDiv() {
		return this.element === "div";
	}
	getStylesCopy() {
		return {
			baseStyles: Object.assign({}, this.baseStyles),
			mobileStyles: Object.assign({}, this.mobileStyles),
			tabletStyles: Object.assign({}, this.tabletStyles),
		};
	}
	isHovered(): boolean {
		const store = useStore();
		return store.hoveredBlock === this.blockId;
	}
	isSelected(): boolean {
		const store = useStore();
		return store.selectedBlocks.some((block: Block) => block.blockId === this.blockId);
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
			top -= 10;
			this.setStyle("top", addPxToNumber(top));
		} else if (direction === "down") {
			top += 10;
			this.setStyle("top", addPxToNumber(top));
		} else if (direction === "left") {
			left -= 10;
			this.setStyle("left", addPxToNumber(left));
		} else if (direction === "right") {
			left += 10;
			this.setStyle("left", addPxToNumber(left));
		}
	}
	addChild(child: BlockOptions, index?: number, extendedFromComponent?: string) {
		if (extendedFromComponent) {
			child.extendedFromComponent = extendedFromComponent;
		}
		const childBlock = new Block(child);
		if (index !== undefined) {
			this.children.splice(index, 0, childBlock);
		} else {
			this.children.push(childBlock);
		}
		return childBlock;
	}
	removeChild(child: Block) {
		const index = this.children.findIndex((block) => block.blockId === child.blockId);
		if (index > -1) {
			this.children.splice(index, 1);
		}
	}
	addChildAfter(child: BlockOptions, siblingBlock: Block) {
		const siblingIndex = this.children.findIndex((block) => block.blockId === siblingBlock.blockId);
		return this.addChild(child, siblingIndex + 1);
	}
	getEditorStyles() {
		const styles = reactive({} as BlockStyleMap);

		if (this.isRoot()) {
			styles.width = "inherit";
			styles.overflowX = "hidden";
		}

		if (this.isImage() && !this.attributes.src) {
			styles.background = `repeating-linear-gradient(45deg, rgba(180, 180, 180, 0.8) 0px, rgba(180, 180, 180, 0.8) 1px, rgba(255, 255, 255, 0.2) 0px, rgba(255, 255, 255, 0.2) 50%)`;
			styles.backgroundSize = "16px 16px";
		}

		if (this.isButton() && this.children.length === 0) {
			styles.display = "flex";
			styles.alignItems = "center";
			styles.justifyContent = "center";
		}

		return styles;
	}
	selectBlock() {
		const store = useStore();
		store.selectedBlocks = [this];
	}
	toggleSelectBlock() {
		const store = useStore();
		if (this.isSelected()) {
			store.selectedBlocks = store.selectedBlocks.filter((block: Block) => block.blockId !== this.blockId);
		} else {
			store.selectedBlocks.push(this);
		}
	}
	getParentBlock(): Block | null {
		const store = useStore();
		return store.findParentBlock(this.blockId);
	}
	canHaveChildren(): boolean {
		return this.isContainer() || this.isRoot() || this.isDiv();
	}
	updateStyles(styles: BlockStyleObjects) {
		this.baseStyles = Object.assign({}, this.baseStyles, styles.baseStyles);
		this.mobileStyles = Object.assign({}, this.mobileStyles, styles.mobileStyles);
		this.tabletStyles = Object.assign({}, this.tabletStyles, styles.tabletStyles);
	}
	getBackgroundColor() {
		return this.getStyle("backgroundColor") || "transparent";
	}
	getFontFamily() {
		const editor = this.getEditor();
		if (this.isText() && editor && editor.isEditable) {
			return editor.getAttributes("textStyle").fontFamily;
		}
		return this.getStyle("fontFamily");
	}
	setFontFamily(fontFamily: string) {
		const editor = this.getEditor();
		if (this.isText() && editor && editor.isEditable) {
			editor.chain().focus().setFontFamily(fontFamily).run();
		} else {
			this.setStyle("fontFamily", fontFamily);
		}
	}
	getTextColor() {
		const editor = this.getEditor();
		if (this.isText() && editor && editor.isEditable) {
			return editor.getAttributes("textStyle").color;
		} else {
			return this.getStyle("color");
		}
	}
	getEditor(): any {
		return null;
	}
	setTextColor(color: string) {
		const editor = this.getEditor();
		if (this.isText() && editor && editor.isEditable) {
			editor.chain().focus().setColor(color).run();
		} else {
			this.setStyle("color", color);
		}
	}
	isHTML() {
		return this.originalElement === "__raw_html__";
	}
	makeBlockEditable() {
		const store = useStore();
		this.selectBlock();
		store.builderState.editableBlock = this;
		nextTick(() => {
			this.getEditor()?.commands.focus("all");
		});
	}
	isComponent() {
		return Boolean(this.extendedFromComponent);
	}
	convertToRepeater() {
		this.setBaseStyle("display", "flex");
		this.setBaseStyle("flexDirection", "column");
		this.setBaseStyle("alignItems", "flex-start");
		this.setBaseStyle("justifyContent", "flex-start");
		this.setBaseStyle("flexWrap", "wrap");
		this.setBaseStyle("width", "fit-content");
		this.setBaseStyle("height", "fit-content");
		this.blockData = [1, 2, 3];
	}
	moveChild(child: Block, index: number) {
		const childIndex = this.children.findIndex((block) => block.blockId === child.blockId);
		if (childIndex > -1) {
			this.children.splice(childIndex, 1);
			this.children.splice(index, 0, child);
		}
	}
	isRepeater() {
		return Array.isArray(this.blockData);
	}
}

export default Block;
