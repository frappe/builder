/* eslint-disable */
declare module "~icons/*" {
	import type { FunctionalComponent, SVGAttributes } from "vue";
	const component: FunctionalComponent<SVGAttributes>;
	export default component;
}
declare module "*.vue" {
	import type { DefineComponent } from "vue";
	const component: DefineComponent<{}, {}, any>;
	export default component;
}
declare module "*.svg?raw" {
	const content: string;
	export default content;
}
