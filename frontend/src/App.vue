<template>
	<div>
		<router-view v-slot="{ Component }">
			<keep-alive>
				<component :is="Component" />
			</keep-alive>
		</router-view>
		<Toasts />
		<UseDark></UseDark>
	</div>
</template>
<script setup lang="ts">
import { UseDark } from "@vueuse/components";
import { Toasts } from "frappe-ui";
</script>
