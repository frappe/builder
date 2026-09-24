<template>
	<div>
		<div class="flex h-7 items-center px-3 pt-2 text-sm font-medium text-ink-gray-7">
			{{ __("Components") }}
		</div>
		<BuilderAssets class="px-3 pb-3" />
	</div>
</template>
<script setup lang="ts">
import BuilderAssets from "@/components/BuilderAssets.vue";
import { __ } from "@/translation";
</script>
