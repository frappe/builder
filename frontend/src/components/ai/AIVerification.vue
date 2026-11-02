<template>
	<div class="space-y-4">
		<p v-if="!reports.length" class="text-p-sm text-ink-gray-6">
			Ask Bob to verify the page. Results are tied to the exact page revision that was checked.
		</p>
		<div
			v-for="report in reports"
			:key="report.id"
			class="space-y-3 rounded border border-outline-gray-2 p-3">
			<p class="font-medium">
				{{ report.status === "issues_found" ? "Issues found" : "Automated checks completed" }}
			</p>
			<p v-if="report.stale" class="text-p-sm text-ink-orange-5">The page changed after this check.</p>
			<div v-for="view in report.views" :key="view.viewport.width" class="space-y-2 text-p-sm">
				<p class="font-medium">{{ view.viewport.width }}px viewport</p>
				<p v-if="!view.issues.length && !view.runtimeErrors.length">
					No issues found by these automated checks.
				</p>
				<ul v-else class="list-disc space-y-1 pl-5">
					<li v-for="(issue, i) in view.issues" :key="i">
						{{ issue.code }}: {{ issue.detail }} — {{ issue.target }}
					</li>
					<li v-for="(error, i) in view.runtimeErrors" :key="`error-${i}`">{{ error }}</li>
				</ul>
				<ul v-if="view.interactions?.length" class="list-disc space-y-1 pl-5">
					<li v-for="(step, i) in view.interactions" :key="i">
						{{ step.passed ? "Passed" : "Failed" }}: {{ step.action }} {{ step.selector }}
						{{ step.detail || (step.state ? `(${step.state})` : "") }}
					</li>
				</ul>
				<p class="text-ink-gray-6">Manual checks remain: {{ view.manualChecks.join(", ") }}.</p>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
defineProps<{ reports: Array<Record<string, any>> }>();
</script>
