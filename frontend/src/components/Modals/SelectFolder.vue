<template>
	<Dialog
		class="overscroll-none"
		v-model="showModel"
		:options="{
			title: 'Select Folder',
			size: 'sm',
		}">
		<template #body-content>
			<span
				class="flex cursor-pointer gap-2 rounded p-2 text-base text-ink-gray-6"
				@click="$emit('folderSelected', null)">
				<FeatherIcon name="home" class="size-4"></FeatherIcon>
				Home
			</span>
			<span
				class="flex cursor-pointer gap-2 rounded p-2 text-base text-ink-gray-6"
				v-for="project in builderProjectFolder.data"
				@click="$emit('folderSelected', project.folder_name)">
				<FolderIcon class="size-4"></FolderIcon>
				{{ project.folder_name }}
			</span>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import FolderIcon from "@/components/Icons/Folder.vue";
import builderProjectFolder from "@/data/builderProjectFolder";
import { useVModel } from "@vueuse/core";
import { ref } from "vue";

const folderName = ref("");
const props = defineProps<{
	currentFolder: string;
	modelValue: boolean;
}>();

const emit = defineEmits(["update:modelValue", "folderSelected"]);
const showModel = useVModel(props, "modelValue", emit);
</script>
