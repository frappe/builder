<template>
	<FileUploader
		:file-types="image_type"
		class="text-base"
		@success="
			(file: FileDoc) => {
				$emit('upload', file.file_url);
			}
		">
		<template v-slot="{ file, progress, uploading, openFileSelector }">
			<div class="flex items-end gap-2">
				<Button @click="openFileSelector">
					{{ uploading ? __("Uploading {0}%", [progress]) : image_url ? __("Change") : __("Upload") }}
				</Button>
				<Button v-if="image_url" @click="$emit('remove')">{{ __("Remove") }}</Button>
			</div>
		</template>
	</FileUploader>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { FileUploader } from "frappe-ui";
const prop = withDefaults(
	defineProps<{
		image_url?: string;
		image_type?: string;
		label?: string;
	}>(),
	{
		image_type: "image/*",
		label: "",
	},
);
const emit = defineEmits(["upload", "remove"]);
</script>
