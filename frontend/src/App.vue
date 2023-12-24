<template>
	<div>
		<router-view v-slot="{ Component }">
			<keep-alive>
				<component :is="Component" />
			</keep-alive>
		</router-view>
		<Toasts />
		<UseDark></UseDark>
		<Toaster :theme="isDark ? 'dark' : 'light'" />
	</div>
</template>
<script setup lang="ts">
import { UseDark } from "@vueuse/components";
import { useDark } from "@vueuse/core";
import { Toasts } from "frappe-ui";
import { Toaster } from "vue-sonner";

const isDark = useDark();
</script>
