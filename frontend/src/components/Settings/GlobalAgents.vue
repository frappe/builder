<template>
	<div class="flex flex-col gap-4">
		<p class="text-p-sm text-ink-gray-6">
			{{
				__(
					"Let your own coding agent (Claude Code, Codex, OpenCode and others) build, edit and publish pages on this site. It needs a user with the Website Manager role.",
				)
			}}
		</p>
		<div class="overflow-hidden rounded-4 bg-surface-gray-1">
			<div v-for="(step, i) in steps" :key="i" class="flex items-center gap-2 px-3 py-2.5">
				<div class="min-w-0 flex-1">
					<p class="text-p-sm-medium text-ink-gray-8">{{ step.label }}</p>
					<p class="break-words font-mono text-p-xs text-ink-gray-9">{{ step.command }}</p>
					<p v-if="step.hint" class="text-p-xs text-ink-gray-5">{{ step.hint }}</p>
				</div>
				<button
					type="button"
					@click="copyToClipboard(step.command)"
					class="shrink-0 text-ink-gray-4 transition-colors hover:text-ink-gray-7">
					<span class="lucide-copy h-3.5 w-3.5" aria-hidden="true" />
				</button>
			</div>
		</div>
		<a
			href="https://github.com/frappe/builder/blob/develop/skills/frappe-builder/SKILL.md"
			target="_blank"
			class="text-p-sm text-ink-gray-6 underline">
			{{ __("What the skill can do") }}
		</a>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { toast } from "frappe-ui";

const site = window.location.origin;
const profile = window.location.hostname.split(".")[0];

const steps = [
	{
		label: __("1. Add the skill to your agent"),
		command: "npx skills add frappe/builder",
	},
	{
		label: __("2. Sign in to this site"),
		command: `frappectl auth login ${site} --name ${profile} --oauth`,
		hint: __("Opens your browser. Install frappectl first with: uv tool install frappectl"),
	},
	{
		label: __("3. Ask your agent"),
		command: `Using the frappe-builder skill and the frappectl profile "${profile}", add a testimonials section to the home page`,
	},
];

async function copyToClipboard(text: string) {
	try {
		await navigator.clipboard.writeText(text);
		toast.success(__("Copied to clipboard"));
	} catch {
		toast.error(__("Failed to copy"));
	}
}
</script>
