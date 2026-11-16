import { useFrappePageSite, type SiteBrief } from "@/data/frappePageSite";
import { __ } from "@/translation";
import { appURL, fp, isMounted, openSiteURL } from "@/utils/frappePage";
import type { DropdownGroupOption } from "frappe-ui";
import { computed, h } from "vue";

/**
 * The app menu's frappe.page part, shared by the dashboard sidebar and the page editor: a Sites submenu (the
 * user's sites, the current one checked, then New Site), so a long list never pushes the rest of the menu down,
 * and Sign Out. Empty for stock Builder.
 */
export function useFrappePageMenu() {
	const { session, signOut } = useFrappePageSite();

	const sitesGroup = computed<DropdownGroupOption[]>(() => {
		if (!isMounted) return [];
		const sites = session.value?.sites ?? [];
		return [
			{
				group: __("Sites"),
				hideLabel: true,
				options: [
					{
						label: __("Sites"),
						icon: "lucide-globe",
						submenu: [
							...(sites.length ? [{ group: __("Your sites"), options: sites.map(siteOption) }] : []),
							{
								group: __("New"),
								hideLabel: true,
								options: [
									{
										label: __("New Site"),
										icon: "lucide-plus",
										onClick: () => (window.location.href = appURL("/onboarding")),
									},
								],
							},
						],
					},
				],
			},
		];
	});

	const accountGroup = computed<DropdownGroupOption[]>(() =>
		isMounted
			? [
					{
						group: __("Account"),
						hideLabel: true,
						options: [{ label: __("Sign Out"), icon: "lucide-log-out", onClick: () => signOut() }],
					},
				]
			: [],
	);

	return { sitesGroup, accountGroup };
}

const roleLabels: Record<SiteBrief["role"], string> = {
	Owner: __("Owner"),
	Admin: __("Admin"),
	Editor: __("Editor"),
};

function siteOption(site: SiteBrief) {
	const current = site.subdomain === fp.site_subdomain;
	return {
		label: site.subdomain,
		description: site.status === "Active" ? roleLabels[site.role] : __("Setting up…"),
		icon: "lucide-globe",
		// the check marks the site this editor is on; picking it does nothing
		slots: current
			? { suffix: () => h("span", { class: "lucide-check ml-auto size-4 shrink-0 text-ink-gray-7" }) }
			: undefined,
		onClick: () => {
			if (!current) window.location.href = openSiteURL(site.subdomain);
		},
	};
}
