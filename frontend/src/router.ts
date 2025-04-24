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
		beforeEnter: validateVisit,
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
