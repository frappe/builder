import { createRouter, createWebHistory } from "vue-router";

const routes = [
	{
		path: "/",
		redirect: "/home",
	},
	{
		path: "/builder",
		redirect: "/builder/new",
	},
	{
		path: "/home",
		name: "home",
		component: () => import("@/pages/PageBuilderLanding.vue"),
	},
	{
		path: "/builder/:pageId",
		name: "builder",
		component: () => import("@/pages/PageBuilder.vue"),
	},
];

const router = createRouter({
	history: createWebHistory("/"),
	routes,
});

export default router;
