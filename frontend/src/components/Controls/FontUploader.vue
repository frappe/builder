<template>
	<FileUploader
		@success="uploadFont"
		fileTypes=".woff2,.woff,.ttf,.otf"
		:uploadArgs="{
			private: false,
			folder: 'Home/Builder Uploads/Fonts',
		}">
		<template v-slot="{ openFileSelector }" #default>
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
const emit = defineEmits(["change"]);
const uploadFont = async (file: { file_name: string; file_url: string }) => {
	const fontName = file.file_name.split(".")[0];
	const fontURL = file.file_url;
	const fontFace = new FontFace(fontName, `url("${fontURL}")`);
	await fontFace.load();
	try {
		await userFont.insert.submit({
			font_name: fontFace.family,
			font_file: fontURL,
		});
		await userFont.list.promise;
	} catch (e) {
		if (e.message?.includes("DuplicateEntryError")) {
			console.log("Font already exists");
		}
	}
	// if text is selected, apply the font
	if (blockController.isText()) {
		blockController.setFontFamily(fontFace.family);
	}
	emit("change");
};
</script>
