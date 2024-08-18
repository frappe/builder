<template>
	<div class="h-screen w-full overflow-hidden bg-gray-200 dark:bg-zinc-800">
		<div
			class="toolbar relative z-10 flex h-14 items-center justify-center bg-white p-2 shadow-sm dark:border-b-[1px] dark:border-gray-800 dark:bg-zinc-900">
			<div class="absolute left-3 flex items-center gap-3">
				<!-- go back -->
				<FeatherIcon
					name="chevron-left"
					class="h-6 w-6 cursor-pointer !text-gray-700 dark:!text-gray-200"
					@click="$router.back()"></FeatherIcon>
			</div>
		</div>
		<div class="flex h-full flex-1">
			<!-- sidebar -->
			<div class="flex h-full w-72 flex-col gap-6 bg-white p-4 shadow-sm dark:bg-zinc-900">
				<div class="flex flex-col gap-3">
					<span class="font-semibold text-gray-800 dark:text-zinc-200">Page Settings</span>
					<div class="flex flex-col gap-2">
						<span class="text-base text-gray-700 dark:text-zinc-400">General</span>
						<span class="text-base text-gray-700 dark:text-zinc-400">Meta</span>
						<span class="text-base text-gray-700 dark:text-zinc-400">Robots</span>
						<span class="text-base text-gray-700 dark:text-zinc-400">Analytics</span>
					</div>
				</div>
				<div class="flex flex-col gap-3">
					<span class="font-semibold text-gray-800 dark:text-zinc-200">Global Settings</span>
					<div class="flex flex-col gap-2">
						<span class="text-base text-gray-700 dark:text-zinc-400">General</span>
						<span class="text-base text-gray-700 dark:text-zinc-400">Meta</span>
						<span class="text-base text-gray-700 dark:text-zinc-400">Redirects</span>
						<span class="text-base text-gray-700 dark:text-zinc-400">Code</span>
					</div>
				</div>
			</div>
			<!-- main -->
			<div class="flex w-full flex-col items-center gap-10 p-10">
				<div
					class="flex h-fit w-2/4 max-w-4xl flex-col gap-5 rounded bg-white p-5 shadow-sm dark:bg-zinc-900">
					<span class="text-xl font-semibold text-gray-800 dark:text-zinc-200">General</span>
					<div class="flex flex-col gap-4">
						<div class="flex gap-5">
							<Input
								type="text"
								label="Page Title"
								:modelValue="store.activePage?.page_title"
								@update:modelValue="(val) => store.updateActivePage('page_title', val)"></Input>
							<Input
								type="text"
								label="Page Route"
								:modelValue="store.activePage?.route"
								@update:modelValue="(val) => store.updateActivePage('route', val)"></Input>
						</div>
						<Input
							type="textarea"
							label="Page Description"
							:modelValue="store.activePage?.meta_description"
							@update:modelValue="(val) => store.updateActivePage('meta_description', val)"></Input>
					</div>
					<div class="flex flex-col gap-2">
						<span class="text-base font-semibold text-gray-800 dark:text-zinc-200">Preview</span>

						<div class="flex items-center justify-between">
							<div
								class="flex h-fit w-full flex-col gap-1 rounded-md border border-gray-100 p-4 dark:border-zinc-800">
								<span class="text-sm italic text-gray-600">{{ store.activePage?.route }}</span>
								<span class="mt-2 text-base text-blue-600">{{ store.activePage?.page_title }}</span>
								<span class="text-sm italic text-gray-600">
									{{ store.activePage?.meta_description }}
								</span>
							</div>
						</div>
					</div>
					<hr class="dark:border-zinc-800" />
					<div class="flex flex-col gap-2">
						<div class="flex items-center justify-between">
							<div class="flex flex-col gap-2">
								<span class="text-base dark:text-zinc-200">Unpublish</span>
								<p class="text-sm text-gray-600">Unpublish your page</p>
							</div>
							<Button variant="subtle" theme="red" @click="store.unpublishPage()">Unpublish</Button>
						</div>
					</div>
				</div>
				<div
					class="flex h-fit w-2/4 max-w-4xl flex-col gap-5 rounded bg-white p-5 shadow-sm dark:bg-zinc-900">
					<span class="text-xl font-semibold text-gray-800 dark:text-zinc-200">Meta</span>
					<div class="flex flex-col gap-4"></div>
					<div class="flex flex-col gap-2">
						<span class="text-base font-semibold text-gray-800 dark:text-zinc-200">Preview</span>
						<div class="flex items-center justify-between"></div>
					</div>
					<div class="flex flex-col gap-2">
						<div class="flex items-center justify-between"></div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import Input from "@/components/Input.vue";
import useStore from "@/store";
import { ref } from "vue";

const store = useStore();
const isDark = ref(false);
</script>
