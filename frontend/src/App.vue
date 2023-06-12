<template>
	<div>
		<router-view />
		<Toasts />
		<UseDark></UseDark>
	</div>
</template>
<script setup lang="ts">
import { Toasts } from "frappe-ui";
import { UseDark } from "@vueuse/components";
</script>
