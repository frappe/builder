import { createRouter, createWebHistory } from "vue-router";

// Hack, TODO: Check authentication
const validateVisit = function(to, from, next) {
	if (document.cookie.includes("user_id") && !document.cookie.includes("user_id=Guest")) {
		next()
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
		path: "/builder",
		beforeEnter: validateVisit,
		redirect: "/builder/new",
	},
	{
		path: "/home",
		name: "home",
		beforeEnter: validateVisit,
		component: () => import("@/pages/PageBuilderLanding.vue"),
	},
	{
		path: "/builder/:pageId",
		name: "builder",
		beforeEnter: validateVisit,
		component: () => import("@/pages/PageBuilder.vue"),
	}
];



const router = createRouter({
	history: createWebHistory("/p"),
	routes,
});

export default router;
