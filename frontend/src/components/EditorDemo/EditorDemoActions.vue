<template>
	<div class="flex items-center gap-3">
		<Tooltip :text="__('Changes aren\'t saved')" :hoverDelay="300">
			<Badge variant="subtle" theme="blue">{{ __("Demo") }}</Badge>
		</Tooltip>
		<Button variant="solid" @click="editorDemoStage.exit()">{{ __("Exit demo") }}</Button>
	</div>
</template>
<script setup lang="ts">
import { editorDemoStage } from "@/components/EditorDemo/editorDemoStage";
import { __ } from "@/translation";
import { Badge, Tooltip } from "frappe-ui";
</script>
