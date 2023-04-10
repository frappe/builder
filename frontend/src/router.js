import { createRouter, createWebHistory } from "vue-router";

const routes = [
	{
		path: "/",
		redirect: "builder",
	},
	{
		path: "/home",
		name: "Home",
		component: () => import("@/pages/PageBuilderLanding.vue"),
	},
	{
		path: "/builder",
		name: "Page Builder",
		component: () => import("@/pages/PageBuilder.vue"),
	},
];

const router = createRouter({
	history: createWebHistory("/"),
	routes,
});

export default router;
