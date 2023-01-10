import { defineStore } from 'pinia';

export const useStore = defineStore('store', {
	state: () => ({
		"active_breakpoint": "desktop",
		"blocks": [{
			id: 1,
			name: 'Container',
			element: "div",
			icon: "square",
			attributes: {
				class: "bg-gray-300 h-[300px] w-full"
			}
		}],
		"device_breakpoints": {
			"desktop": {
				"icon": "monitor",
				"device": "desktop",
				"width": 1024,
			},
			"tablet": {
				"icon": "tablet",
				"device": "tablet",
				"width": 640,
			},
			"mobile": {
				"icon": "smartphone",
				"device": "mobile",
				"width": 320,
			},
		},
	}),
	actions: {
		get_active_breakpoint() {
			return this.device_breakpoints[this.active_breakpoint].width;
		},
	}
});