<template>
	<Popover transition="default" placement="left" class="!block w-full" popoverClass="!min-w-fit !mr-[30px]">
		<template #target="{ togglePopover, isOpen }">
			<div class="flex items-center justify-between">
				<InputLabel>BG Image</InputLabel>
				<div class="relative w-full">
					<div>
						<BuilderInput
							class="[&>div>input]:pl-8"
							type="text"
							placeholder="Set Background"
							@focus="togglePopover"
							@update:modelValue="updateBG"
							:modelValue="backgroundURL?.replace(/^'|'$/g, '')" />
						<div
							class="absolute left-2 top-[6px] z-10 h-4 w-4 rounded shadow-sm"
							@click="togglePopover"
							:class="{
								'bg-surface-gray-4': !backgroundURL,
							}"
							:style="{
								backgroundImage: backgroundURL ? `url(${backgroundURL})` : '',
								backgroundPosition: `center`,
								backgroundSize: `contain`,
								backgroundRepeat: `no-repeat`,
							}"></div>
					</div>
				</div>
			</div>
		</template>
		<template #body>
			<div class="rounded-lg bg-surface-white p-3 shadow-lg">
				<div
					class="image-preview group relative h-24 w-48 cursor-pointer overflow-hidden rounded bg-surface-gray-3"
					:style="{
						backgroundImage: backgroundURL ? `url(${backgroundURL})` : '',
						backgroundPosition: `center`,
						backgroundSize: backgroundSize || `contain`,
						backgroundRepeat: `no-repeat`,
					}">
					<FileUploader
						@success="setBG"
						:uploadArgs="{
							private: false,
							folder: 'Home/Builder Uploads',
							optimize: true,
							upload_endpoint: '/api/method/builder.api.upload_builder_asset',
						}">
						<template v-slot="{ openFileSelector }">
							<div
								class="absolute bottom-0 left-0 right-0 top-0 hidden place-items-center bg-gray-500 bg-opacity-20"
								:class="{
									'!grid': !backgroundURL,
									'group-hover:grid': backgroundURL,
								}">
								<BuilderButton @click="openFileSelector">Upload</BuilderButton>
							</div>
						</template>
					</FileUploader>
				</div>
				<InlineInput
					label="Size"
					class="mt-4"
					:modelValue="backgroundSize"
					type="select"
					:options="['contain', 'cover']"
					@update:modelValue="setBGSize" />
			</div>
		</template>
	</Popover>
</template>
<script lang="ts" setup>
import InlineInput from "@/components/Controls/InlineInput.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import blockController from "@/utils/blockController";
import { FileUploader, Popover } from "frappe-ui";
import { computed } from "vue";

const backgroundURL = computed(() => {
	const background = blockController?.getStyle("background") as string;
	if (background) {
		const { bgImageURL } = parseBackground(background);
		return bgImageURL;
	}
	return null;
});

const backgroundSize = computed(() => {
	const background = blockController?.getStyle("background") as string;
	if (background) {
		const { bgSize } = parseBackground(background);
		return bgSize;
	}
});

const setBG = (file: { file_url: string }) => {
	const url = window.location.origin + file.file_url;
	blockController?.setStyle(
		"background",
		`url('${url}') center / ${backgroundSize.value || "cover"} no-repeat`,
	);
};

const setBGSize = (value: string) => {
	blockController?.setStyle("background", `url(${backgroundURL.value}) center / ${value} no-repeat`);
};

const parseBackground = (background: string) => {
	const bgImageURL = background.match(/url\((.*?)\)/)?.[1];
	const bgPosition = background.match(/center|top|bottom|left|right/g)?.[0];
	const bgSize = background.match(/contain|cover/g)?.[0];
	const bgRepeat = background.match(/repeat|no-repeat/g)?.[0];
	return { bgImageURL, bgPosition, bgSize, bgRepeat };
};

const updateBG = (value: string) => {
	value = value ? `url('${value}') center / ${backgroundSize.value || "cover"} no-repeat` : "";
	blockController?.setStyle("background", value);
};
</script>
