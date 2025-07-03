import StyleControl from "@/components/Controls/StyleControl.vue";
import ImageUploadInput from "@/components/ImageUploadInput.vue";
import blockController from "@/utils/blockController";
import { Button, createResource } from "frappe-ui";
import { toast } from "vue-sonner";

const imageOptionsSectionProperties = [
	{
		component: StyleControl,
		getProps: () => {
			return {
				component: ImageUploadInput,
				controlType: "attribute",
				styleProperty: "src",
				label: "Image URL",
				allowDynamicValue: true,
				enableStates: false,
				imageURL: blockController.getAttribute("src"),
				imageFit: blockController.getStyle("objectFit"),
			};
		},
		events: {
			"update:imageURL": (val: string) => blockController.setAttribute("src", val),
			"update:imageFit": (val: StyleValue) => blockController.setStyle("objectFit", val),
		},
		searchKeyWords: "Image, URL, Src, Fit, ObjectFit, Object Fit, Fill, Contain, Cover",
	},
	{
		component: Button,
		getProps: () => {
			return {
				label: "Convert to WebP",
				class: "text-base self-end",
			};
		},
		innerText: "Convert to WebP",
		searchKeyWords: "Convert, webp, Convert to webp, image, src, url",
		events: {
			click: () => {
				const block = blockController.getSelectedBlocks()[0];
				const convertToWebP = createResource({
					url: "/api/method/builder.api.convert_to_webp",
					params: {
						image_url: block.getAttribute("src"),
					},
				});
				toast.promise(
					convertToWebP.fetch().then((res: string) => {
						block.setAttribute("src", res);
					}),
					{
						loading: "Converting...",
						success: () => "Image converted to WebP",
						error: () => "Failed to convert image to WebP",
					},
				);
			},
		},
		condition: () => {
			if (!blockController.isImage()) {
				return false;
			}
			if (
				[".jpg", ".jpeg", ".png"].some((ext) =>
					((blockController.getAttribute("src") as string) || ("" as string)).toLowerCase().endsWith(ext),
				)
			) {
				return true;
			}
		},
	},
	{
		component: StyleControl,
		getProps: () => {
			return {
				controlType: "attribute",
				styleProperty: "alt",
				label: "Alt Text",
				allowDynamicValue: true,
				enableStates: false,
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
