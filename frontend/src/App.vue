<template>
	<div>
		<router-view v-slot="{ Component }">
			<keep-alive>
				<component :is="Component" />
			</keep-alive>
		</router-view>
		<UseDark></UseDark>
		<Toaster :theme="isDark ? 'dark' : 'light'" richColors />
	</div>
</template>
<script setup lang="ts">
import { UseDark } from "@vueuse/components";
import { useDark } from "@vueuse/core";
import { Toaster } from "vue-sonner";

const isDark = useDark();
</script>
