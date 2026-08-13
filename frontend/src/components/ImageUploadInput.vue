<template>
	<FileUploader
		ref="fileUploaderRef"
		@success="(file: FileDoc) => setImageURL(file.file_url)"
		fileTypes="image/*"
		:private="false"
		folder="Home/Builder Uploads"
		uploadEndpoint="/api/method/builder.api.upload_builder_asset">
		<template #default="{ openFileSelector }">
			<Popover side="left" align="center" :offset="popoverOffset" bare>
				<template #trigger="{ toggle }">
					<div class="flex items-center justify-between">
						<InputLabel v-if="label && labelPosition === 'left'">{{ label }}</InputLabel>
						<!-- .stop keeps input clicks from reaching the popover trigger's own toggle -->
						<div class="relative w-full [&>div>div>div>div]:pe-0" @click.stop>
							<BuilderInput
								:class="{
									'[&>input]:pl-8': labelPosition === 'left',
								}"
								type="text"
								:label="labelPosition === 'top' ? label : null"
								:placeholder="placeholder"
								:description="description"
								:hideClearButton="labelPosition === 'top'"
								@update:modelValue="setImageURL"
								:modelValue="currentImageURL">
								<template v-if="labelPosition === 'top'" #suffix>
									<ImageUploader
										@upload="setImageURL"
										@remove="setImageURL('')"
										:image_url="currentImageURL"
										:file_types="['image/*']" />
								</template>
							</BuilderInput>
							<img
								v-if="labelPosition === 'left'"
								:src="currentImageURL || '/assets/builder/images/fallback.png'"
								alt=""
								@click="toggle"
								class="rounded absolute bottom-[6px] left-2 h-4 w-4 border border-outline-gray-3 shadow-sm"
								:style="{
									'object-fit': imageFit || 'contain',
								}" />
						</div>
					</div>
				</template>
				<template #default>
					<div class="rounded-lg bg-surface-base p-3 shadow-lg">
						<div class="rounded group relative flex items-center justify-center overflow-hidden">
							<img
								:src="currentImageURL || '/assets/builder/images/fallback.png'"
								alt=""
								class="image-preview relative h-24 w-48 cursor-pointer bg-surface-gray-2"
								:style="{
									'object-fit': imageFit || 'contain',
								}" />
							<div
								class="absolute bottom-0 left-0 right-0 top-0 hidden place-items-center bg-surface-gray-4 opacity-90"
								:class="{
									'!grid': !currentImageURL,
									'group-hover:grid': currentImageURL,
								}">
								<Button variant="subtle" @click="openFileSelector">Upload</Button>
							</div>
						</div>
						<InlineInput
							label="Image Fit"
							class="mt-4"
							:modelValue="imageFit"
							type="select"
							:options="[
								{ label: 'Fit Inside', value: 'contain' },
								{ label: 'Fill & Crop', value: 'cover' },
								{ label: 'Stretch', value: 'fill' },
								{ label: 'Original Size', value: 'none' },
							]"
							@update:modelValue="setImageFit" />
					</div>
				</template>
			</Popover>
		</template>
	</FileUploader>
</template>
<script lang="ts" setup>
import ImageUploader from "@/components/Controls/ImageUploader.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import useBuilderStore from "@/stores/builderStore";
import { FileUploader, Popover } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = withDefaults(
	defineProps<{
		imageURL?: string;
		modelValue?: string;
		label?: string;
		labelPosition?: "top" | "left";
		placeholder?: string;
		imageFit?: "contain" | "cover" | "fill" | "none";
		description?: string;
		popoverOffset?: number;
	}>(),
	{
		labelPosition: "left",
		placeholder: "Set Image",
		imageFit: "contain",
		popoverOffset: 10,
	},
);

const builderStore = useBuilderStore();
// FileUploader no longer exposes its input; reach the hidden file input through the root element
const fileUploaderRef = ref<{ $el: HTMLElement } | null>(null);

watch(
	() => builderStore.openImageUpload,
	(val) => {
		if (val && props.labelPosition === "left") {
			builderStore.openImageUpload = false;
			fileUploaderRef.value?.$el.querySelector<HTMLInputElement>("input[type=file]")?.click();
		}
	},
);

const currentImageURL = computed(() => props.modelValue || "");
const emit = defineEmits(["update:imageFit", "update:modelValue"]);

const setImageURL = (fileURL: string) => {
	emit("update:modelValue", fileURL);
};

const setImageFit = (fit: string) => {
	emit("update:imageFit", fit);
};
</script>
