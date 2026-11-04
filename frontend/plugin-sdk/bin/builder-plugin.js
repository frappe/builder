#!/usr/bin/env node

import { createPlugin, promptForCreateOptions } from "../create.js";
import { packagePlugin } from "../package.js";

const usage = `Usage:
  builder-plugin create [directory] [options]
  builder-plugin package [root] [options]

Create options:
  --publisher <publisher>        Publisher, ideally a GitHub username
  --name <display name>          Human-facing plugin name
  --description <description>    Optional description
  --builder-url <url>            Origin that serves Builder
  --copyright-holder <name>      Person or organization for the MIT license

Package options:
  --dist <directory>    Built files relative to root (default: dist)
  --output <directory>  Package output relative to root (default: release)
  --tag <tag>           Require v<version> to match the manifest

General options:
  --help                Show this help`;

const readOptions = (arguments_, fields) => {
	const options = {};
	for (let index = 0; index < arguments_.length; index += 1) {
		const argument = arguments_[index];
		if (argument === "--help") return { help: true };
		if (!argument.startsWith("--") && !options.positional) options.positional = argument;
		else {
			const field = fields[argument];
			if (!field || arguments_[index + 1] === undefined)
				throw new Error(`Unknown or incomplete option "${argument}"\n\n${usage}`);
			options[field] = arguments_[index + 1];
			index += 1;
		}
	}
	return options;
};

const readArguments = (arguments_) => {
	const [command, ...rest] = arguments_;
	if (!command || command === "--help") return { help: true };
	if (command === "package") {
		const { positional, ...options } = readOptions(rest, {
			"--dist": "dist",
			"--output": "output",
			"--tag": "tag",
		});
		return { command, ...options, root: positional };
	}
	if (command === "create") {
		const { positional, ...options } = readOptions(rest, {
			"--publisher": "publisher",
			"--name": "name",
			"--description": "description",
			"--builder-url": "builderUrl",
			"--copyright-holder": "copyrightHolder",
		});
		return { command, ...options, directory: positional };
	}
	throw new Error(`Unknown command "${command}"\n\n${usage}`);
};

try {
	const options = readArguments(process.argv.slice(2));
	if (options.help) console.log(usage);
	else if (options.command === "package") {
		const packaged = packagePlugin(options);
		console.log(`Created ${packaged.path}`);
		console.log(`SHA-256 ${packaged.sha256}`);
		console.log(`Size ${packaged.size} bytes`);
	} else {
		const created = createPlugin(await promptForCreateOptions(options));
		console.log(`\nCreated ${created.pluginId} in ${created.directory}`);
		console.log("\nNext steps:");
		console.log(`  cd ${JSON.stringify(created.directory)}`);
		console.log("  npm install");
		console.log("  npm run dev");
	}
} catch (error) {
	console.error(error.message);
	process.exitCode = 1;
}
