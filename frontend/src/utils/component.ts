import { WebPageComponent } from "@/types/WebsiteBuilder/WebPageComponent";
import Block from "./block";

interface ComponentOptions extends BlockOptions {
	component: WebPageComponent;
	componentData: ComponentData;
}
export default class Component extends Block {
	constructor(options: ComponentOptions) {
		super(options);
	}
}
