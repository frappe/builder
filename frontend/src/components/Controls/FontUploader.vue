<template>
	<BuilderButton
		iconLeft="plus"
		class="w-full rounded-none text-xs text-ink-gray-8"
		@click="openFileSelector">
		Upload Font
	</BuilderButton>
</template>
<script lang="ts" setup>
import userFont from "@/data/userFonts";
import blockController from "@/utils/blockController";
import { getFontName } from "@/utils/helpers";
import { FileUploadHandler } from "frappe-ui";
import { nextTick } from "vue";
import { toast } from "vue-sonner";
const emit = defineEmits(["change"]);

type FileDoc = {
	file_name: string;
	file_url: string;
};

const openFileSelector = () => {
	const input = document.createElement("input");
	input.type = "file";
	input.accept = ".woff2,.woff,.ttf,.otf";
	input.onchange = (e) =>
		toast.promise(
			new Promise(async (resolve) => {
				const file = (e.target as HTMLInputElement)?.files?.[0];
				if (file) {
					const fileUploadHandler = new FileUploadHandler();
					const fileDoc = await fileUploadHandler.upload(file, {
						private: false,
						folder: "Home/Builder Uploads/Fonts",
					});
					await uploadFont(fileDoc);
				}
				resolve(null);
			}),
			{
				loading: "Uploading font...",
				success: () => "Font uploaded",
			},
		);
	input.click();
};

const uploadFont = async (file: FileDoc) => {
	const fontFamilyName = await getFontName(file.file_url);
	const fontURL = file.file_url;
	const fontFace = new FontFace(fontFamilyName, `url("${fontURL}")`);
	const loadedFont = await fontFace.load();
	document.fonts.add(loadedFont);
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
	await userFont.fetch();
	emit("change");
	await nextTick();
	if (blockController.isBlockSelected()) {
		blockController.setFontFamily(fontFace.family);
	}
};
</script>
