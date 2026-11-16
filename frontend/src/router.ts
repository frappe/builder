import { createResource } from "frappe-ui";
import { ref } from "vue";
import { NavigationGuardNext, RouteLocationNormalized, createRouter, createWebHistory } from "vue-router";
import { __ } from "./translation";
import { editorDemo } from "./utils/editorDemo";
import { appURL, isMounted, loginURL, shortEditorURLs } from "./utils/frappePage";

let hasPermission: null | boolean = null;
let sessionUser = ref("Guest");

function validatePermission(next: NavigationGuardNext) {
	if (hasPermission) {
		next();
	} else {
		alert(__("You do not have permission to access this page"));
		if (isUserLoggedIn()) {
			// a frappe.page site has no Desk: the user's sites, listed even when there is only this one
			window.location.href = isMounted ? appURL("/sites?all=1") : "/app";
		} else {
			window.location.href = loginURL();
		}
	}
}

const validateVisit = async function (
	to: RouteLocationNormalized,
	from: RouteLocationNormalized,
	next: NavigationGuardNext,
) {
	if (isUserLoggedIn()) {
		sessionUser.value = getSessionUser();
		if (hasPermission === null) {
			try {
				const response = await createResource({
					url: "frappe.client.has_permission",
				}).submit({
					doctype: "Builder Page",
					docname: "",
					perm_type: "write",
				});
				hasPermission = response.has_permission;
				return validatePermission(next);
			} catch (e) {
				hasPermission = false;
				return validatePermission(next);
			}
		}
	}
	return validatePermission(next);
};

function isUserLoggedIn() {
	return document.cookie.includes("user_id") && !document.cookie.includes("user_id=Guest");
}

function getSessionUser() {
	return decodeURIComponent(document.cookie.split("user_id=")[1].split(";")[0]) || "Guest";
}

// frappe.page shows a page at frappe.page/<sub>/<page>, without Builder's /page segment
const pagePath = shortEditorURLs ? "/:pageId" : "/page/:pageId";

const routes = [
	{
		path: "/home",
		beforeEnter: validateVisit,
		redirect: "/",
	},
	{
		path: "/page",
		beforeEnter: validateVisit,
		redirect: "/home",
	},
	{
		path: "/",
		name: "home",
		beforeEnter: validateVisit,
		component: () => import("@/pages/PageBuilderDashboard.vue"),
	},
	{
		path: pagePath,
		name: "builder",
		beforeEnter: validateVisit,
		component: () => import("@/pages/PageBuilder.vue"),
	},
	{
		path: `${pagePath}/preview`,
		name: "preview",
		beforeEnter: validateVisit,
		component: () => import("@/pages/PagePreview.vue"),
	},
	{
		path: "/persona-survey",
		name: "persona-survey",
		beforeEnter: validateVisit,
		component: () => import("@/pages/PagePersonaSurvey.vue"),
	},
	// older /page/<page> links keep working under short addresses
	...(shortEditorURLs
		? [
				{ path: "/page/:pageId", redirect: (to) => ({ name: "builder", params: to.params, query: to.query }) },
				{ path: "/page/:pageId/preview", redirect: (to) => ({ name: "preview", params: to.params, query: to.query }) },
			]
		: []),
];

declare global {
	interface Window {
		builder_path: string;
	}
}

let builder_path = window.builder_path || "/builder";
if (builder_path.startsWith("{{")) {
	builder_path = "/builder";
}
const router = createRouter({
	history: createWebHistory(builder_path),
	// named "builder" so the editor's own links resolve, but only to the demo's page
	routes: editorDemo
		? [{ path: "/demo/:pageId", name: "builder", component: () => import("@/pages/PageBuilder.vue") }]
		: routes,
});

if (editorDemo) router.beforeEach((to) => to.params.pageId === editorDemo?.page.name);

export { sessionUser };
export default router;
