<template>
	<Tooltip
		v-if="plugin.has_draft && !plugin.is_shared"
		text="Bob built it for you. No one else runs it until you share it.">
		<Badge size="sm" theme="blue" label="Only you" />
	</Tooltip>
	<Tooltip
		v-else-if="plugin.has_draft"
		text="You run changes that no one else has yet. Share the update to give them out.">
		<Badge size="sm" theme="amber" label="Changed" />
	</Tooltip>
	<Badge v-else-if="plugin.source === 'Bob'" size="sm" theme="gray" label="Shared" />
</template>

<script setup lang="ts">
import type { Installation } from "@/data/plugins";
import { Badge, Tooltip } from "frappe-ui";

defineProps<{ plugin: Installation }>();
</script>
