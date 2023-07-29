import Block from "./block";

export default class Component extends Block {
	constructor(options: ComponentOptions) {
		super(options);
		this.isComponent = true;
	}
}
