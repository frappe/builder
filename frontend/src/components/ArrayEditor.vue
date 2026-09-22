<template>
	<div ref="arrayEditor" class="flex flex-col gap-2" @paste="pasteArray">
    <draggable
      v-if="arr.length"
      :modelValue="indexedItems"
      item-key="index"
      handle=".drag-handle"
      class="-m-1 flex min-h-0 flex-col gap-2 overflow-y-auto p-1"
      :class="listClass"
      @update:modelValue="reorderItems">
			<template #item="{ element: { item, index } }">
				<div class="flex items-center gap-2">
					<span
						class="drag-handle lucide-grip-vertical -ml-1 size-3.5 flex-shrink-0 cursor-grab text-ink-gray-5 hover:text-ink-gray-8" />
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
			</template>
		</draggable>
		<Button variant="outline" class="w-full shrink-0" :label="__('Add')" iconLeft="plus" @click="addItem" />
		<p class="shrink-0 rounded-1 bg-surface-gray-1 p-2 text-xs text-ink-gray-7" v-show="description">
			<span v-html="description"></span>
		</p>
	</div>
</template>
<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import draggable from "vuedraggable";
import ImageUploadInput from "./ImageUploadInput.vue";
import { __ } from "@/translation";

const props = defineProps<{
	arr: Array<ArrayPropItem>;
	description?: string;
	itemType?: "string" | "image";
	targetRatio?: number;
	listClass?: string;
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

// keep any other data saved on the item, such as a slide's own text
const updateImageItem = (index: number, patch: Partial<ImageArrayItem>) => {
	const newArr = [...props.arr];
	const current = newArr[index];
	const image = { ...(typeof current === "string" ? { url: current } : current), ...patch } as ImageArrayItem;
	Object.keys(image).forEach((key) => key !== "url" && !image[key] && delete image[key]);
	newArr[index] = Object.keys(image).length > 1 ? image : image.url || "";
	emit("update:arr", newArr);
};

// items can be duplicate strings, so key draggable rows by their position
const indexedItems = computed(() => props.arr.map((item, index) => ({ item, index })));

const reorderItems = (items: Array<{ item: ArrayPropItem; index: number }>) => {
	emit("update:arr", items.map(({ item }) => item));
};

const deleteItem = (index: number) => {
	const newArr = [...props.arr];
	newArr.splice(index, 1);
	emit("update:arr", newArr);
};

const arrayEditor = ref<HTMLElement | null>(null);

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
