import AttributePropertyControl from "@/components/Controls/AttributePropertyControl.vue";
import ImageUploadInput from "@/components/ImageUploadInput.vue";
import blockController from "@/utils/blockController";
import { getOptimizeButtonText, optimizeImage, shouldShowOptimizeButton } from "@/utils/imageUtils";
import { Button } from "frappe-ui";
import { computed } from "vue";

const imageOptionsSectionProperties = [
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				component: ImageUploadInput,
				styleProperty: "src",
				label: "Image URL",
				allowDynamicValue: true,
				popoverOffset: 120,
				imageFit: blockController.getStyle("objectFit"),
				variants: [{ name: "dark", property: "darkSrc", label: "Dark Mode" }],
			};
		},
		events: {
			"update:imageURL": (val: string) => blockController.setAttribute("src", val),
			"update:imageFit": (val: StyleValue) => blockController.setStyle("objectFit", val),
		},
		searchKeyWords:
			"Image, URL, Src, Fit, ObjectFit, Object Fit, Fill, Contain, Cover, Dark, Mode, Dark Mode, Theme",
	},
	{
		component: Button,
		getProps: () => {
			return {
				class: "text-base self-end",
			};
		},
		innerText: computed(() => {
			const block = blockController.getSelectedBlocks()[0];
			const imageUrl = (block?.getAttribute("src") as string) || "";
			return getOptimizeButtonText(imageUrl);
		}),
		searchKeyWords:
			"Image, Local, Copy, Server, Download, Host, Store, Convert, webp, Convert to webp, image, src, url",
		events: {
			click: () => {
				const block = blockController.getSelectedBlocks()[0];
				const imageUrl = block.getAttribute("src") as string;

				return optimizeImage({
					imageUrl,
					onSuccess: (newUrl: string) => {
						block.setAttribute("src", newUrl);
					},
				});
			},
		},
		condition: () => {
			if (!blockController.isImage()) {
				return false;
			}
			const imageUrl = blockController.getAttribute("src") as string;
			return shouldShowOptimizeButton(imageUrl);
		},
	},
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				styleProperty: "alt",
				label: "Alt Text",
				allowDynamicValue: true,
				getModelValue: () => blockController.getAttribute("alt") || "",
				setModelValue: (val: string) => blockController.setAttribute("alt", val),
			};
		},
		searchKeyWords: "Alt, Text, AltText, Alternate Text",
		condition: () => blockController.isImage(),
	},
];

export default {
	name: "Image Options",
	properties: imageOptionsSectionProperties,
	condition: () => blockController.isImage(),
};
