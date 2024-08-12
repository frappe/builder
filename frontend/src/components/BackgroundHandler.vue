<template>
	<Popover transition="default" placement="left" class="!block w-full" popoverClass="!min-w-fit !mr-[30px]">
		<template #target="{ togglePopover, isOpen }">
			<div class="flex items-center justify-between">
				<InputLabel>BG Image</InputLabel>
				<div class="relative w-full">
					<div>
						<Input
							class="[&>div>input]:pl-8"
							type="text"
							placeholder="Set Background"
							@update:modelValue="updateBG"
							:value="backgroundURL?.replace(/^'|'$/g, '')" />
						<div
							class="absolute left-2 top-[6px] z-10 h-4 w-4 rounded shadow-sm"
							@click="togglePopover"
							:class="{
								'bg-gray-400 dark:bg-zinc-600': !backgroundURL,
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
			<div class="rounded-lg bg-white p-3 shadow-lg dark:bg-zinc-900">
				<div
					class="image-preview group relative h-24 w-48 cursor-pointer overflow-hidden rounded bg-gray-200 dark:bg-zinc-700"
					:style="{
						backgroundImage: backgroundURL ? `url(${backgroundURL})` : '',
						backgroundPosition: `center`,
						backgroundSize: backgroundSize || `contain`,
						backgroundRepeat: `no-repeat`,
					}">
					<FileUploader @success="setBG">
						<template v-slot="{ openFileSelector }">
							<div
								class="absolute bottom-0 left-0 right-0 top-0 hidden place-items-center bg-gray-500 bg-opacity-20"
								:class="{
									'!grid': !backgroundURL,
									'group-hover:grid': backgroundURL,
								}">
								<div
									class="rounded bg-gray-200 p-2 text-xs text-gray-900 dark:bg-zinc-700 dark:text-zinc-200"
									@click="openFileSelector">
									Upload
								</div>
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
import blockController from "@/utils/blockController";
import { FileUploader, Popover } from "frappe-ui";
import { computed } from "vue";
import InlineInput from "./InlineInput.vue";
import Input from "./Input.vue";
import InputLabel from "./InputLabel.vue";

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
	blockController?.setStyle(
		"background",
		`url('${value}') center / ${backgroundSize.value || "cover"} no-repeat`,
	);
};
</script>
