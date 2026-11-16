/** Add a Builder plugin project to an existing Frappe app, so the app ships it. */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { createPlugin, slugify } from "./create.js";

const HOOKS_FILE = "hooks.py";
/** Under the module's `public` folder, so the build ships and is served as the app's other assets are. */
const BUILDS_FOLDER = "public/builder_plugins";
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
	// the list is written again on one line, so a comment in it would swallow the items after it
	if (match[1].includes("#")) fail(`add ${JSON.stringify(folder)} to builder_plugins in ${hooksPath}`);
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

/** Vite writes the build outside the project, so it must also be told to empty the folder first. */
export const setBuildFolder = (configPath, folder) => {
	const source = fs.readFileSync(configPath, "utf8");
	const build = `\tbuild: { outDir: "../${BUILDS_FOLDER}/${folder}", emptyOutDir: true },\n`;
	fs.writeFileSync(configPath, source.replace("\tplugins: [", `${build}\tplugins: [`));
};

/** The build is not committed. Prebuilt asset archives carry the ignored files under `public`. */
export const ignoreBuilds = (gitignorePath, module) => {
	const line = `${module}/${BUILDS_FOLDER}/`;
	const source = fs.existsSync(gitignorePath) ? fs.readFileSync(gitignorePath, "utf8") : "";
	if (source.split("\n").includes(line)) return;
	const separator = source && !source.endsWith("\n") ? "\n" : "";
	fs.writeFileSync(gitignorePath, `${source}${separator}${line}\n`);
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
	setBuildFolder(path.join(created.directory, "vite.config.ts"), folder);
	ignoreBuilds(path.join(appRoot, ".gitignore"), module);
	addPluginHook(path.join(appRoot, module, HOOKS_FILE), folder);
	addBuildScript(path.join(appRoot, "package.json"), `${module}/${folder}`, folder);
	return { ...created, app: appRoot, folder };
};
