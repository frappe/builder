<template>
	<BuilderButton
		iconLeft="plus"
		class="w-full rounded-none text-xs text-text-icons-gray-8"
		@click="openFileSelector">
		Upload Font
	</BuilderButton>
</template>
<script lang="ts" setup>
import userFont from "@/data/userFonts";
import blockController from "@/utils/blockController";
import { FileUploadHandler } from "frappe-ui";
const emit = defineEmits(["change"]);

type FileDoc = {
	file_name: string;
	file_url: string;
};

const openFileSelector = () => {
	const input = document.createElement("input");
	input.type = "file";
	input.accept = ".woff2,.woff,.ttf,.otf";
	input.onchange = (e: Event) => {
		const file = (e.target as HTMLInputElement)?.files?.[0];
		if (file) {
			const fileUploadHandler = new FileUploadHandler();
			fileUploadHandler
				.upload(file, {
					private: false,
					folder: "Home/Builder Uploads/Fonts",
				})
				.then((fileDoc: FileDoc) => {
					uploadFont(fileDoc);
				});
		}
	};
	input.click();
};

const uploadFont = async (file: FileDoc) => {
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
	} catch (e: any) {
		if (e?.message?.includes("DuplicateEntryError")) {
			console.log("Font already exists");
		}
	}
	if (blockController.isBLockSelected()) {
		blockController.setFontFamily(fontFace.family);
	}
	emit("change");
};
</script>
