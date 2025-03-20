import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import { Editor } from "@tiptap/vue-3";
import { clamp } from "@vueuse/core";
import { computed, nextTick, reactive } from "vue";
import {
	addPxToNumber,
	dataURLtoFile,
	getBlockCopy,
	getBlockInstance,
	getNumberFromPx,
	getTextContent,
	kebabToCamelCase,
	uploadImage,
} from "./helpers";

type BlockDataKeyType = "key" | "attribute" | "style";

export interface BlockDataKey {
	key?: string;
	type?: BlockDataKeyType;
	property?: string;
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
	referenceBlockId?: string;
	isRepeaterBlock?: boolean;
	visibilityCondition?: string;
	elementBeforeConversion?: string;
	parentBlock: Block | null;
	// @ts-expect-error
	referenceComponent: Block | null;
	customAttributes: BlockAttributeMap;
	constructor(options: BlockOptions) {
		const componentStore = useComponentStore();
		this.element = options.element;
		this.innerHTML = options.innerHTML;
		this.extendedFromComponent = options.extendedFromComponent;
		this.isRepeaterBlock = options.isRepeaterBlock;
		this.isChildOfComponent = options.isChildOfComponent;
		this.referenceBlockId = options.referenceBlockId;
		this.visibilityCondition = options.visibilityCondition;
		this.parentBlock = options.parentBlock || null;
		if (this.extendedFromComponent) {
			componentStore.loadComponent(this.extendedFromComponent);
		}
		// to keep this property out of block reactivity
		Object.defineProperty(this, "referenceComponent", {
			value: computed(() => {
				if (this.extendedFromComponent) {
					return componentStore.getComponentBlock(this.extendedFromComponent as string) || null;
				} else if (this.isChildOfComponent) {
					const componentBlock = componentStore.getComponentBlock(this.isChildOfComponent as string);
					return findBlock(this.referenceBlockId as string, [componentBlock]);
				}
				return null;
			}),
			enumerable: false,
		});

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
			child.parentBlock = this;
			return getBlockInstance(child);
		});

		this.baseStyles = reactive(options.styles || options.baseStyles || {});
		this.rawStyles = reactive(options.rawStyles || {});
		this.customAttributes = reactive(options.customAttributes || {});
		this.mobileStyles = reactive(options.mobileStyles || {});
		this.tabletStyles = reactive(options.tabletStyles || {});
		this.attributes = reactive(options.attributes || {});

		this.blockName = options.blockName;
		delete this.attributes.style;
		this.classes = options.classes || [];

		if (this.isRoot()) {
			this.blockId = "root";
			this.draggable = false;
			this.removeStyle("minHeight");
		}

		if (this.isImage()) {
			// if src is base64, convert it to a file
			const src = this.getAttribute("src") as string;
			if (src && src.startsWith("data:image")) {
				const file = dataURLtoFile(src, "image.png");
				if (file) {
					this.setAttribute("src", "");
					options.src = "";
					uploadImage(file, true).then((obj) => {
						this.setAttribute("src", obj.fileURL);
					});
				}
			}
		}
	}
	getStyles(breakpoint: string = "desktop"): BlockStyleMap {
		let styleObj = {};
		if (this.isExtendedFromComponent()) {
			styleObj = this.getComponentStyles(breakpoint);
		}
		styleObj = { ...styleObj, ...this.baseStyles };
		if (["mobile", "tablet"].includes(breakpoint)) {
			styleObj = { ...styleObj, ...this.tabletStyles };
			if (breakpoint === "mobile") {
				styleObj = { ...styleObj, ...this.mobileStyles };
			}
		}
		styleObj = { ...styleObj, ...this.rawStyles };
		// replace variables with values
		// Object.keys(styleObj).forEach((style) => {
		// 	const value = styleObj[style];
		// 	if (typeof value === "string" && value.startsWith("--")) {
		// 		styleObj[style] = this.getVariableValue(value);
		// 	}
		// });

		return styleObj;
	}
	hasOverrides(breakpoint: string) {
		if (breakpoint === "mobile") {
			return Object.keys(this.mobileStyles).length > 0;
		}
		if (breakpoint === "tablet") {
			return Object.keys(this.tabletStyles).length > 0;
		}
		return false;
	}
	resetOverrides(breakpoint: string) {
		if (breakpoint === "mobile") {
			this.mobileStyles = {};
		}
		if (breakpoint === "tablet") {
			this.tabletStyles = {};
		}
	}
	getComponentStyles(breakpoint: string): BlockStyleMap {
		return this.referenceComponent?.getStyles(breakpoint) || {};
	}
	getAttributes(): BlockAttributeMap {
		let attributes = {};
		if (this.isExtendedFromComponent()) {
			attributes = this.getComponentAttributes();
		}
		attributes = { ...attributes, ...this.attributes };
		return attributes;
	}
	getComponentAttributes() {
		return this.referenceComponent?.attributes || {};
	}
	getClasses() {
		let classes = [] as Array<string>;
		if (this.isExtendedFromComponent()) {
			classes = this.getComponentClasses();
		}
		classes = [...classes, ...this.classes];
		return classes;
	}
	getComponentClasses() {
		return this.referenceComponent?.classes || [];
	}
	getChildren() {
		return this.children;
	}
	hasChildren() {
		return this.getChildren().length > 0;
	}
	getCustomAttributes() {
		let customAttributes = {};
		if (this.isExtendedFromComponent()) {
			customAttributes = this.referenceComponent?.customAttributes || {};
		}
		customAttributes = { ...customAttributes, ...this.customAttributes };
		return customAttributes;
	}
	getRawStyles() {
		let rawStyles = {};
		if (this.isExtendedFromComponent()) {
			rawStyles = this.referenceComponent?.rawStyles || {};
		}
		rawStyles = { ...rawStyles, ...this.rawStyles };
		return rawStyles;
	}
	getVisibilityCondition() {
		let visibilityCondition = this.visibilityCondition;
		if (this.isExtendedFromComponent() && this.referenceComponent?.visibilityCondition) {
			visibilityCondition = this.referenceComponent?.visibilityCondition;
		}
		return visibilityCondition;
	}
	getBlockDescription() {
		if (this.extendedFromComponent) {
			return this.getComponentBlockDescription() || "";
		}
		if (this.isHTML() && !this.blockName) {
			const innerHTML = this.getInnerHTML() || "";
			const match = innerHTML.match(/<([a-z]+)[^>]*>/);
			if (match) {
				return `${match[1]}`;
			} else {
				return "raw";
			}
		}
		let description = this.blockName || this.originalElement || this.getElement() || "";
		if (this.getTextContent() && !this.blockName) {
			description += " | " + this.getTextContent();
		}
		return description;
	}
	getComponentBlockDescription() {
		const componentStore = useComponentStore();
		return componentStore.getComponentName(this.extendedFromComponent as string);
	}
	getTextContent() {
		return getTextContent(this.getInnerHTML() || "");
	}
	isImage() {
		return this.getElement() === "img";
	}
	isVideo() {
		return this.getElement() === "video" || this.getInnerHTML()?.startsWith("<video");
	}
	isForm() {
		return this.getElement() === "form";
	}
	isButton() {
		return this.getElement() === "button";
	}
	isLink() {
		return this.getElement() === "a";
	}
	isSVG() {
		return this.getElement() === "svg" || this.getInnerHTML()?.startsWith("<svg");
	}
	isText() {
		return ["span", "h1", "p", "b", "h2", "h3", "h4", "h5", "h6", "label", "a", "cite"].includes(
			this.getElement() as string,
		);
	}
	isContainer() {
		return ["section", "div"].includes(this.getElement() as string);
	}
	isHeader() {
		return ["h1", "h2", "h3", "h4", "h5", "h6"].includes(this.getElement() as string);
	}
	isInput() {
		return (
			this.originalElement === "input" || this.getElement() === "input" || this.getElement() === "textarea"
		);
	}
	setStyle(style: styleProperty, value: StyleValue) {
		const canvasStore = useCanvasStore();
		let styleObj = this.baseStyles;
		style = kebabToCamelCase(style as string) as styleProperty;
		if (canvasStore.activeCanvas?.activeBreakpoint === "mobile") {
			styleObj = this.mobileStyles;
		} else if (canvasStore.activeCanvas?.activeBreakpoint === "tablet") {
			styleObj = this.tabletStyles;
		}
		if (value === null || value === "") {
			delete styleObj[style];
			return;
		}
		styleObj[style] = value;
	}
	setAttribute(attribute: string, value: string | undefined) {
		this.attributes[attribute] = value;
	}
	removeAttribute(attribute: string) {
		this.setAttribute(attribute, undefined);
	}
	getAttribute(attribute: string) {
		return this.getAttributes()[attribute];
	}
	removeStyle(style: styleProperty) {
		delete this.baseStyles[style];
		delete this.mobileStyles[style];
		delete this.tabletStyles[style];
	}
	setBaseStyle(style: styleProperty, value: StyleValue) {
		style = kebabToCamelCase(style as string) as styleProperty;
		this.baseStyles[style] = value;
	}
	getStyle(style: styleProperty, breakpoint?: string | null) {
		const canvasStore = useCanvasStore();
		breakpoint = breakpoint || canvasStore.activeCanvas?.activeBreakpoint;
		let styleValue = undefined as StyleValue;
		if (breakpoint === "mobile") {
			styleValue = this.mobileStyles[style] || this.tabletStyles[style] || this.baseStyles[style];
		} else if (breakpoint === "tablet") {
			styleValue = this.tabletStyles[style] || this.baseStyles[style];
		} else {
			styleValue = this.baseStyles[style];
		}
		if (styleValue === undefined && this.isExtendedFromComponent()) {
			styleValue = this.referenceComponent?.getStyle(style, breakpoint) as StyleValue;
		}
		return styleValue;
	}
	getNativeStyle(style: styleProperty) {
		const canvasStore = useCanvasStore();
		if (canvasStore.activeCanvas?.activeBreakpoint === "mobile") {
			return this.mobileStyles[style];
		}
		if (canvasStore.activeCanvas?.activeBreakpoint === "tablet") {
			return this.tabletStyles[style];
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
			case this.isSVG():
				return "aperture";
			case this.isHTML():
				return "code";
			case this.isLink():
				return "link";
			case this.isText():
				return "type";
			case this.isContainer() && this.isRow():
				return "columns";
			case this.isContainer() && this.isColumn():
				return "credit-card";
			case this.isGrid():
				return "grid";
			case this.isContainer():
				return "square";
			case this.isImage():
				return "image";
			case this.isVideo():
				return "film";
			case this.isForm():
				return "file-text";
			default:
				return "square";
		}
	}
	isRoot() {
		return this.originalElement === "body";
	}
	getTag(): string {
		if (this.isButton() || this.isLink()) {
			return "div";
		}
		return this.getElement() || "div";
	}
	getComponentTag() {
		return this.referenceComponent?.getTag() || "div";
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
	isMovable(): boolean {
		return ["absolute", "fixed"].includes(this.getStyle("position") as string);
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
	addChild(child: BlockOptions, index?: number | null, select: boolean = true) {
		if (index === undefined || index === null) {
			index = this.children.length;
		}
		index = clamp(index, 0, this.children.length);

		const childBlock = getBlockInstance(child);
		childBlock.parentBlock = this;
		this.children.splice(index, 0, childBlock);
		if (select) {
			childBlock.selectBlock();
		}
		if (childBlock.isText()) {
			childBlock.makeBlockEditable();
		}

		if (childBlock.getStyle("position")) {
			if (!this.getStyle("position")) {
				this.setStyle("position", "relative");
			}
		}

		return childBlock;
	}
	removeChild(child: Block) {
		const index = this.getChildIndex(child);
		if (index > -1) {
			this.children.splice(index, 1);
		}
	}
	replaceChild(child: Block, newChild: Block) {
		newChild.parentBlock = this;
		const index = this.getChildIndex(child);
		if (index > -1) {
			// This is not triggering the reactivity even though the child object is reactive
			// this.children.splice(index, 1, newChild);
			this.removeChild(child);
			this.addChild(newChild, index);
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

		if (this.isImage() && !this.getAttribute("src")) {
			styles.background = `repeating-linear-gradient(45deg, rgba(180, 180, 180, 0.8) 0px, rgba(180, 180, 180, 0.8) 1px, rgba(255, 255, 255, 0.2) 0px, rgba(255, 255, 255, 0.2) 50%)`;
			styles.backgroundSize = "16px 16px";
		}

		if (this.isButton() && this.children.length === 0) {
			styles.display = "flex";
			styles.alignItems = "center";
			styles.justifyContent = "center";
		}
		styles.transition = "unset";

		return styles;
	}
	selectBlock() {
		const canvasStore = useCanvasStore();
		nextTick(() => {
			canvasStore.selectBlock(this, null);
		});
	}
	getParentBlock(): Block | null {
		return this.parentBlock || null;
	}
	selectParentBlock() {
		const parentBlock = this.getParentBlock();
		if (parentBlock) {
			parentBlock.selectBlock();
		}
	}
	getSiblingBlock(direction: "next" | "previous") {
		const parentBlock = this.getParentBlock();
		let sibling = null as Block | null;
		if (parentBlock) {
			const index = parentBlock.getChildIndex(this);
			if (direction === "next") {
				sibling = parentBlock.children[index + 1];
			} else {
				sibling = parentBlock.children[index - 1];
			}
			if (sibling) {
				return sibling;
			}
		}
		return null;
	}
	getFirstChild() {
		return this.children[0];
	}
	getLastChild() {
		return this.children[this.children.length - 1];
	}
	selectSiblingBlock(direction: "next" | "previous") {
		const sibling = this.getSiblingBlock(direction);
		if (sibling) {
			sibling.selectBlock();
		}
	}
	canHaveChildren(): boolean {
		return !(
			this.isImage() ||
			this.isSVG() ||
			this.isInput() ||
			this.isVideo() ||
			(this.isText() && !this.isLink()) ||
			this.isExtendedFromComponent()
		);
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
		if (this.isText() && editor && editor.isFocused) {
			return editor.getAttributes("textStyle").fontFamily;
		}
		return this.getStyle("fontFamily");
	}
	setFontFamily(fontFamily: string) {
		const editor = this.getEditor();
		if (this.isText() && editor && editor.isFocused) {
			editor.chain().focus().setFontFamily(fontFamily).run();
		} else {
			this.setStyle("fontFamily", fontFamily);
		}
	}
	getTextColor() {
		const editor = this.getEditor();
		const color = editor?.getAttributes("textStyle").color;
		if (this.isText() && editor && color && editor.isEditable) {
			return color;
		} else {
			return this.getStyle("color");
		}
	}
	getEditor(): null | Editor {
		// @ts-ignore
		return this.__proto__.editor || null;
	}
	setTextColor(color: string) {
		const editor = this.getEditor();
		if (this.isText() && editor && editor.isEditable) {
			editor.chain().setColor(color).run();
		} else {
			this.setStyle("color", color);
		}
	}
	isHTML() {
		return this.originalElement === "__raw_html__";
	}
	isIframe() {
		return this.innerHTML?.startsWith("<iframe");
	}
	makeBlockEditable() {
		const canvasStore = useCanvasStore();
		this.selectBlock();
		canvasStore.editableBlock = this;
		nextTick(() => {
			this.getEditor()?.commands.focus("all");
		});
	}
	isExtendedFromComponent() {
		return Boolean(this.extendedFromComponent) || Boolean(this.isChildOfComponent);
	}
	convertToRepeater() {
		this.setBaseStyle("display", "flex");
		this.setBaseStyle("flexDirection", "column");
		this.setBaseStyle("alignItems", "flex-start");
		this.setBaseStyle("justifyContent", "flex-start");
		this.setBaseStyle("flexWrap", "wrap");
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
	getDataKey(key: keyof BlockDataKey): string {
		let dataKey = (this.dataKey && this.dataKey[key]) || "";
		if (!dataKey && this.isExtendedFromComponent()) {
			dataKey = this.referenceComponent?.getDataKey(key) || "";
		}
		return dataKey;
	}
	setDataKey(key: keyof BlockDataKey, value: BlockDataKeyType) {
		if (!this.dataKey || !this.dataKey[key]) {
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
		if (!innerHTML && this.isExtendedFromComponent()) {
			innerHTML = this.referenceComponent?.getInnerHTML() || "";
		}
		return innerHTML;
	}
	setInnerHTML(innerHTML: string) {
		this.innerHTML = innerHTML;
	}
	toggleVisibility(show: boolean | null = null) {
		if ((this.getStyle("display") === "none" && show !== false) || show === true) {
			this.setStyle("display", this.getStyle("__last_display") || "flex");
			this.setStyle("__last_display", null);
		} else {
			this.setStyle("__last_display", this.getStyle("display"));
			this.setStyle("display", "none");
		}
	}
	isVisible(breakpoint?: string) {
		return this.getStyle("display", breakpoint) !== "none";
	}
	extendFromComponent(componentName: string) {
		this.extendedFromComponent = componentName;
		// @ts-expect-error
		this.referenceComponent?.effect?.run();
		const component = this.referenceComponent as Block;
		if (component) {
			extendWithComponent(this, componentName, component.children);
		}
	}
	isChildOfComponentBlock() {
		return Boolean(this.isChildOfComponent);
	}
	resetWithComponent() {
		const component = this.referenceComponent;
		if (component) {
			resetWithComponent(this, this.extendedFromComponent as string, component.children);
			// TODO: Remove this
			const canvasStore = useCanvasStore();
			canvasStore.activeCanvas?.history?.resume(undefined, true, true);
		}
	}
	syncWithComponent() {
		const component = this.referenceComponent;
		if (component) {
			syncBlockWithComponent(this, this, this.extendedFromComponent as string, component.children);
		}
	}
	resetChanges(resetChildren: boolean = false) {
		resetBlock(this, resetChildren);
	}
	convertToLink() {
		this.elementBeforeConversion = this.element;
		this.element = "a";
	}
	unsetLink() {
		this.removeAttribute("href");
		this.removeAttribute("target");
		if (this.elementBeforeConversion) {
			this.element = this.elementBeforeConversion;
		}
	}
	getElement() {
		if (!this.element && this.isExtendedFromComponent()) {
			return this.referenceComponent?.element;
		}
		return this.element;
	}
	getUsedComponentNames() {
		const componentStore = useComponentStore();
		const componentNames = [] as string[];
		if (this.extendedFromComponent) {
			componentNames.push(this.extendedFromComponent);
		}
		if (this.isChildOfComponent) {
			componentNames.push(this.isChildOfComponent);
		}
		this.children.forEach((child) => {
			componentNames.push(...child.getUsedComponentNames());
		});

		componentNames.forEach((name) => {
			componentNames.push(...componentStore.getComponentBlock(name).getUsedComponentNames());
		});

		return new Set(componentNames);
	}
	isFlex() {
		return this.getStyle("display") === "flex";
	}
	isGrid() {
		return this.getStyle("display") === "grid";
	}
	isRow() {
		return this.isFlex() && this.getStyle("flexDirection") === "row";
	}
	isColumn() {
		return this.isFlex() && this.getStyle("flexDirection") === "column";
	}
	duplicateBlock() {
		if (this.isRoot()) {
			return;
		}
		const canvasStore = useCanvasStore();
		const pauseId = canvasStore.activeCanvas?.history?.pause();
		const blockCopy = getBlockCopy(this);
		const parentBlock = this.getParentBlock();

		if (blockCopy.getStyle("position") === "absolute") {
			// shift the block a bit
			const left = getNumberFromPx(blockCopy.getStyle("left"));
			const top = getNumberFromPx(blockCopy.getStyle("top"));
			blockCopy.setStyle("left", `${left + 20}px`);
			blockCopy.setStyle("top", `${top + 20}px`);
		}

		let child = null as Block | null;
		if (parentBlock) {
			child = parentBlock.addChildAfter(blockCopy, this);
		} else {
			child = canvasStore.activeCanvas?.getRootBlock().addChild(blockCopy) as Block;
		}
		nextTick(() => {
			if (child) {
				child.selectBlock();
				pauseId && canvasStore.activeCanvas?.history?.resume(pauseId, true);
			}
		});
	}
	getPadding() {
		const padding = this.getStyle("padding") || "0px";

		const paddingTop = this.getStyle("paddingTop");
		const paddingBottom = this.getStyle("paddingBottom");
		const paddingLeft = this.getStyle("paddingLeft");
		const paddingRight = this.getStyle("paddingRight");

		if (!paddingTop && !paddingBottom && !paddingLeft && !paddingRight) {
			return padding;
		}

		if (
			paddingTop &&
			paddingBottom &&
			paddingTop === paddingBottom &&
			paddingTop === paddingRight &&
			paddingTop === paddingLeft
		) {
			return paddingTop;
		}

		if (paddingTop && paddingLeft && paddingTop === paddingBottom && paddingLeft === paddingRight) {
			return `${paddingTop} ${paddingLeft}`;
		} else {
			return `${paddingTop || padding} ${paddingRight || padding} ${paddingBottom || padding} ${
				paddingLeft || padding
			}`;
		}
	}
	setPadding(padding: string) {
		// reset padding
		this.setStyle("padding", null);
		this.setStyle("paddingTop", null);
		this.setStyle("paddingBottom", null);
		this.setStyle("paddingLeft", null);
		this.setStyle("paddingRight", null);

		if (!padding) {
			return;
		}

		const paddingArray = padding.split(" ");

		if (paddingArray.length === 1) {
			this.setStyle("padding", paddingArray[0]);
		} else if (paddingArray.length === 2) {
			this.setStyle("paddingTop", paddingArray[0]);
			this.setStyle("paddingBottom", paddingArray[0]);
			this.setStyle("paddingLeft", paddingArray[1]);
			this.setStyle("paddingRight", paddingArray[1]);
		} else if (paddingArray.length === 3) {
			this.setStyle("paddingTop", paddingArray[0]);
			this.setStyle("paddingLeft", paddingArray[1]);
			this.setStyle("paddingRight", paddingArray[1]);
			this.setStyle("paddingBottom", paddingArray[2]);
		} else if (paddingArray.length === 4) {
			this.setStyle("paddingTop", paddingArray[0]);
			this.setStyle("paddingRight", paddingArray[1]);
			this.setStyle("paddingBottom", paddingArray[2]);
			this.setStyle("paddingLeft", paddingArray[3]);
		}
	}
	setMargin(margin: string) {
		// reset margin
		this.setStyle("margin", null);
		this.setStyle("marginTop", null);
		this.setStyle("marginBottom", null);
		this.setStyle("marginLeft", null);
		this.setStyle("marginRight", null);

		if (!margin) {
			return;
		}

		const marginArray = margin.split(" ");

		if (marginArray.length === 1) {
			this.setStyle("margin", marginArray[0]);
		} else if (marginArray.length === 2) {
			this.setStyle("marginTop", marginArray[0]);
			this.setStyle("marginBottom", marginArray[0]);
			this.setStyle("marginLeft", marginArray[1]);
			this.setStyle("marginRight", marginArray[1]);
		} else if (marginArray.length === 3) {
			this.setStyle("marginTop", marginArray[0]);
			this.setStyle("marginLeft", marginArray[1]);
			this.setStyle("marginRight", marginArray[1]);
			this.setStyle("marginBottom", marginArray[2]);
		} else if (marginArray.length === 4) {
			this.setStyle("marginTop", marginArray[0]);
			this.setStyle("marginRight", marginArray[1]);
			this.setStyle("marginBottom", marginArray[2]);
			this.setStyle("marginLeft", marginArray[3]);
		}
	}
	getMargin() {
		const margin = this.getStyle("margin") || "0px";

		const marginTop = this.getStyle("marginTop");
		const marginBottom = this.getStyle("marginBottom");
		const marginLeft = this.getStyle("marginLeft");
		const marginRight = this.getStyle("marginRight");

		if (!marginTop && !marginBottom && !marginLeft && !marginRight) {
			return margin;
		}

		if (
			marginTop &&
			marginBottom &&
			marginTop === marginBottom &&
			marginTop === marginRight &&
			marginTop === marginLeft
		) {
			return marginTop;
		}

		if (marginTop && marginLeft && marginTop === marginBottom && marginLeft === marginRight) {
			return `${marginTop} ${marginLeft}`;
		} else {
			return `${marginTop || margin} ${marginRight || margin} ${marginBottom || margin} ${
				marginLeft || margin
			}`;
		}
	}
}

function extendWithComponent(
	block: Block | BlockOptions,
	extendedFromComponent: string | undefined,
	componentChildren: Block[],
	resetOverrides: boolean = true,
) {
	resetBlock(block, false, resetOverrides);
	block.children?.forEach((child, index) => {
		child.isChildOfComponent = extendedFromComponent;
		let componentChild = componentChildren[index];
		if (child.extendedFromComponent) {
			const component = child.referenceComponent;
			child.referenceBlockId = componentChild.blockId;
			extendWithComponent(child, child.extendedFromComponent, component.children, false);
		} else if (componentChild) {
			child.referenceBlockId = componentChild.blockId;
			extendWithComponent(child, extendedFromComponent, componentChild.children, resetOverrides);
		}
	});
}

function resetWithComponent(
	block: Block | BlockOptions,
	extendedWithComponent: string,
	componentChildren: Block[],
	resetOverrides: boolean = true,
) {
	resetBlock(block, true, resetOverrides);
	block.children?.splice(0, block.children.length);
	componentChildren.forEach((componentChild) => {
		const blockComponent = getBlockCopy(componentChild);
		blockComponent.isChildOfComponent = extendedWithComponent;
		blockComponent.referenceBlockId = componentChild.blockId;
		const childBlock = block.addChild(blockComponent, null, false);
		if (componentChild.extendedFromComponent) {
			const component = childBlock.referenceComponent;
			resetWithComponent(childBlock, componentChild.extendedFromComponent, component.children, false);
		} else {
			resetWithComponent(childBlock, extendedWithComponent, componentChild.children, resetOverrides);
		}
	});
}

function syncBlockWithComponent(
	parentBlock: Block,
	block: Block,
	componentName: string,
	componentChildren: Block[],
) {
	componentChildren.forEach((componentChild, index) => {
		const blockExists = findComponentBlock(componentChild.blockId, parentBlock.children);
		if (!blockExists) {
			const blockComponent = getBlockCopy(componentChild);
			blockComponent.isChildOfComponent = componentName;
			blockComponent.referenceBlockId = componentChild.blockId;
			resetBlock(blockComponent);
			resetWithComponent(blockComponent, componentName, componentChild.children);
			block.addChild(blockComponent, index, false);
		}
	});

	block.children.forEach((child) => {
		const componentChild = componentChildren.find((c) => c.blockId === child.referenceBlockId);
		if (componentChild) {
			syncBlockWithComponent(parentBlock, child, componentName, componentChild.children);
		}
	});
}

function findComponentBlock(blockId: string, blocks: Block[]): Block | null {
	for (const block of blocks) {
		if (block.referenceBlockId === blockId) {
			return block;
		}
		if (block.children) {
			const found = findComponentBlock(blockId, block.children);
			if (found) {
				return found;
			}
		}
	}
	return null;
}

function resetBlock(
	block: Block | BlockOptions,
	resetChildren: boolean = true,
	resetOverrides: boolean = true,
) {
	block.blockId = block.generateId();
	if (resetOverrides) {
		delete block.innerHTML;
		delete block.element;
		block.baseStyles = {};
		block.rawStyles = {};
		block.mobileStyles = {};
		block.tabletStyles = {};
		block.attributes = {};
		block.customAttributes = {};
		block.classes = [];
		block.dataKey = null;
	}

	if (resetChildren) {
		block.children?.forEach((child) => {
			resetBlock(child, resetChildren, !Boolean(child.extendedFromComponent));
		});
	}
}

function findBlock(blockId: string, blocks: Block[]): Block | null {
	for (const block of blocks) {
		if (block.blockId === blockId) {
			return block;
		}
		if (block.children) {
			const found = findBlock(blockId, block.children);
			if (found) {
				return found;
			}
		}
	}
	return null;
}

export default Block;
