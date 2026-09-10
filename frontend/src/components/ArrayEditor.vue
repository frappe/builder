<template>
	<div ref="arrayEditor" class="flex flex-col gap-2" @paste="pasteArray">
		<div v-for="(item, index) in arr" :key="index" class="flex gap-2">
			<ImageUploadInput
				v-if="itemType === 'image'"
				class="w-full"
				:placeholder="__('Enter image URL or upload one')"
				:modelValue="itemURL(item)"
				:imageFit="(itemFit(item) || 'cover') as 'contain' | 'cover' | 'fill'"
				:objectPosition="itemPosition(item)"
				:targetRatio="targetRatio"
				@update:modelValue="(val: string) => updateImageItem(index, { url: val })"
				@update:imageFit="(val: string) => updateImageItem(index, { fit: val })"
				@update:objectPosition="(val: string) => updateImageItem(index, { position: val })" />
			<BuilderInput
				v-else
				:placeholder="__('Enter value')"
				:modelValue="itemURL(item)"
				@input="(val: string) => updateItem(index, val)" />
			<Button
				class="flex-shrink-0 text-xs"
				variant="subtle"
				icon="lucide-x"
				@click="deleteItem(index)"></Button>
		</div>
		<Button
			v-if="itemType === 'image'"
			variant="outline"
			class="w-full"
			:loading="isBulkUploading"
			:label="isBulkUploading ? __('Uploading...') : __('Upload')"
			iconLeft="upload"
			@click="triggerBulkUpload" />
		<Button
			v-else
			variant="outline"
			class="w-full"
			:label="__('Add')"
			iconLeft="plus"
			@click="addItem" />
		<input
			v-if="itemType === 'image'"
			ref="bulkFileInput"
			type="file"
			multiple
			accept="image/*"
			class="hidden"
			@change="handleBulkUpload" />
		<p class="rounded-sm bg-surface-gray-1 p-2 text-xs text-ink-gray-7" v-show="description">
			<span v-html="description"></span>
		</p>
	</div>
</template>
<script setup lang="ts">
import { nextTick, ref } from "vue";
import ImageUploadInput from "./ImageUploadInput.vue";
import { uploadBuilderAsset } from "@/utils/helpers";
import { toast } from "frappe-ui";
import { __ } from "@/translation";

const props = defineProps<{
	arr: Array<ArrayPropItem>;
	description?: string;
	itemType?: "string" | "image";
	targetRatio?: number;
}>();

const emit = defineEmits({
	"update:arr": (arr: Array<ArrayPropItem>) => true,
});

const itemURL = (item: ArrayPropItem) => (typeof item === "string" ? item : item?.url || "");
const itemFit = (item: ArrayPropItem) => (typeof item === "string" ? "" : item?.fit || "");
const itemPosition = (item: ArrayPropItem) => (typeof item === "string" ? "" : item?.position || "");

const addItem = async () => {
	const newArr = [...props.arr, ""];
	emit("update:arr", newArr);
	await nextTick();
	const inputs = arrayEditor.value?.querySelectorAll("input:not([type='file'])");
	if (inputs) {
		const lastInput = inputs[inputs.length - 1];
		lastInput.focus();
	}
};

const updateItem = (index: number, value: string) => {
	const newArr = [...props.arr];
	newArr[index] = value;
	emit("update:arr", newArr);
};

const updateImageItem = (index: number, patch: { url?: string; fit?: string; position?: string }) => {
	const newArr = [...props.arr];
	const current = newArr[index];
	const url = patch.url ?? itemURL(current);
	const fit = patch.fit ?? itemFit(current);
	const position = patch.position ?? itemPosition(current);
	if (fit || position) {
		const image: ImageArrayItem = { url };
		if (fit) image.fit = fit;
		if (position) image.position = position;
		newArr[index] = image;
	} else {
		newArr[index] = url;
	}
	emit("update:arr", newArr);
};

const deleteItem = (index: number) => {
	const newArr = [...props.arr];
	newArr.splice(index, 1);
	emit("update:arr", newArr);
};

const arrayEditor = ref<HTMLElement | null>(null);
const bulkFileInput = ref<HTMLInputElement | null>(null);
const isBulkUploading = ref(false);

const triggerBulkUpload = () => {
	bulkFileInput.value?.click();
};

const uploadFiles = async (files: FileList | File[]) => {
	const uploadPromises = Array.from(files).map((file) => uploadBuilderAsset(file, true));
	const results = await Promise.allSettled(uploadPromises);

	const uploadedUrls: string[] = [];
	let hasFailed = false;

	for (const result of results) {
		if (result.status === "fulfilled" && result.value?.fileURL) {
			const url = result.value.fileURL;
			if (typeof url === "string" && url.trim() !== "") {
				uploadedUrls.push(url);
			} else {
				hasFailed = true;
			}
		} else {
			hasFailed = true;
		}
	}

	return { uploadedUrls, hasFailed };
};

const notifyUploadResults = (uploadedCount: number, hasFailed: boolean) => {
	if (uploadedCount > 0) {
		toast.success(__("Uploaded {0} image(s)", [uploadedCount]));
	}
	if (hasFailed) {
		toast.error(__("Failed to upload images"));
	}
};

const appendUploadedUrls = (urls: string[]) => {
	const currentArr = props.arr.filter((item) => itemURL(item).trim() !== "");
	const newArr = [...currentArr, ...urls];
	emit("update:arr", newArr);
};

const handleBulkUpload = async (e: Event) => {
	const target = e.target as HTMLInputElement;
	const files = target.files;
	if (!files || files.length === 0) return;

	isBulkUploading.value = true;
	try {
		const { uploadedUrls, hasFailed } = await uploadFiles(files);

		if (uploadedUrls.length > 0) {
			appendUploadedUrls(uploadedUrls);
		}

		notifyUploadResults(uploadedUrls.length, hasFailed);
	} catch (error) {
		toast.error(__("Failed to upload images"));
	} finally {
		isBulkUploading.value = false;
		if (target) {
			target.value = "";
		}
	}
};

const pasteArray = (e: ClipboardEvent) => {
	const passedArr = props.arr.filter((item) => itemURL(item).trim() !== "");
	const text = e.clipboardData?.getData("text/plain");
	if (text) {
		e.preventDefault();
		try {
			// Try to parse as JSON array first
			const parsed = JSON.parse(text);
			if (Array.isArray(parsed)) {
				const stringArray = parsed.map((item) => String(item));
				emit("update:arr", [...passedArr, ...stringArray]);
				return;
			}
		} catch (e) {
			// If JSON parsing fails, try other formats
		}

		// Try to parse as comma-separated values
		if (text.includes(",")) {
			const items = text
				.split(",")
				.map((item) => item.trim())
				.filter((item) => item);
			emit("update:arr", [...passedArr, ...items]);
			return;
		}

		// Try to parse as line-separated values
		if (text.includes("\n")) {
			const items = text
				.split("\n")
				.map((item) => item.trim())
				.filter((item) => item);
			emit("update:arr", [...passedArr, ...items]);
			return;
		}

		// Single item
		emit("update:arr", [...passedArr, text.trim()]);
	}
};
</script>
