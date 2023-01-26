import { defineStore } from "pinia";

const useStore = defineStore("store", {
	state: () => ({
		selectedComponent: null,
		alignments: [{
			name: "Left",
			class: "justify-start",
			icon: "align-left",
		}, {
			name: "Center",
			class: "justify-center",
			icon: "align-center",
		}, {
			name: "Right",
			class: "justify-end",
			icon: "align-right",
		}, {
			name: "Justify",
			class: "justify-between",
			icon: "align-justify",
		}],
		pageName: "test-879",
		route: "pages/home",
		pages: {},
		activeBreakpoint: "desktop",
		blocks: [],
		pastelCssColors: ["#F5FFFA", "#F8F8FF", "#F0F8FF", "#F5F5DC", "#FFE4C4", "#FFEBCD", "#FFDEAD", "#FFC1C1", "#FFB6C1", "#FFA07A", "#FF8C00", "#FF7F50", "#FF69B4", "#FF6347", "#FDB813", "#FDAB9F", "#FDA50F", "#F49AC2", "#FFB347", "#FFD700", "#ADFF2F", "#87CEFA", "#00BFFF", "#ADD8E6", "#B0E0E6", "#5F9EA0", "#FDD5B1", "#FCCDE3", "#FCC2D9", "#FCB4D5", "#FBB5A3", "#FBB917", "#FBB972", "#FBB9AC", "#FBCEB1",
			"linear-gradient(120deg, #f093fb 0%, #f5576c 100%)",
			"linear-gradient(to top, #a18cd1 0%, #fbc2eb 100%)",
			"linear-gradient(to top, #a8edea 0%, #fed6e3 100%)",
			"linear-gradient(to top, #96fbc4 0%, #f9f586 100%)",
			"linear-gradient(to top, #9795f0 0%, #fbc8d4 100%)",
			"linear-gradient(-60deg, #16a085 0%, #f4d03f 100%)",
			"linear-gradient( 135deg, #81FFEF 10%, #F067B4 100%)"
		],
		textColors: ["#000000", "#424242", "#636363", "#9C9C94", "#CEC6CE", "#EFEFEF", "#F7F7F7", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF", "#C0C0C0", "#808080", "#808000", "#008080", "#800080", "#800000"],
		deviceBreakpoints: {
			desktop: {
				icon: "monitor",
				device: "desktop",
				width: 1024,
			},
			tablet: {
				icon: "tablet",
				device: "tablet",
				width: 640,
			},
			mobile: {
				icon: "smartphone",
				device: "mobile",
				width: 320,
			},
		},
	}),
	actions: {
		getActiveBreakpoint() {
			return this.deviceBreakpoints[this.activeBreakpoint].width;
		},
	},
});

export default useStore;
