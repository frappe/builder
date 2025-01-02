<template>
	<Popover placement="right-start" trigger="hover" :hoverDelay="0.1" :leaveDelay="0.1">
		<template #target="{ togglePopover, isOpen }">
			<button
				class="flex h-7 w-full items-center justify-between rounded px-2 text-base hover:bg-surface-gray-2"
				:class="{ 'bg-surface-gray-2': isOpen }"
				@click.prevent="togglePopover()">
				<div class="flex gap-2">
					<FeatherIcon name="grid" class="size-4" />
					<span class="text-ink-gray-7">Apps</span>
				</div>
				<FeatherIcon name="chevron-right" class="size-4" />
			</button>
		</template>
		<template #body>
			<div
				class="flex w-fit min-w-32 max-w-48 flex-col rounded-lg border border-outline-gray-2 bg-surface-white p-1.5 text-sm text-ink-gray-8 shadow-xl auto-fill-[100px] dark:bg-surface-gray-1">
				<a
					:href="app.route"
					v-for="app in apps.data"
					key="name"
					class="flex items-center gap-2 rounded p-1 hover:bg-surface-gray-2">
					<img class="size-6" :src="app.logo" />
					<span class="max-w-18 w-full truncate">
						{{ app.title }}
					</span>
				</a>
			</div>
		</template>
	</Popover>
</template>
<script setup lang="ts">
import { Popover, createResource } from "frappe-ui";
const apps = createResource({
	url: "builder.api.get_apps",
	cache: "other_apps",
	auto: true,
});
</script>
