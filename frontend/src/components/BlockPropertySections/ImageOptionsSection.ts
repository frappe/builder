import AttributePropertyControl from "@/components/Controls/AttributePropertyControl.vue";
import ImageFocusInput from "@/components/Controls/ImageFocusInput.vue";
import ImageUploadInput from "@/components/ImageUploadInput.vue";
import blockController from "@/utils/blockController";
import { getOptimizeButtonText, optimizeImage, shouldShowOptimizeButton } from "@/utils/imageUtils";
import { Button } from "frappe-ui";
import { computed } from "vue";
import { __ } from "@/translation";

const imageOptionsSectionProperties = [
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				component: ImageUploadInput,
				propertyKey: "src",
				label: __("Image URL"),
				allowDynamicValue: true,
				popoverOffset: 120,
				imageFit: blockController.getStyle("objectFit"),
				variants: [{ name: "dark", property: "darkSrc", label: __("Dark Mode") }],
			};
		},
		events: {
			"update:imageURL": (val: string) => blockController.setAttribute("src", val),
			"update:imageFit": (val: StyleValue) => blockController.setStyle("objectFit", val),
		},
		searchKeyWords:
			"Image, URL, Src, Fit, ObjectFit, Object Fit, Fill, Contain, Cover, Dark, Mode, Dark Mode, Theme",
		usedStyleProperties: ["object-fit"],
	},
	{
		component: ImageFocusInput,
		getProps: () => {
			return {
				label: __("Focus Point"),
				imageSrc: (blockController.getAttribute("src") as string) || "",
				modelValue: (blockController.getStyle("objectPosition") as string) || "",
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setStyle("objectPosition", val),
		},
		searchKeyWords: "Focus, Focal, Point, Crop, Framing, Position, Object Position, ObjectPosition",
		usedStyleProperties: ["object-position"],
		condition: () =>
			blockController.isImage() &&
			blockController.getStyle("objectFit") === "cover" &&
			Boolean(blockController.getAttribute("src")),
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
				propertyKey: "alt",
				label: __("Alt Text"),
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
	name: __("Image Options"),
	properties: imageOptionsSectionProperties,
	condition: () => blockController.isImage(),
};
