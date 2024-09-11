<template>
	<Popover transition="default" placement="left" class="!block w-full" popoverClass="!min-w-fit !mr-[30px]">
		<template #target="{ togglePopover, isOpen }">
			<div class="flex items-center justify-between">
				<InputLabel>Image URL</InputLabel>
				<div class="relative w-full">
					<div>
						<Input
							class="[&>div>input]:pl-8"
							type="text"
							placeholder="Set Image URL"
							@update:modelValue="setImageURL"
							:modelValue="imageURL" />
						<img
							:src="imageURL || '/assets/builder/images/fallback.png'"
							alt=""
							@click="togglePopover"
							class="absolute left-2 top-[6px] z-10 h-4 w-4 rounded shadow-sm"
							:style="{
								'object-fit': imageFit || 'contain',
							}" />
					</div>
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
								class="image-preview relative h-24 w-48 cursor-pointer bg-gray-200 dark:bg-zinc-700"
								:style="{
									'object-fit': imageFit || 'contain',
								}" />
							<div
								class="absolute bottom-0 left-0 right-0 top-0 hidden place-items-center bg-gray-500 bg-opacity-20"
								:class="{
									'!grid': !imageURL,
									'group-hover:grid': imageURL,
								}">
								<Button
									class="rounded bg-gray-200 p-2 text-xs text-gray-900 dark:bg-zinc-700 dark:text-zinc-200"
									variant="solid"
									@click="openFileSelector">
									Upload
								</Button>
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
import { FileUploader, Popover } from "frappe-ui";
import { PropType } from "vue";
import InlineInput from "./InlineInput.vue";
import Input from "./Input.vue";
import InputLabel from "./InputLabel.vue";

defineProps({
	imageURL: String,
	imageFit: {
		type: String as PropType<"contain" | "cover" | "fill" | "none">,
		default: "contain",
	},
});

const emit = defineEmits(["update:imageURL", "update:imageFit"]);

const setImageURL = (fileURL: string) => {
	emit("update:imageURL", fileURL);
};

const setImageFit = (fit: string) => {
	emit("update:imageFit", fit);
};
</script>
