import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { addBuildScript, addPluginHook, createAppPlugin, findAppModule } from "./app.js";

let appRoot;
const read = (relative) => fs.readFileSync(path.join(appRoot, relative), "utf8");
const write = (relative, content) => {
	fs.mkdirSync(path.dirname(path.join(appRoot, relative)), { recursive: true });
	fs.writeFileSync(path.join(appRoot, relative), content);
};

beforeEach(() => {
	appRoot = fs.mkdtempSync(path.join(os.tmpdir(), "builder-app-"));
	write("my_app/hooks.py", 'app_name = "my_app"\n');
});
afterEach(() => fs.rmSync(appRoot, { recursive: true, force: true }));

describe("createAppPlugin", () => {
	const create = () =>
		createAppPlugin({
			app: appRoot,
			name: "SEO Tools",
			publisher: "acme",
			builderUrl: "http://builder.localhost:8000",
			copyrightHolder: "Acme",
		});

	it("writes the project into the app's source folder and declares it", () => {
		const created = create();

		expect(created.directory).toBe(path.join(appRoot, "my_app", "seo-tools"));
		expect(created.pluginId).toBe("acme/seo-tools");
		expect(fs.existsSync(path.join(created.directory, "manifest.json"))).toBe(true);
		expect(read("my_app/hooks.py")).toContain('builder_plugins = ["seo-tools"]');
		expect(JSON.parse(read("package.json")).scripts).toEqual({
			"build:seo-tools": "yarn --cwd my_app/seo-tools install && yarn --cwd my_app/seo-tools build",
			build: "yarn build:seo-tools",
		});
	});

	it("leaves out the git repository and the Hub release workflow", () => {
		const created = create();

		expect(fs.existsSync(path.join(created.directory, ".git"))).toBe(false);
		expect(fs.existsSync(path.join(created.directory, ".github"))).toBe(false);
	});
});

describe("findAppModule", () => {
	it("refuses a folder that is not a Frappe app", () => {
		fs.rmSync(path.join(appRoot, "my_app"), { recursive: true });
		expect(() => findAppModule(appRoot)).toThrow("is not a Frappe app");
	});
});

describe("addPluginHook", () => {
	it("adds the folder to an existing list once", () => {
		write("my_app/hooks.py", 'builder_plugins = ["seo"]\nother = 1\n');
		const hooks = path.join(appRoot, "my_app/hooks.py");

		addPluginHook(hooks, "forms");
		addPluginHook(hooks, "forms");

		expect(read("my_app/hooks.py")).toBe('builder_plugins = ["seo", "forms"]\nother = 1\n');
	});
});

describe("addBuildScript", () => {
	it("runs the plugin build after the app's own build, once", () => {
		write(
			"package.json",
			'{\n  "name": "my_app",\n  "scripts": { "build": "cd frontend && yarn build" }\n}\n',
		);
		const packagePath = path.join(appRoot, "package.json");

		addBuildScript(packagePath, "my_app/seo", "seo");
		addBuildScript(packagePath, "my_app/seo", "seo");

		const source = read("package.json");
		expect(JSON.parse(source).scripts.build).toBe("cd frontend && yarn build && yarn build:seo");
		expect(source).toContain('\n  "name"');
	});
});
