<template>
	<Popover placement="left" class="!block w-full" popoverClass="!min-w-fit !mr-[30px]">
		<template #target="{ togglePopover, isOpen }">
			<div class="flex items-center justify-between">
				<InputLabel v-if="label && labelPosition === 'left'">{{ label }}</InputLabel>
				<div class="relative w-full">
					<BuilderInput
						:class="{
							'[&>div>input]:pl-8': labelPosition === 'left',
						}"
						type="text"
						:label="labelPosition === 'top' ? label : null"
						:placeholder="placeholder"
						:description="description"
						:hideClearButton="labelPosition === 'top'"
						@update:modelValue="setImageURL"
						:modelValue="imageURL" />
					<img
						v-if="labelPosition === 'left'"
						:src="imageURL || '/assets/builder/images/fallback.png'"
						alt=""
						@click="togglePopover"
						class="absolute bottom-[6px] left-2 z-10 h-4 w-4 rounded border border-outline-gray-3 shadow-sm"
						:style="{
							'object-fit': imageFit || 'contain',
						}" />
					<ImageUploader
						v-if="labelPosition === 'top'"
						@upload="setImageURL"
						@remove="setImageURL('')"
						:image_url="imageURL"
						class="absolute right-0 top-5 rounded-r-md bg-surface-gray-2 pl-2 dark:bg-transparent"
						:file_types="['image/*']" />
				</div>
			</div>
		</template>
		<template #body>
			<div class="rounded-lg bg-surface-white p-3 shadow-lg">
				<FileUploader
					@success="(file: FileDoc) => setImageURL(file.file_url)"
					:uploadArgs="{
						private: false,
						folder: 'Home/Builder Uploads',
						optimize: true,
						upload_endpoint: '/api/method/builder.api.upload_builder_asset',
					}">
					<template v-slot="{ openFileSelector }">
						<div class="group relative overflow-hidden rounded">
							<img
								:src="imageURL || '/assets/builder/images/fallback.png'"
								alt=""
								class="image-preview relative h-24 w-48 cursor-pointer bg-surface-gray-2"
								:style="{
									'object-fit': imageFit || 'contain',
								}" />
							<div
								class="absolute bottom-0 left-0 right-0 top-0 hidden place-items-center bg-gray-500 bg-opacity-20"
								:class="{
									'!grid': !imageURL,
									'group-hover:grid': imageURL,
								}">
								<BuilderButton variant="solid" @click="openFileSelector">Upload</BuilderButton>
							</div>
						</div>
					</template>
				</FileUploader>
				<InlineInput
					label="Image Fit"
					class="mt-4"
					:modelValue="imageFit"
					type="select"
					:options="['contain', 'cover', 'fill', 'none']"
					@update:modelValue="setImageFit" />
			</div>
		</template>
	</Popover>
</template>
<script lang="ts" setup>
import ImageUploader from "@/components/Controls/ImageUploader.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import { FileUploader, Popover } from "frappe-ui";

withDefaults(
	defineProps<{
		imageURL?: string;
		label?: string;
		labelPosition?: "top" | "left";
		placeholder?: string;
		imageFit?: "contain" | "cover" | "fill" | "none";
		description?: string;
	}>(),
	{
		labelPosition: "left",
		placeholder: "Set Image",
		imageFit: "contain",
	},
);

const emit = defineEmits(["update:imageURL", "update:imageFit"]);

const setImageURL = (fileURL: string) => {
	emit("update:imageURL", fileURL);
};

const setImageFit = (fit: string) => {
	emit("update:imageFit", fit);
};
</script>
