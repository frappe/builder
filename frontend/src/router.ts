import { createResource } from "frappe-ui";
import { ref } from "vue";
import { NavigationGuardNext, RouteLocationNormalized, createRouter, createWebHistory } from "vue-router";
import { __ } from "./translation";
import { editorDemo } from "./utils/editorDemo";
import { personaSurveyRedirect } from "./utils/personaSurvey";

let hasPermission: null | boolean = null;
let sessionUser = ref("Guest");

function validatePermission(next: NavigationGuardNext) {
	if (hasPermission) {
		next();
	} else {
		alert(__("You do not have permission to access this page"));
		if (isUserLoggedIn()) {
			window.location.href = "/app";
		} else {
			window.location.href = "/login?redirect-to=/builder";
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

// before the dashboard renders, so a user who owes the persona survey never sees the dashboard first
const personaSurveyFirst = (to: RouteLocationNormalized) => personaSurveyRedirect(to, sessionUser.value);

function isUserLoggedIn() {
	return document.cookie.includes("user_id") && !document.cookie.includes("user_id=Guest");
}

function getSessionUser() {
	return decodeURIComponent(document.cookie.split("user_id=")[1].split(";")[0]) || "Guest";
}

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
		beforeEnter: [validateVisit, personaSurveyFirst],
		component: () => import("@/pages/PageBuilderDashboard.vue"),
	},
	{
		path: "/dashboard/:item/:path(.*)*",
		name: "dashboard-item",
		// a dashboard view is the dashboard too, so a user who owes the survey goes there first
		beforeEnter: [validateVisit, personaSurveyFirst],
		component: () => import("@/pages/PageBuilderDashboard.vue"),
	},
	{
		path: "/page/:pageId",
		name: "builder",
		beforeEnter: validateVisit,
		component: () => import("@/pages/PageBuilder.vue"),
	},
	{
		path: "/page/:pageId/preview",
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
