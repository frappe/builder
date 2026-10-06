<template>
	<div class="flex flex-col gap-4">
		<p class="text-p-sm text-ink-gray-6">
			{{
				__(
					"Paste this into your coding agent (Claude Code, Codex, OpenCode and others) to let it build, edit and publish pages on this site. When your browser asks, click Allow.",
				)
			}}
		</p>
		<div class="flex items-start gap-2 rounded-4 bg-surface-gray-1 px-3 py-2.5">
			<p class="min-w-0 flex-1 break-words text-p-sm text-ink-gray-9">
				<template v-for="(part, i) in promptParts" :key="i">
					<code
						v-if="part.code"
						class="rounded bg-surface-gray-3 px-1 py-0.5 font-mono text-p-xs"
						v-text="part.text" />
					<template v-else>{{ part.text }}</template>
				</template>
			</p>
			<Button variant="subtle" icon-left="lucide-copy" :label="__('Copy')" @click="copyPrompt" />
		</div>
		<p v-if="!reachable" class="text-p-xs text-ink-amber-8">
			{{ __("Agents can only reach this site over https or at a *.localhost address.") }}
		</p>
		<p class="text-p-xs text-ink-gray-5">
			{{ __("It works as your user, so your user needs the Website Manager role.") }}
		</p>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { Button, toast } from "frappe-ui";

const site = window.location.origin;
const host = window.location.hostname;
// frappectl refuses plain http anywhere but localhost
const reachable =
	window.location.protocol === "https:" || host === "localhost" || host.endsWith(".localhost");

const promptParts = [
	{ text: "Install the frappe-builder skill with " },
	{ text: "npx skills add frappe/builder -g -y", code: true },
	{ text: ", read its SKILL.md, and connect to " },
	{ text: site, code: true },
	{ text: ". Then suggest what we could build first." },
];
// agents read the copied text as markdown
const prompt = promptParts.map((part) => (part.code ? `\`${part.text}\`` : part.text)).join("");

async function copyPrompt() {
	try {
		await navigator.clipboard.writeText(prompt);
		toast.success(__("Copied to clipboard"));
	} catch {
		toast.error(__("Failed to copy"));
	}
}
</script>
