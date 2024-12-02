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

router.beforeEach((to, from, next) => {
	if (to.path !== "/" && to.path.endsWith("/")) {
		const path = to.path.slice(0, -1);
		next({ path, query: to.query, hash: to.hash }); // Redirect to the path without the slash
	} else {
		next();
	}
});

export { sessionUser };
export default router;
