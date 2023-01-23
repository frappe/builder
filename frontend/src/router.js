import { createRouter, createWebHistory } from "vue-router";

const routes = [
	{
		path: "/",
		name: "Page Builder",
		component: () => import("@/pages/PageBuilder.vue"),
	},
];

const router = createRouter({
	history: createWebHistory("/frontend"),
	routes,
});

export default router;
