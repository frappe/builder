import { defineConfig } from "cypress";

export default defineConfig({
	projectId: "jvejd7",
	e2e: {
		baseUrl: "http://builder.test:8000",
	},
	env: {
		adminPassword: "admin",
	},
	retries: {
		runMode: 2,
		openMode: 0,
	},
});
