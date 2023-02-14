class BlockProperties {
	constructor(options) {
		Object.assign(this, options);
		this.blockID = this.blockID || this.generateId();
		if (this.children && this.children.length) {
			this.children = this.children.map(child => new BlockProperties(child));
		}
	}
	isImage() {
		return this.element === "img";
	}
	isText() {
		return this.element === "span";
	}
	isContainer() {
		return this.element === "section";
	}
	setStyle(style, value) {
		this.styles[style] = value;
	}
	generateId() {
		return Math.random().toString(36).substr(2, 9);
	}
}

export default BlockProperties;
