/** Add a Builder plugin project to an existing Frappe app, so the app ships it. */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { createPlugin, slugify } from "./create.js";

const HOOKS_FILE = "hooks.py";
const HOOK_PATTERN = /^builder_plugins\s*=\s*\[([^\]]*)\]/m;

const fail = (message) => {
	throw new Error(`[builder] ${message}`);
};

/** The app's source folder: the one folder in the app root that holds hooks.py. */
export const findAppModule = (appRoot) => {
	const modules = fs
		.readdirSync(appRoot, { withFileTypes: true })
		.filter((entry) => entry.isDirectory() && fs.existsSync(path.join(appRoot, entry.name, HOOKS_FILE)));
	if (modules.length !== 1) fail(`${appRoot} is not a Frappe app: expected one folder with ${HOOKS_FILE}`);
	return modules[0].name;
};

export const addPluginHook = (hooksPath, folder) => {
	const source = fs.readFileSync(hooksPath, "utf8");
	const match = source.match(HOOK_PATTERN);
	if (!match) {
		const separator = source.endsWith("\n") ? "\n" : "\n\n";
		fs.writeFileSync(hooksPath, `${source}${separator}builder_plugins = [${JSON.stringify(folder)}]\n`);
		return;
	}
	if (match[1].includes(JSON.stringify(folder))) return;
	const items = match[1].trim().replace(/,$/, "");
	const list = items ? `${items}, ${JSON.stringify(folder)}` : JSON.stringify(folder);
	fs.writeFileSync(hooksPath, source.replace(HOOK_PATTERN, `builder_plugins = [${list}]`));
};

/** bench build runs the app root's `yarn build`, and installs only the root's dependencies. */
export const addBuildScript = (packagePath, projectPath, folder) => {
	const exists = fs.existsSync(packagePath);
	const source = exists ? fs.readFileSync(packagePath, "utf8") : "";
	const manifest = exists ? JSON.parse(source) : { private: true };
	const scripts = (manifest.scripts ??= {});
	const script = `build:${folder}`;

	scripts[script] = `yarn --cwd ${projectPath} install && yarn --cwd ${projectPath} build`;
	if (!scripts.build) scripts.build = `yarn ${script}`;
	else if (!scripts.build.includes(script)) scripts.build = `${scripts.build} && yarn ${script}`;

	const indent = source.match(/^[ \t]+(?=")/m)?.[0] ?? "\t";
	fs.writeFileSync(packagePath, `${JSON.stringify(manifest, null, indent)}\n`);
};

export const createAppPlugin = ({ app, directory, cwd = process.cwd(), ...options }) => {
	const appRoot = path.resolve(cwd, app);
	const module = findAppModule(appRoot);
	const folder = directory || slugify(options.name ?? "");
	if (!folder || folder.includes("/") || folder.includes(path.sep)) fail(`invalid plugin folder: ${folder}`);

	const created = createPlugin({
		...options,
		directory: path.join(appRoot, module, folder),
		initializeGit: false,
		releaseWorkflow: false,
	});
	addPluginHook(path.join(appRoot, module, HOOKS_FILE), folder);
	addBuildScript(path.join(appRoot, "package.json"), `${module}/${folder}`, folder);
	return { ...created, app: appRoot, folder };
};
