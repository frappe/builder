<template>
	<FileUploader
		@success="uploadFont"
		fileTypes="font/ttf,font/otf,font/woff,font/woff2,application/vnd.ms-fontobject"
		:uploadArgs="{
			private: false,
			folder: 'Home/Builder Uploads/Fonts',
		}">
		<template v-slot="{ openFileSelector }">
			<BuilderButton
				iconLeft="plus"
				class="w-full rounded-none text-xs text-text-icons-gray-8"
				@click="openFileSelector">
				Upload Font
			</BuilderButton>
		</template>
	</FileUploader>
</template>
<script lang="ts" setup>
import userFont from "@/data/userFonts";
import blockController from "@/utils/blockController";
import { FileUploader } from "frappe-ui";
const uploadFont = async (file: { file_name: string; file_url: string }) => {
	const fontName = file.file_name.split(".")[0];
	const fontURL = file.file_url;
	console.log(fontName, fontURL);
	const fontFace = new FontFace(fontName, `url(${fontURL})`);
	await fontFace.load();
	await userFont.insert.submit({
		font_name: fontFace.family,
		font_file: fontURL,
	});
	// if text is selected, apply the font
	if (blockController.isText()) {
		blockController.setStyle("font-family", fontFace.family);
	}
};
</script>
