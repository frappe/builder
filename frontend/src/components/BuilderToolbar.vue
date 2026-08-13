<template>
	<div
		class="toolbar border-outline border-outline flex items-center justify-center border-b-[1px] border-outline-gray-2 bg-surface-base px-2 py-1 dark:border-outline-gray-1"
		ref="toolbar">
		<div class="absolute left-3 flex items-center gap-4">
			<component
				v-for="item of itemsIn('left')"
				:key="item.name"
				:is="item.component"
				v-bind="item.props?.()" />
		</div>
		<div class="flex items-center gap-2">
			<component
				v-for="item of itemsIn('center')"
				:key="item.name"
				:is="item.component"
				v-bind="item.props?.()" />
		</div>
		<div class="absolute right-3 flex items-center gap-4">
			<component
				v-for="item of itemsIn('right')"
				:key="item.name"
				:is="item.component"
				v-bind="item.props?.()" />
		</div>

		<Dialog :title="__('Get Started')" size="4xl" v-model="showInfoDialog">
			<template #default>
				<iframe
					class="h-[60vh] w-full rounded-sm"
					src="https://www.youtube-nocookie.com/embed/videoseries?si=8NvOFXFq6ntafauO&amp;controls=0&amp;list=PL3lFfCEoMxvwZsBfCgk6vLKstZx204xe3"
					:title="__('Frappe Builder - Get Started')"
					frameborder="0"
					allowfullscreen></iframe>
			</template>
		</Dialog>
		<Dialog v-model="builderStore.showSettingsDialog" :dismissable="false" size="5xl" bare>
			<template #default>
				<DialogTitle class="sr-only">{{ __("Builder Settings") }}</DialogTitle>
				<DialogDescription class="sr-only">
					{{ __("Configure page and global settings for this project.") }}
				</DialogDescription>
				<BuilderSettings
					:initial-tab="builderStore.settingsActiveTab"
					@close="builderStore.showSettingsDialog = false"></BuilderSettings>
			</template>
		</Dialog>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import Dialog from "@/components/Controls/Dialog.vue";
import { toolbarItems, type ToolbarRegion } from "@/components/ToolbarItems";
import useBuilderStore from "@/stores/builderStore";
import { DialogDescription, DialogTitle } from "reka-ui";
import { defineAsyncComponent, ref } from "vue";

const BuilderSettings = defineAsyncComponent(() => import("./BuilderSettings.vue"));

const builderStore = useBuilderStore();

const itemsIn = (region: ToolbarRegion) =>
	toolbarItems.visible.value.filter((item) => item.region === region);

const showInfoDialog = ref(false);
</script>
