import builder from "frappe-builder-extension-sdk";
import { vueAdapter } from "frappe-builder-extension-sdk/vue";
import "./index.css";

builder.use(vueAdapter);

builder.popover.register({ component: () => import("./Popover.vue") });
builder.open.register({ kind: "popover", width: 420, height: 560 });

const openPopover = () =>
	builder.ui.openPopover({
		title: __LABEL_JSON__,
		width: 420,
		height: 560,
	});

builder.toolbar.register({
	name: __EXTENSION_SLUG_JSON__,
	region: "right",
	icon: "lucide-blocks",
	tooltip: __TOOLTIP_JSON__,
	action: openPopover,
});
