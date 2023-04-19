<template>
	<div>
		<router-view />
		<Toasts />
	</div>
</template>
<script setup lang="ts">
import { Toasts } from "frappe-ui";
</script>
