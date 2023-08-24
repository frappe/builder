import useStore from "@/store";
import { Editor } from "@tiptap/vue-3";
import { clamp } from "@vueuse/core";
import { CSSProperties, nextTick, reactive } from "vue";
import { addPxToNumber, getNumberFromPx, getTextContent, kebabToCamelCase } from "./helpers";

export type styleProperty = keyof CSSProperties;

export interface BlockDataKey {
	key?: string;
	type?: string;
	property?: string;
}

function resetBlock(block: Block | BlockOptions) {
	delete block.innerHTML;
	delete block.element;
	block.baseStyles = {};
	block.rawStyles = {};
	block.mobileStyles = {};
	block.tabletStyles = {};
	block.attributes = {};
	block.classes = [];
	block.children = [];
}

class Block implements BlockOptions {
	blockId: string;
	children: Array<Block>;
	baseStyles: BlockStyleMap;
	rawStyles: BlockStyleMap;
	mobileStyles: BlockStyleMap;
	tabletStyles: BlockStyleMap;
	attributes: BlockAttributeMap;
	classes: Array<string>;
	dataKey?: BlockDataKey | null = null;
	blockName?: string;
	element?: string;
	draggable?: boolean;
	innerText?: string;
	innerHTML?: string;
	extendedFromComponent?: string;
	originalElement?: string | undefined;
	isChildOfComponent?: string;
	isRepeaterBlock?: boolean;
	constructor(options: BlockOptions) {
		this.element = options.element;
		this.innerHTML = options.innerHTML;
		this.extendedFromComponent = options.extendedFromComponent;
		this.isRepeaterBlock = options.isRepeaterBlock;
		this.isChildOfComponent = options.isChildOfComponent;

		this.dataKey = options.dataKey || null;

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
			return reactive(new Block(child));
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
		let styleObj = {};
		if (this.isComponent()) {
			styleObj = this.getComponentStyles(breakpoint);
		}
		styleObj = { ...styleObj, ...this.baseStyles };
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
		if (this.extendedFromComponent) {
			return store.getComponentBlock(this.extendedFromComponent as string);
		}
		if (this.isChildOfComponent) {
			return store.getComponentBlock(this.isChildOfComponent as string).children.find((child) => {
				return child.blockId === this.blockId;
			}) as Block;
		}
		return this;
	}
	getComponentStyles(breakpoint: string): BlockStyleMap {
		return this.getComponent()?.getStyles(breakpoint);
	}
	getAttributes() {
		let attributes = {};
		if (this.isComponent()) {
			attributes = this.getComponentAttributes();
		}
		attributes = { ...attributes, ...this.attributes };
		return attributes;
	}
	getComponentAttributes() {
		return this.getComponent()?.attributes || {};
	}
	getClasses() {
		let classes = [] as Array<string>;
		if (this.isComponent()) {
			classes = this.getComponentClasses();
		}
		classes = [...classes, ...this.classes];
		return classes;
	}
	getComponentClasses() {
		return this.getComponent()?.classes || [];
	}
	getChildren() {
		return this.children;
	}
	hasChildren() {
		return this.getChildren().length > 0;
	}
	getComponentChildren() {
		return this.getComponent()?.children || [];
	}

	getBlockDescription() {
		if (this.isComponent() && !this.isChildOfComponentBlock()) {
			return this.getComponentBlockDescription();
		}
		if (this.isHTML()) {
			return "raw";
		}
		let description = this.blockName || this.originalElement || this.getElement();
		if (this.getTextContent() && !this.blockName) {
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
		return text || getTextContent(this.getInnerHTML() || "");
	}
	isImage() {
		return this.getElement() === "img";
	}
	isButton() {
		return this.getElement() === "button";
	}
	isLink() {
		return this.getElement() === "a";
	}
	isText() {
		return ["span", "h1", "p", "b", "h2", "h3", "h4", "h5", "h6", "label", "a"].includes(
			this.getElement() as string
		);
	}
	isContainer() {
		return ["section", "div"].includes(this.getElement() as string);
	}
	isInput() {
		return this.originalElement === "input" || this.getElement() === "input";
	}
	setStyle(style: styleProperty, value: StyleValue) {
		const store = useStore();
		let styleObj = this.baseStyles;
		style = kebabToCamelCase(style) as styleProperty;
		if (store.activeBreakpoint === "mobile") {
			styleObj = this.mobileStyles;
		} else if (store.activeBreakpoint === "tablet") {
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
	setBaseStyle(style: styleProperty, value: StyleValue) {
		style = kebabToCamelCase(style) as styleProperty;
		this.baseStyles[style] = value;
	}
	getStyle(style: styleProperty) {
		const store = useStore();
		if (store.activeBreakpoint === "mobile") {
			return this.mobileStyles[style] || this.baseStyles[style];
		} else if (store.activeBreakpoint === "tablet") {
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
			case this.isLink():
				return "link";
			case this.isText():
				return "type";
			case this.isContainer():
				return "square";
			case this.isImage():
				return "image";

			default:
				return "square";
		}
	}
	isRoot() {
		return this.originalElement === "body";
	}
	getTag(): string {
		if (this.isButton()) {
			return "div";
		}
		return this.getElement() || "div";
	}
	getComponentTag() {
		return this.getComponent()?.getTag() || "div";
	}
	isDiv() {
		return this.getElement() === "div";
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
	addChild(child: BlockOptions, index?: number) {
		if (index === undefined) {
			index = this.children.length;
		}
		index = clamp(index, 0, this.children.length);

		const childBlock = reactive(new Block(child));
		this.children.splice(index, 0, childBlock);
		return childBlock;
	}
	removeChild(child: Block) {
		const index = this.getChildIndex(child);
		if (index > -1) {
			this.children.splice(index, 1);
		}
	}
	getChildIndex(child: Block) {
		return this.children.findIndex((block) => block.blockId === child.blockId);
	}
	addChildAfter(child: BlockOptions, siblingBlock: Block) {
		const siblingIndex = this.getChildIndex(siblingBlock);
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
	getEditor(): null | Editor {
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
		return Boolean(this.extendedFromComponent) || Boolean(this.isChildOfComponent);
	}
	convertToRepeater() {
		this.setBaseStyle("display", "flex");
		this.setBaseStyle("flexDirection", "column");
		this.setBaseStyle("alignItems", "flex-start");
		this.setBaseStyle("justifyContent", "flex-start");
		this.setBaseStyle("flexWrap", "wrap");
		this.setBaseStyle("width", "fit-content");
		this.setBaseStyle("height", "fit-content");
		this.setBaseStyle("gap", "20px");
		this.isRepeaterBlock = true;
	}
	moveChild(child: Block, index: number) {
		const childIndex = this.children.findIndex((block) => block.blockId === child.blockId);
		if (childIndex > -1) {
			this.children.splice(childIndex, 1);
			this.children.splice(index, 0, child);
		}
	}
	isRepeater() {
		return this.isRepeaterBlock;
	}
	getDataKey(key: keyof BlockDataKey) {
		return this.dataKey && this.dataKey[key];
	}
	setDataKey(key: keyof BlockDataKey, value: string) {
		if (!this.dataKey) {
			this.dataKey = {
				key: "",
				type: this.isImage() || this.isLink() ? "attribute" : "key",
				property: this.isLink() ? "href" : this.isImage() ? "src" : "innerHTML",
			};
		}
		this.dataKey[key] = value;
	}
	getInnerHTML(): string {
		let innerHTML = this.innerHTML || "";
		if (!innerHTML && this.isComponent()) {
			innerHTML = this.getComponent().getInnerHTML();
		}
		return innerHTML;
	}
	setInnerHTML(innerHTML: string) {
		this.innerHTML = innerHTML;
	}
	toggleVisibility() {
		if (this.getStyle("display") === "none") {
			this.setStyle("display", "block");
		} else {
			this.setStyle("display", "none");
		}
	}
	isVisible() {
		return this.getStyle("display") !== "none";
	}
	extendFromComponent(componentName: string) {
		resetBlock(this);
		this.extendedFromComponent = componentName;
		this.children.push(...this.getComponentChildrenCopy());
	}
	isChildOfComponentBlock() {
		return Boolean(this.isChildOfComponent);
	}
	getComponentChildrenCopy() {
		const store = useStore();
		const children = [] as Block[];
		const componentChildren = this.getComponentChildren();
		componentChildren.forEach((componentChild) => {
			const componentChildClone = store.getBlockCopy(componentChild, true);
			componentChildClone.isChildOfComponent = this.extendedFromComponent;
			children.push(componentChildClone);
		});
		return children;
	}
	resetChanges() {
		resetBlock(this);
		this.children = this.getComponentChildrenCopy();
	}
	convertToLink() {
		this.element = "a";
		this.attributes.href = "#";
	}
	getElement() {
		if (this.isComponent()) {
			return this.getComponent()?.element || "div";
		}
		return this.element;
	}
}

export default Block;
