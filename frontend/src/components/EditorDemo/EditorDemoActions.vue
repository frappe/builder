<template>
	<div class="flex items-center gap-3">
		<Tooltip :text="__('A sandboxed copy of this page. Nothing you change is saved.')" :hoverDelay="300">
			<Badge variant="subtle" theme="blue">{{ __("Demo") }}</Badge>
		</Tooltip>
		<span class="text-sm text-ink-gray-5">{{ __("Changes aren't saved") }}</span>
		<Button variant="solid" @click="editorDemoStage.exit()">{{ __("Exit demo") }}</Button>
	</div>
</template>
<script setup lang="ts">
import { editorDemoStage } from "@/components/EditorDemo/editorDemoStage";
import { __ } from "@/translation";
import { Badge, Tooltip } from "frappe-ui";
</script>
