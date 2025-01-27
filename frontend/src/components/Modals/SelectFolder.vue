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
				class="flex gap-2 rounded p-2 text-base text-ink-gray-3"
				:class="{
					'cursor-pointer text-ink-gray-6 hover:text-ink-gray-9': currentFolder,
				}"
				@click="folderSelected('')">
				<FeatherIcon name="home" class="size-4"></FeatherIcon>
				Home
			</span>
			<span
				class="flex cursor-default gap-2 rounded p-2 text-base text-ink-gray-2"
				v-for="project in builderProjectFolder.data"
				:class="{
					'cursor-pointer !text-ink-gray-6 hover:!text-ink-gray-9': currentFolder !== project.folder_name,
				}"
				@click="folderSelected(project.folder_name)">
				<FolderIcon class="size-4"></FolderIcon>
				{{ project.folder_name }}
			</span>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import FolderIcon from "@/components/Icons/Folder.vue";
import builderProjectFolder from "@/data/builderProjectFolder";
import { useVModel } from "@vueuse/core";

const props = defineProps<{
	currentFolder: string;
	modelValue: boolean;
}>();

const emit = defineEmits(["update:modelValue", "folderSelected"]);
const showModel = useVModel(props, "modelValue", emit);

const folderSelected = (folder: string | null) => {
	if (folder === props.currentFolder) {
		return;
	}
	emit("folderSelected", folder);
	showModel.value = false;
};
</script>
