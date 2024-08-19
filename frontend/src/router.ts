import { createResource } from "frappe-ui";
import { ref } from "vue";
import { NavigationGuardNext, RouteLocationNormalized, createRouter, createWebHistory } from "vue-router";

let hasPermission: null | boolean = null;
let sessionUser = ref("Guest");

function validatePermission(next: NavigationGuardNext) {
	if (hasPermission) {
		next();
	} else {
		alert("You do not have permission to access this page");
		window.location.href = "/login";
	}
}

const validateVisit = function (
	to: RouteLocationNormalized,
	from: RouteLocationNormalized,
	next: NavigationGuardNext,
) {
	if (document.cookie.includes("user_id") && !document.cookie.includes("user_id=Guest")) {
		sessionUser.value = decodeURIComponent(document.cookie.split("user_id=")[1].split(";")[0]);
		if (hasPermission === null) {
			createResource({
				url: "frappe.client.has_permission",
				caches: "has_permission",
			})
				.submit({
					doctype: "Builder Page",
					docname: null,
					perm_type: "write",
				})
				.then((res: { has_permission: boolean }) => {
					hasPermission = res.has_permission;
					validatePermission(next);
				})
				.catch(() => {
					hasPermission = false;
					validatePermission(next);
				});
		} else {
			validatePermission(next);
		}
	} else {
		validatePermission(next);
	}
};

const routes = [
	{
		path: "/",
		beforeEnter: validateVisit,
		redirect: "/home",
	},
	{
		path: "/page",
		beforeEnter: validateVisit,
		redirect: "/home",
	},
	{
		path: "/home",
		name: "home",
		beforeEnter: validateVisit,
		component: () => import("@/pages/PageBuilderLanding.vue"),
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
		path: "/page/:pageId/settings",
		name: "settings",
		beforeEnter: validateVisit,
		component: () => import("@/pages/PageSettings.vue"),
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
	routes,
});

export { sessionUser };
export default router;
