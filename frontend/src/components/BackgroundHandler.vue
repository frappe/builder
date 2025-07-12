<template>
	<Popover placement="left" class="!block w-full" popoverClass="!min-w-fit !mr-[30px]">
		<template #target="{ togglePopover }">
			<div class="flex w-full items-center justify-between">
				<PropertyControl
					styleProperty="backgroundImage"
					:component="Input"
					label="BG Image"
					:enableStates="false"
					:allowDynamicValue="true"
					placeholder="Set Background"
					@focus="togglePopover"
					:modelValue="backgroundImage"
					@update:modelValue="setBGImageURL">
					<template #prefix>
						<div
							class="absolute left-2 top-[6px] z-10 h-4 w-4 cursor-pointer rounded shadow-sm"
							@click="togglePopover"
							:class="{ 'bg-surface-gray-4': !Boolean(backgroundImage) }"
							:style="previewStyle" />
					</template>
				</PropertyControl>
			</div>
		</template>
		<template #body>
			<div class="rounded-lg bg-surface-white p-3 shadow-lg">
				<div
					class="image-preview group relative h-24 w-48 cursor-pointer overflow-hidden rounded bg-surface-gray-3"
					:style="previewStyle">
					<FileUploader
						@success="setBGImage"
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
									'!grid': !backgroundImage,
									'group-hover:grid': backgroundImage,
								}">
								<BuilderButton @click="openFileSelector">Upload</BuilderButton>
							</div>
						</template>
					</FileUploader>
				</div>
				<div class="mt-4 space-y-2">
					<InlineInput
						label="Size"
						:modelValue="backgroundSize"
						type="select"
						:options="sizeOptions"
						@update:modelValue="setBGSize" />
					<InlineInput
						label="Position"
						:modelValue="backgroundPosition"
						type="select"
						:options="positionOptions"
						@update:modelValue="setBGPosition" />
					<InlineInput
						label="Repeat"
						:modelValue="backgroundRepeat"
						type="select"
						:options="repeatOptions"
						@update:modelValue="setBGRepeat" />
				</div>
				<BuilderButton v-if="backgroundImage" class="mt-3 w-full" variant="subtle" @click="clearBGImage">
					Clear Image
				</BuilderButton>
			</div>
		</template>
	</Popover>
	<PropertyControl label="BG Color" styleProperty="backgroundColor" :component="ColorInput" />
</template>

<script lang="ts" setup>
import ColorInput from "@/components/Controls/ColorInput.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import Input from "@/components/Controls/Input.vue";
import PropertyControl from "@/components/Controls/PropertyControl.vue";
import blockController from "@/utils/blockController";
import { FileUploader, Popover } from "frappe-ui";
import { computed } from "vue";

const backgroundImage = computed(() => {
	const bgImage = blockController.getStyle("backgroundImage") as string;
	return bgImage ? bgImage.replace(/^url\(['"]?|['"]?\)$/g, "") : null;
});
const backgroundSize = computed(() => blockController.getStyle("backgroundSize") as string);
const backgroundPosition = computed(() => blockController.getStyle("backgroundPosition") as string);
const backgroundRepeat = computed(() => blockController.getStyle("backgroundRepeat") as string);

const previewStyle = computed(() => ({
	backgroundImage: (backgroundImage.value ? `url(${backgroundImage.value})` : "") as string,
	backgroundPosition: backgroundPosition.value,
	backgroundSize: backgroundSize.value,
	backgroundRepeat: backgroundRepeat.value,
}));

const sizeOptions = [
	{ label: "Contain", value: "contain" },
	{ label: "Cover", value: "cover" },
	{ label: "Auto", value: "auto" },
];

const positionOptions = [
	{ label: "Center", value: "center" },
	{ label: "Top", value: "top" },
	{ label: "Bottom", value: "bottom" },
	{ label: "Left", value: "left" },
	{ label: "Right", value: "right" },
];

const repeatOptions = [
	{ label: "No Repeat", value: "no-repeat" },
	{ label: "Repeat", value: "repeat" },
	{ label: "Repeat X", value: "repeat-x" },
	{ label: "Repeat Y", value: "repeat-y" },
];

const setBGImage = (file: { file_url: string }) => {
	blockController.setStyle("backgroundImage", `url(${file.file_url})`);
	if (!blockController.getStyle("backgroundSize")) {
		blockController.setStyle("backgroundSize", "cover");
	}
	if (!blockController.getStyle("backgroundPosition")) {
		blockController.setStyle("backgroundPosition", "center");
	}
	if (!blockController.getStyle("backgroundRepeat")) {
		blockController.setStyle("backgroundRepeat", "no-repeat");
	}
};

const setBGImageURL = (url: string) => {
	blockController.setStyle("backgroundImage", url ? `url(${url})` : null);
};

const setBGSize = (value: string) => {
	blockController.setStyle("backgroundSize", value);
};

const setBGPosition = (value: string) => {
	blockController.setStyle("backgroundPosition", value);
};

const setBGRepeat = (value: string) => {
	blockController.setStyle("backgroundRepeat", value);
};

const clearBGImage = () => {
	blockController.setStyle("backgroundImage", null);
	blockController.setStyle("backgroundSize", null);
	blockController.setStyle("backgroundPosition", null);
	blockController.setStyle("backgroundRepeat", null);
};
</script>
