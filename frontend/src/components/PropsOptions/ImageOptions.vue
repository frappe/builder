<template>
	<div class="flex items-center justify-between">
		<ImageUploadInput
			label="Default Value"
			label-position="left"
			placeholder="Enter image URL or upload one"
			class="w-full"
			:imageURL="defaultImageURL"
			:image-fit="defaultImageFit"
			@update:image-fit="handleDefaultFitChange"
			@update:imageURL="handleDefaultImgURLChange"></ImageUploadInput>
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import ImageUploadInput from "../ImageUploadInput.vue";

const props = defineProps<{
	options: Record<string, any>;
}>();

const emit = defineEmits<{
	(update: "update:options", value: Record<string, any>): void;
}>();

const defaultImageURL = ref(props.options?.defaultValue || props.options?.defaultImageURL);
const defaultImageFit = ref(props.options?.defaultImageFit);
const handleDefaultImgURLChange = (value: string) => {
	defaultImageURL.value = value;
	handleDefaultValueChange({ imageURL: value });
};
const handleDefaultFitChange = (value: string) => {
	defaultImageFit.value = value;
	handleDefaultValueChange({ imageFit: value });
};

const handleDefaultValueChange = ({ imageURL, imageFit }: { imageURL?: string; imageFit?: string }) => {
	emit("update:options", {
		defaultValue: imageURL || defaultImageURL.value,
		defaultImageURL: imageURL || defaultImageURL.value,
		defaultImageFit: imageFit || defaultImageFit.value,
	});
};

const reset = (toProps: boolean = false) => {
	defaultImageURL.value = toProps ? props.options?.defaultValue || props.options?.defaultImageURL : "";
	defaultImageFit.value = toProps ? props.options?.defaultImageFit : "";
};

defineExpose({ reset });
</script>
