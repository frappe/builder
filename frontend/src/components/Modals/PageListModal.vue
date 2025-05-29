<template>
	<Dialog
		class="overscroll-none"
		v-model="showModel"
		:options="{
			title: 'Used in following pages',
			size: 'xl',
		}">
		<template #body-content>
			<div class="max-h-[80vh] overflow-y-auto">
				<div v-for="page in pages">
					<router-link
						target="_blank"
						:to="{
							name: 'builder',
							params: {
								pageId: page.name,
							},
						}">
						<div class="flex items-start space-x-4 rounded p-2 hover:bg-surface-gray-2">
							<img
								:src="page.preview"
								:alt="page.page_title"
								class="w-26 h-16 rounded-lg border border-outline-gray-1" />
							<div>
								<div class="font-bold">{{ page.page_title }}</div>
								<div class="text-sm text-gray-500">{{ page.route }}</div>
							</div>
						</div>
					</router-link>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { ref } from "vue";
const showModel = ref(true);
defineProps<{
	pages: BuilderPage[];
}>();
</script>
