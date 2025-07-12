import PropertyControl from "@/components/Controls/PropertyControl.vue";
import ImageUploadInput from "@/components/ImageUploadInput.vue";
import blockController from "@/utils/blockController";
import { Button, createResource } from "frappe-ui";
import { computed } from "vue";
import { toast } from "vue-sonner";

const imageOptionsSectionProperties = [
	{
		component: PropertyControl,
		getProps: () => {
			return {
				component: ImageUploadInput,
				controlType: "attribute",
				styleProperty: "src",
				label: "Image URL",
				allowDynamicValue: true,
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
				class: "text-base self-end",
			};
		},
		innerText: computed(() => {
			const block = blockController.getSelectedBlocks()[0];
			const imageUrl = (block?.getAttribute("src") as string) || "";
			const isExternal = imageUrl.startsWith("http://") || imageUrl.startsWith("https://");
			const isConvertibleToWebP = [".jpg", ".jpeg", ".png"].some((ext) =>
				imageUrl.toLowerCase().endsWith(ext),
			);
			if (isExternal) {
				return "Serve Locally";
			} else if (isConvertibleToWebP) {
				return "Convert to WebP";
			}
		}),
		searchKeyWords:
			"Image, Local, Copy, Server, Download, Host, Store, Convert, webp, Convert to webp, image, src, url",
		events: {
			click: () => {
				const block = blockController.getSelectedBlocks()[0];
				const convertToWebP = createResource({
					url: "/api/method/builder.api.convert_to_webp",
					params: {
						image_url: block.getAttribute("src"),
					},
				});

				const imageUrl = block.getAttribute("src") as string;
				const isExternal = imageUrl.startsWith("http://") || imageUrl.startsWith("https://");

				return toast.promise(
					convertToWebP.fetch().then((res: string) => {
						block.setAttribute("src", res);
					}),
					{
						loading: isExternal ? "Pulling..." : "Converting...",
						success: () => (isExternal ? "Image pulled to local" : "Image converted to WebP"),
						error: () => (isExternal ? "Failed to pull image to local" : "Failed to convert image to WebP"),
					},
				);
			},
		},
		condition: () => {
			if (!blockController.isImage()) {
				return false;
			}
			const imageUrl = blockController.getAttribute("src") as string;
			if (!imageUrl) {
				return false;
			}

			const isExternal = imageUrl.startsWith("http://") || imageUrl.startsWith("https://");
			const isConvertibleToWebP = [".jpg", ".jpeg", ".png"].some((ext) =>
				imageUrl.toLowerCase().endsWith(ext),
			);

			return isExternal || isConvertibleToWebP;
		},
	},
	{
		component: PropertyControl,
		getProps: () => {
			return {
				controlType: "attribute",
				styleProperty: "alt",
				label: "Alt Text",
				allowDynamicValue: true,
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
