<template>
  <div>
    <router-view />
		<Toasts />
  </div>
</template>
<script setup>
import { Toasts } from 'frappe-ui'
</script>
