import type Block from "@/block";
import AttributePropertyControl from "@/components/Controls/AttributePropertyControl.vue";
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import { linkablePages } from "@/data/allWebPages";
import useCanvasStore from "@/stores/canvasStore";
import { BuilderPage } from "@/types/doctypes";
import blockController from "@/utils/blockController";
import { Switch } from "frappe-ui";
import { computed } from "vue";
import { __ } from "@/translation";

const getSectionIds = (block: Block): string[] => {
	const id = block.getId();
	return [...(id ? [String(id)] : []), ...block.getChildren().flatMap(getSectionIds)];
};

const toOption = (value: string) => ({ label: value, value });

const getSectionOptions = () => {
	const rootBlock = useCanvasStore().getRootBlock();
	return [...new Set(rootBlock ? getSectionIds(rootBlock) : [])].map((id) => toOption(`#${id}`));
};

const getPageOptions = () =>
	(linkablePages.data || [])
		.filter((page: BuilderPage) => page.route)
		.map((page: BuilderPage) => toOption(`/${page.route}`));

const getHref = () => String(blockController.getAttribute("href") || "");

const isSectionLink = () => getHref().startsWith("#");

const scrollBehaviorOptions = [
	{ label: __("Smooth"), value: "smooth" },
	{ label: __("Instant"), value: "instant" },
];

const setHref = async (val: string) => {
	if (!val?.startsWith("#")) {
		blockController.removeAttribute("data-scroll-behavior");
	}
	if (val && !blockController.isLink()) {
		await blockController.convertToLink();
	}
	if (!val && blockController.isLink()) {
		blockController.unsetLink();
	} else {
		blockController.setAttribute("href", val);
	}
};

const linkSectionProperties = [
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				label: __("Link To"),
				propertyKey: "href",
				component: Autocomplete,
				options: getPageOptions(),
				// pages can be added, deleted or given a new route while the editor stays open
				onFocus: () => linkablePages.reload(),
				showInputAsOption: true,
				placeholder: __("URL or /page"),
				allowDynamicValue: true,
				// #section links are edited in Scroll To
				getModelValue: () => (isSectionLink() ? "" : getHref()),
				setModelValue: setHref,
			};
		},
		searchKeyWords: "Link, Href, URL",
		events: {
			setDynamicValue: () => {
				if (!blockController.isLink()) {
					blockController.convertToLink();
				}
			},
			clearDynamicValue: () => {
				if (blockController.isLink() && !blockController.getAttribute("href")) {
					blockController.unsetLink();
				}
			},
		},
	},
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				label: __("Scroll To"),
				propertyKey: "href",
				component: Autocomplete,
				options: getSectionOptions(),
				placeholder: __("#section"),
				getModelValue: () => (isSectionLink() ? getHref() : ""),
				setModelValue: (val: string) => setHref(val && `#${val.replace(/^#/, "")}`),
			};
		},
		searchKeyWords: "Scroll To, Section, Anchor, Link, ID",
	},
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				label: __("Scrolling"),
				type: "select",
				propertyKey: "data-scroll-behavior",
				allowDynamicValue: false,
				getModelValue: () => blockController.getAttribute("data-scroll-behavior") || "smooth",
				setModelValue: (val: string) => {
					if (val === "smooth") {
						blockController.removeAttribute("data-scroll-behavior");
					} else {
						blockController.setAttribute("data-scroll-behavior", val);
					}
				},
				options: scrollBehaviorOptions,
			};
		},
		searchKeyWords: "Scroll, Scrolling, Smooth, Instant, Scroll Behavior",
		condition: isSectionLink,
	},
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				label: __("Opens in"),
				type: "select",
				propertyKey: "target",
				allowDynamicValue: false,
				getModelValue: () => blockController.getAttribute("target") || "_self",
				setModelValue: (val: string) => {
					if (val === "_self") {
						blockController.removeAttribute("target");
					} else {
						blockController.setAttribute("target", val);
					}
				},
				options: [
					{
						value: "_self",
						label: __("Same Tab"),
					},
					{
						value: "_blank",
						label: __("New Tab"),
					},
				],
			};
		},
		searchKeyWords: "Link, Target, Opens in, OpensIn, Opens In, New Tab",
		condition: () => blockController.getAttribute("href"),
	},
	{
		component: Switch,
		getProps: () => {
			return {
				label: __("Track Clicks"),
				size: "sm",
				class: "[&_label]:text-xs [&_label]:text-ink-gray-6 [&_label]:font-normal",
				modelValue: blockController.isClickTrackingEnabled(),
			};
		},
		searchKeyWords: "Track, Clicks, Tracking, Analytics, CTR, Click Tracking",
		events: {
			"update:modelValue": (val: boolean) => blockController.toggleClickTracking(val),
		},
	},
];

export default {
	name: __("Link"),
	properties: linkSectionProperties,
	collapsed: computed(() => !blockController.isLink()),
	condition: () =>
		!blockController.multipleBlocksSelected() &&
		!blockController.getSelectedBlocks()[0].parentBlock?.isLink() &&
		!(blockController.isHTML() && !blockController.isSVG()),
};
