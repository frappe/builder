<template>
	<FileUploader
		ref="fileUploaderRef"
		@success="(file: FileDoc) => setImageURL(file.file_url)"
		fileTypes="image/*"
		:uploadArgs="{
			private: false,
			folder: 'Home/Builder Uploads',
			upload_endpoint: '/api/method/builder.api.upload_builder_asset',
		}">
		<template #default="{ openFileSelector }">
			<Popover placement="left" class="!block w-full" :offset="popoverOffset">
				<template #target="{ togglePopover }">
					<div class="flex items-center justify-between">
						<InputLabel v-if="label && labelPosition === 'left'">{{ label }}</InputLabel>
						<div class="relative w-full [&>div>div>div>div]:pe-0">
							<BuilderInput
								type="text"
								:label="labelPosition === 'top' ? label : null"
								:placeholder="placeholder"
								:description="description"
								:hideClearButton="labelPosition === 'top'"
								@update:modelValue="setImageURL"
								:modelValue="currentImageURL">
								<template v-if="labelPosition === 'left'" #prefix>
									<img
										:src="currentImageURL || '/assets/builder/images/fallback.png'"
										alt=""
										@click="togglePopover"
										class="h-4 w-4 cursor-pointer rounded border border-outline-gray-3 shadow-sm"
										:style="{
											'object-fit': imageFit || 'contain',
										}" />
								</template>
								<template v-if="labelPosition === 'top'" #suffix>
									<ImageUploader
										@upload="setImageURL"
										@remove="setImageURL('')"
										:image_url="currentImageURL"
										:file_types="['image/*']" />
								</template>
							</BuilderInput>
						</div>
					</div>
				</template>
				<template #body>
					<div class="w-64 rounded-lg bg-surface-base p-3 shadow-lg">
						<div v-if="objectPosition !== undefined" class="mb-3 flex items-center">
							<span class="text-sm font-semibold text-ink-gray-9">{{ __("Image") }}</span>
						</div>
						<div v-if="objectPosition !== undefined" class="mb-3">
							<TabButtons
								:class="STRETCH_TABS"
								:options="fitOptions"
								:modelValue="imageFit || 'contain'"
								@update:modelValue="setImageFit" />
						</div>
						<!-- one surface for every fit: interactive (dot, frame, zoom) when the
						     cover crop makes a focal point meaningful, plain preview otherwise -->
						<ImageFocusInput
							v-if="currentImageURL && objectPosition !== undefined"
							:imageSrc="currentImageURL"
							:modelValue="objectPosition"
							:viewBox="objectViewBox"
							:targetRatio="targetRatio"
							:fit="imageFit"
							:disabled="imageFit !== 'cover'"
							@update:modelValue="(val) => emit('update:objectPosition', val)"
							@update:viewBox="(val) => emit('update:objectViewBox', val)" />
						<div
							v-else-if="objectPosition !== undefined"
							class="flex h-24 items-center justify-center rounded border border-dashed border-outline-gray-2 bg-surface-gray-1 text-p-xs text-ink-gray-4">
							{{ __("No image") }}
						</div>
						<div v-else class="group relative flex items-center justify-center overflow-hidden rounded">
							<img
								:src="currentImageURL || '/assets/builder/images/fallback.png'"
								alt=""
								class="image-preview relative h-24 w-full cursor-pointer bg-surface-gray-2"
								:style="{
									'object-fit': imageFit || 'contain',
								}" />
							<div
								class="absolute bottom-0 left-0 right-0 top-0 hidden place-items-center bg-surface-gray-4 opacity-90"
								:class="{
									'!grid': !currentImageURL,
									'group-hover:grid': currentImageURL,
								}">
								<Button variant="subtle" @click="openFileSelector">{{ __("Upload") }}</Button>
							</div>
						</div>
						<div v-if="objectPosition !== undefined" class="mt-3 flex items-center gap-1.5">
							<Button
								class="flex-1"
								variant="outline"
								iconLeft="upload"
								:label="currentImageURL ? __('Replace') : __('Upload')"
								@click="openFileSelector" />
							<Button
								variant="outline"
								icon="rotate-ccw"
								:title="__('Reset focal point')"
								:disabled="!objectPosition && !objectViewBox"
								@click="resetFocus" />
						</div>
						<InlineInput
							v-if="objectPosition === undefined"
							:label="__('Image Fit')"
							class="mt-4"
							:modelValue="imageFit"
							type="select"
							:options="[
								{ label: __('Fit Inside'), value: 'contain' },
								{ label: __('Fill & Crop'), value: 'cover' },
								{ label: __('Stretch'), value: 'fill' },
								{ label: __('Original Size'), value: 'none' },
							]"
							@update:modelValue="setImageFit" />
					</div>
				</template>
			</Popover>
		</template>
	</FileUploader>
</template>
<script lang="ts" setup>
import { __ } from "@/translation";
import ImageFocusInput from "@/components/Controls/ImageFocusInput.vue";
import ImageUploader from "@/components/Controls/ImageUploader.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import useBuilderStore from "@/stores/builderStore";
import { STRETCH_TABS } from "@/utils/tabButtons";
import { FileUploader, Popover, TabButtons } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = withDefaults(
	defineProps<{
		imageURL?: string;
		modelValue?: string;
		label?: string;
		labelPosition?: "top" | "left";
		placeholder?: string;
		imageFit?: "contain" | "cover" | "fill" | "none";
		// pass them (even empty) to get the focus-point picker / zoom crop for cover fits
		objectPosition?: string;
		objectViewBox?: string;
		targetRatio?: number;
		description?: string;
		popoverOffset?: number;
	}>(),
	{
		labelPosition: "left",
		placeholder: __("Set Image"),
		imageFit: "contain",
		popoverOffset: 10,
	},
);

const builderStore = useBuilderStore();
const fileUploaderRef = ref<{ inputRef: () => HTMLInputElement } | null>(null);

watch(
	() => builderStore.openImageUpload,
	(val) => {
		if (val && props.labelPosition === "left") {
			builderStore.openImageUpload = false;
			fileUploaderRef.value?.inputRef()?.click();
		}
	},
);

const currentImageURL = computed(() => props.modelValue || "");

const fitOptions = [
	{ label: __("Fill & crop"), value: "cover" },
	{ label: __("Fit"), value: "contain" },
	{ label: __("Stretch"), value: "fill" },
];

const emit = defineEmits([
	"update:imageFit",
	"update:modelValue",
	"update:objectPosition",
	"update:objectViewBox",
]);

const resetFocus = () => {
	emit("update:objectPosition", "");
	emit("update:objectViewBox", "");
};

const setImageURL = (fileURL: string) => {
	emit("update:modelValue", fileURL);
};

const setImageFit = (fit: string) => {
	emit("update:imageFit", fit);
};
</script>
