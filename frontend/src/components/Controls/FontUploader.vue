<template>
	<BuilderButton
		iconLeft="plus"
		class="w-full rounded-none text-xs text-ink-gray-8"
		@click="openFileSelector">
		Upload Font
	</BuilderButton>
</template>
<script lang="ts" setup>
import blockController from "@/utils/blockController";
import { uploadUserFont } from "@/utils/helpers";
import { nextTick } from "vue";
const emit = defineEmits(["change"]);

const openFileSelector = () => {
	const input = document.createElement("input");
	input.type = "file";
	input.accept = ".woff2,.woff,.ttf,.otf";
	input.onchange = async (e) => {
		const file = (e.target as HTMLInputElement)?.files?.[0];
		if (file) {
			const result = await uploadUserFont(file);
			if (result?.uploaded) {
				emit("change");
				await nextTick();
				if (blockController.isBlockSelected()) {
					blockController.setFontFamily(result.fontName);
				}
			}
		}
	};
	input.click();
};
</script>
