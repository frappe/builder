const { defineConfig } = require("cypress");

module.exports = defineConfig({
  projectId: "jvejd7",
	e2e: {
		baseUrl: "http://builder.test:8000",
		adminPassword: "admin",
	},
	retries: {
		runMode: 2,
		openMode: 0,
	},
});
