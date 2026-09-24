/** Create a publishable Vue extension project. */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import readline from "node:readline/promises";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const TEMPLATE_ROOT = fileURLToPath(new URL("./templates/create", import.meta.url));
const RELEASE_WORKFLOW = fileURLToPath(new URL("./templates/github/workflows/release.yml", import.meta.url));
const GENERIC_DESCRIPTION = "A Frappe Builder extension.";
const PLAIN_TEXT = /^[^<>\u0000-\u001f\u007f]*$/;

const fail = (message) => {
	throw new Error(`[builder] ${message}`);
};

export const slugify = (value) =>
	value
		.normalize("NFKD")
		.replace(/[\u0300-\u036f]/g, "")
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-+|-+$/g, "");

const plainText = (value, label, maximum) => {
	if (typeof value !== "string") fail(`${label} is required`);
	const trimmed = value.trim();
	if (!trimmed || [...trimmed].length > maximum || !PLAIN_TEXT.test(trimmed)) {
		fail(`${label} must contain 1 through ${maximum} plain text characters`);
	}
	return trimmed;
};

const builderOrigin = (value) => {
	if (typeof value !== "string") fail("Builder URL is required");
	let url;
	try {
		url = new URL(value.trim());
	} catch {
		fail("Builder URL must be a valid URL");
	}
	if (!["http:", "https:"].includes(url.protocol) || url.pathname !== "/" || url.search || url.hash) {
		fail("Builder URL must be an HTTP origin without a path, query, or fragment");
	}
	return url.origin;
};

const render = (source, values) =>
	Object.entries(values).reduce((result, [name, value]) => result.replaceAll(`__${name}__`, value), source);

const outputName = (relative) => {
	const parts = relative.split(path.sep);
	if (parts[0] === "github") parts[0] = ".github";
	if (parts.at(-1) === "gitignore") parts[parts.length - 1] = ".gitignore";
	return parts.join(path.sep);
};

const templateFiles = (directory = TEMPLATE_ROOT) =>
	fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
		const file = path.join(directory, entry.name);
		return entry.isDirectory() ? templateFiles(file) : [file];
	});

const assertEmptyDirectory = (directory) => {
	const entry = fs.statSync(directory, { throwIfNoEntry: false });
	if (entry && !entry.isDirectory()) fail(`target exists and is not a directory: ${directory}`);
	if (entry && fs.readdirSync(directory).length) fail(`target directory is not empty: ${directory}`);
};

const initializeRepository = (directory) => {
	const result = spawnSync("git", ["init"], { cwd: directory, encoding: "utf8" });
	if (result.status !== 0) fail(`could not initialize Git: ${result.stderr.trim() || "git init failed"}`);
};

export const createExtension = ({
	directory,
	name,
	publisher,
	description = "",
	builderUrl,
	copyrightHolder,
	cwd = process.cwd(),
	initializeGit = true,
} = {}) => {
	const label = plainText(name, "Extension name", 80);
	const extensionSlug = slugify(label);
	const publisherSlug = slugify(plainText(publisher, "Publisher", 80));
	if (!extensionSlug) fail("Extension name must contain at least one letter or number");
	if (!publisherSlug) fail("Publisher must contain at least one letter or number");

	const projectDescription = description.trim()
		? plainText(description, "Description", 240)
		: GENERIC_DESCRIPTION;
	const holder = plainText(copyrightHolder, "Copyright holder", 160);
	const origin = builderOrigin(builderUrl);
	const target = path.resolve(cwd, directory || extensionSlug);
	assertEmptyDirectory(target);

	const values = {
		BUILDER_URL: JSON.stringify(origin),
		COPYRIGHT_HOLDER: holder,
		COPYRIGHT_HOLDER_JSON: JSON.stringify(holder),
		DESCRIPTION: projectDescription,
		DESCRIPTION_JSON: JSON.stringify(projectDescription),
		EXTENSION_ID_JSON: JSON.stringify(`${publisherSlug}/${extensionSlug}`),
		EXTENSION_SLUG: extensionSlug,
		EXTENSION_SLUG_JSON: JSON.stringify(extensionSlug),
		LABEL: label,
		LABEL_JSON: JSON.stringify(label),
		PACKAGE_NAME_JSON: JSON.stringify(`@${publisherSlug}/${extensionSlug}`),
		PUBLISHER: publisherSlug,
		TOOLTIP_JSON: JSON.stringify("Open " + label),
		YEAR: String(new Date().getFullYear()),
	};

	fs.mkdirSync(target, { recursive: true });
	for (const template of templateFiles()) {
		const relative = path.relative(TEMPLATE_ROOT, template);
		const destination = path.join(target, outputName(relative));
		fs.mkdirSync(path.dirname(destination), { recursive: true });
		fs.writeFileSync(destination, render(fs.readFileSync(template, "utf8"), values));
	}
	const workflow = path.join(target, ".github/workflows/release.yml");
	fs.mkdirSync(path.dirname(workflow), { recursive: true });
	fs.copyFileSync(RELEASE_WORKFLOW, workflow);
	if (initializeGit) initializeRepository(target);

	return { directory: target, extensionId: `${publisherSlug}/${extensionSlug}` };
};

const requiredAnswer = async (terminal, current, prompt) => {
	if (current !== undefined) return current;
	if (!process.stdin.isTTY) fail(`missing value for ${prompt}`);
	return terminal.question(`${prompt}: `);
};

export const promptForCreateOptions = async (options) => {
	const terminal = readline.createInterface({ input: process.stdin, output: process.stdout });
	try {
		return {
			...options,
			name: await requiredAnswer(terminal, options.name, "Extension name"),
			publisher: await requiredAnswer(
				terminal,
				options.publisher,
				"Publisher (ideally your GitHub username)",
			),
			description: await requiredAnswer(
				terminal,
				options.description,
				`Description (optional; defaults to \"${GENERIC_DESCRIPTION}\")`,
			),
			builderUrl: await requiredAnswer(terminal, options.builderUrl, "Builder URL"),
			copyrightHolder: await requiredAnswer(
				terminal,
				options.copyrightHolder,
				"Copyright holder (person or organization)",
			),
		};
	} finally {
		terminal.close();
	}
};
