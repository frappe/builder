import { createResource } from "frappe-ui";
import { createRouter, createWebHistory } from "vue-router";

// Hack, TODO: Check authentication
let hasPermission: null | boolean = null;

function validatePermission(next: CallableFunction) {
	if (hasPermission) {
		next();
	} else {
		alert("You do not have permission to access this page");
		window.location.href = "/login";
	}
}

const validateVisit = function (to, from, next) {
	if (document.cookie.includes("user_id") && !document.cookie.includes("user_id=Guest")) {
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
				.then((res: any) => {
					hasPermission = res.has_permission as boolean;
					validatePermission(next);
				});
		} else {
			validatePermission(next);
		}
	} else {
		window.location.href = "/login";
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
];

const router = createRouter({
	history: createWebHistory("/builder"),
	routes,
});

export default router;
