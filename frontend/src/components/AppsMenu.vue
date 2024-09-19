<template>
	<Popover placement="right-start" trigger="hover" :hoverDelay="0.1" :leaveDelay="0.1">
		<template #target="{ togglePopover, isOpen }">
			<button
				class="flex h-7 w-full items-center justify-between rounded px-2 text-base hover:bg-surface-gray-2"
				:class="{ 'bg-surface-gray-2': isOpen }"
				@click.prevent="togglePopover()">
				<div class="flex gap-2">
					<FeatherIcon name="grid" class="size-4" />
					<span>Apps</span>
				</div>
				<FeatherIcon name="chevron-right" class="size-4" />
			</button>
		</template>
		<template #body>
			<div
				class="mx-3 grid grid-cols-3 rounded-lg border border-outline-gray-2 bg-surface-white p-2 text-sm text-text-icons-gray-8 shadow-xl dark:bg-surface-gray-1">
				<div v-for="app in apps.data" key="name">
					<a
						:href="app.route"
						class="flex flex-col items-center justify-center gap-1.5 rounded px-3 py-2 hover:bg-surface-gray-2">
						<img class="size-8" :src="app.logo" />
						<router-link :to="app.route">
							{{ app.title }}
						</router-link>
					</a>
				</div>
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
