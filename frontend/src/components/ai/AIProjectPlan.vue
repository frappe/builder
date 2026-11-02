<template>
	<div class="space-y-3">
		<p v-if="!project" class="text-p-sm text-ink-gray-6">
			Ask Bob to plan your site's pages. Routes, dependencies and progress stay with the project across chats.
		</p>
		<template v-else>
			<h3 class="text-p-lg font-medium">{{ project.title }}</h3>
			<p class="whitespace-pre-wrap text-p-sm text-ink-gray-6">{{ project.brief }}</p>
			<div
				v-for="task in project.tasks"
				:key="task.id"
				class="space-y-1 rounded border border-outline-gray-2 p-3">
				<div class="flex justify-between gap-2">
					<p class="font-medium">{{ task.title }}</p>
					<span class="text-p-xs capitalize">{{ task.status }}</span>
				</div>
				<p class="text-p-sm text-ink-gray-6">/{{ task.route }} · {{ task.goal }}</p>
				<p v-if="task.depends_on?.length" class="text-p-xs text-ink-gray-6">
					Depends on: {{ task.depends_on.join(", ") }}
				</p>
				<p v-if="task.evidence" class="text-p-sm">{{ task.evidence }}</p>
				<a
					v-if="task.page"
					:href="`${base}/page/${encodeURIComponent(task.page)}`"
					class="text-p-sm underline">
					Open draft
				</a>
			</div>
		</template>
	</div>
</template>
<script setup lang="ts">
defineProps<{ project: { title: string; brief: string; tasks: Array<Record<string, any>> } | null }>();
const base = `/${(window.builder_path || "builder").replace(/^\/+|\/+$/g, "")}`;
</script>
