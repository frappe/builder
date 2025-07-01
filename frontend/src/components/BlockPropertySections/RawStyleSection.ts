import ObjectEditor from "@/components/ObjectEditor.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

const rawStyleSectionProperties = [
	{
		component: ObjectEditor,
		getProps: () => {
			return {
				obj: blockController.getRawStyles() as Record<string, string>,
				description: `
					<b>Note:</b>
					<br />
					<br />
					• Raw styles get applied across all devices
					<br />
					• State based styles are supported (e.g. hover, focus, visited)
					<br />
					Syntax: hover:color, focus:color, etc.
					<br />
					• State styles are only activated in preview mode
				`,
			};
		},
		searchKeyWords: "Raw, RawStyle, Raw Style, CSS, Style, Styles",
		events: {
			"update:obj": (obj: Record<string, string>) => blockController.setRawStyles(obj),
		},
	},
];

export default {
	name: "Raw Style",
	properties: rawStyleSectionProperties,
	collapsed: computed(() => {
		return Object.keys(blockController.getRawStyles()).length === 0;
	}),
};
