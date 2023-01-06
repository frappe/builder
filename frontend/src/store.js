import { defineStore } from 'pinia';

export const useStore = defineStore('store', {
	state: () => ({
		"active_breakpoint": "desktop",
		"active_device_width": 1024,
	}),
});