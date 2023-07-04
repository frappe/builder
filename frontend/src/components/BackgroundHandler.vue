<template>
	<Popover transition="default" placement="left" class="!block w-full" popoverClass="!min-w-fit !mr-[30px]">
		<template #target="{ togglePopover, isOpen }">
			<div class="flex items-center justify-between">
				<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
					<slot>BG Image</slot>
				</span>
				<div class="relative w-[150px]">
					<div>
						<div
							class="absolute left-2 top-[6px] z-10 h-4 w-4 rounded shadow-sm"
							@click="togglePopover"
							:style="{
								backgroundImage: backgroundURL ? `url(${backgroundURL})` : '',
								backgroundPosition: `center`,
								backgroundSize: `contain`,
								backgroundRepeat: `no-repeat`,
							}"></div>
						<Input
							type="text"
							class="rounded-md text-sm text-gray-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:focus:bg-zinc-700"
							placeholder="Select Background"
							inputClass="pl-8"
							:value="backgroundURL?.replace(/^'|'$/g, '')"
							@change=""></Input>
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
								class="absolute bottom-0 left-0 right-0 top-0 hidden place-items-center bg-gray-500 bg-opacity-20 group-hover:grid">
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
					class="mt-4"
					:modelValue="backgroundSize"
					type="select"
					:options="['contain', 'cover']"
					@update:modelValue="setBGSize">
					Size
				</InlineInput>
			</div>
		</template>
	</Popover>
</template>
<script lang="ts" setup>
import { Popover, FileUploader } from "frappe-ui";
import Block from "@/utils/block";
import InlineInput from "./InlineInput.vue";
import { PropType, computed } from "vue";

const props = defineProps({
	block: {
		type: Object as PropType<Block>,
		required: true,
	},
});

const backgroundURL = computed(() => {
	const background = props.block?.getStyle("background") as string;
	if (background) {
		const { bgImageURL } = parseBackground(background);
		return bgImageURL;
	}
	return null;
});

const backgroundSize = computed(() => {
	const background = props.block?.getStyle("background") as string;
	if (background) {
		const { bgSize } = parseBackground(background);
		console.log(bgSize);
		return bgSize;
	}
});

const setBG = (file: { file_url: string }) => {
	const url = window.location.origin + file.file_url;
	props.block?.setStyle("background", `url('${url}') center / ${backgroundSize.value || "cover"} no-repeat`);
};

const setBGSize = (value: string) => {
	props.block?.setStyle("background", `url(${backgroundURL.value}) center / ${value} no-repeat`);
};

const parseBackground = (background: string) => {
	const bgImageURL = background.match(/url\((.*?)\)/)?.[1];
	const bgPosition = background.match(/center|top|bottom|left|right/g)?.[0];
	const bgSize = background.match(/contain|cover/g)?.[0];
	const bgRepeat = background.match(/repeat|no-repeat/g)?.[0];
	return { bgImageURL, bgPosition, bgSize, bgRepeat };
};
</script>
