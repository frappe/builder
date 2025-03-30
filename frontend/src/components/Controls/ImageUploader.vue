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
			<div class="flex items-end space-x-1">
				<!-- <BuilderInput v-model="url" readonly="true" :hideClearButton="true" :label="label"></BuilderInput> -->
				<BuilderButton @click="openFileSelector">
					{{ uploading ? `Uploading ${progress}%` : image_url ? "Change" : "Upload" }}
				</BuilderButton>
				<BuilderButton v-if="image_url" @click="$emit('remove')">Remove</BuilderButton>
			</div>
		</template>
	</FileUploader>
</template>
<script setup lang="ts">
import { FileUploader } from "frappe-ui";
import { computed } from "vue";
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
const url = computed(() => prop.image_url);
</script>
