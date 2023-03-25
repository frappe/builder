import useStore from "../store";

class BlockProperties {
	constructor(options) {
		delete options.computedStyles;
		Object.assign(this, options);
		if (this.isRoot()) {
			this.blockId = 'root';
			this.editorStyles = {
				height: "fit-content",
				minHeight: "100%",
				width: "inherit",
				position: "absolute",
				top: 0,
				left: 0,
				bottom: 0,
				right: 0,
			};
			this.draggable = false;
		}
		this.blockId = this.blockId || this.generateId();
		if (this.children && this.children.length) {
			this.children = this.children.map(child => new BlockProperties(child));
		}
		this.styles = this.styles || {};
		this.mobileStyles = this.mobileStyles || {};
		this.tabletStyles = this.tabletStyles || {};
		this.editorStyles = this.editorStyles || {};

		this.computedStyles = new Proxy(this.styles, {
			set: (target, prop, value) => {
				this.setStyle(prop, value);
			},
			get: (target, prop) => {
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
	setStyle(style, value) {
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
	getStyle(style) {
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
}

export default BlockProperties;
