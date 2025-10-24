import { createResource } from "frappe-ui";
import { toast } from "vue-sonner";

export interface ImageOptimizationOptions {
	imageUrl: string;
	onSuccess: (newUrl: string) => void;
}

export const isExternalImage = (imageUrl: string): boolean => {
	return imageUrl.startsWith("http://") || imageUrl.startsWith("https://");
};

export const isConvertibleToWebP = (imageUrl: string): boolean => {
	return [".jpg", ".jpeg", ".png"].some((ext) => imageUrl.toLowerCase().endsWith(ext));
};

export const shouldShowOptimizeButton = (imageUrl: string | null): boolean => {
	if (!imageUrl) {
		return false;
	}
	return isExternalImage(imageUrl) || isConvertibleToWebP(imageUrl);
};

export const getOptimizeButtonText = (imageUrl: string | null): string => {
	if (!imageUrl) {
		return "";
	}

	if (isExternalImage(imageUrl)) {
		return "Serve Locally";
	} else if (isConvertibleToWebP(imageUrl)) {
		return "Convert to WebP";
	}
	return "";
};

export const optimizeImage = ({ imageUrl, onSuccess }: ImageOptimizationOptions) => {
	if (!imageUrl) {
		return;
	}

	const convertToWebP = createResource({
		url: "/api/method/builder.api.convert_to_webp",
		params: {
			image_url: imageUrl,
		},
	});

	const isExternal = isExternalImage(imageUrl);

	return toast.promise(
		convertToWebP.fetch().then((res: string) => {
			onSuccess(res);
		}),
		{
			loading: isExternal ? "Pulling..." : "Converting...",
			success: () => (isExternal ? "Image pulled to local" : "Image converted to WebP"),
			error: () => (isExternal ? "Failed to pull image to local" : "Failed to convert image to WebP"),
		},
	);
};
