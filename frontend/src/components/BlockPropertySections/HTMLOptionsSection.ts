import CodeEditor from "@/components/Controls/CodeEditor.vue";
import blockController from "@/utils/blockController";
import { convertSVGBlockToImage, isOversizedSVG } from "@/utils/helpers";
import { Button } from "frappe-ui";
import { computed } from "vue";
import useCanvasStore from "../../stores/canvasStore";
import BasePropertyControl from "../Controls/BasePropertyControl.vue";
import { __ } from "@/translation";

function getSelectedSVG() {
	const block = blockController.getSelectedBlocks()[0];
	const html = block?.getInnerHTML() || "";
	return block?.isSVG() && isOversizedSVG(html) ? html : "";
}

const HTMLOptionsSectionProperties = [
	{
		component: BasePropertyControl,
		getProps: () => {
			return {
				component: CodeEditor,
				type: "HTML",
				label: __("HTML"),
				autofocus: false,
				height: "60px",
				controlType: "key",
				propertyKey: "innerHTML",
				labelPlacement: "top",
				getModelValue: () => blockController.getInnerHTML() || "",
				setModelValue: (val: string) => blockController.setInnerHTML(val),
				allowDynamicValue: true,
				actionButton: {
					label: __("Expand"),
					icon: "lucide-maximize-2",
					handler: () => {
						useCanvasStore().editHTML(blockController.getSelectedBlocks()[0]);
					},
				},
			};
		},
		searchKeyWords: "HTML, InnerHTML, Inner HTML",
		condition: () =>
			blockController.isHTML() || (blockController.getInnerHTML() && !blockController.isText()),
	},
	{
		component: Button,
		getProps: () => {
			return {
				class: "text-base self-end",
			};
		},
		innerText: computed(() => {
			const size = Math.round((getSelectedSVG().length || 0) / 1024);
			return __("Convert to Image File ({0} KB)", [String(size)]);
		}),
		searchKeyWords: "SVG, Convert, Image, File, Upload, Inline, Size, Optimize",
		condition: () => Boolean(getSelectedSVG()),
		events: {
			click: () => {
				const block = blockController.getSelectedBlocks()[0];
				if (block) convertSVGBlockToImage(block);
			},
		},
	},
];

export default {
	name: __("HTML Options"),
	properties: HTMLOptionsSectionProperties,
	condition: () => blockController.isHTML() || (blockController.getInnerHTML() && !blockController.isText()),
};
