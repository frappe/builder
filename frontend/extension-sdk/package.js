/** Build and validate the immutable archive an extension author publishes. */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { isDeepStrictEqual } from "node:util";
import zlib from "node:zlib";
import { parseJson, validateManifest } from "./src/protocol.js";

export const MAX_PACKAGE_BYTES = 10 * 1024 * 1024;

export const ALLOWED_SUFFIXES = new Set([".js", ".json", ".svg"]);

const fail = (message) => {
	throw new Error(`[builder] ${message}`);
};

const requiredFile = (root, name) => {
	const file = path.join(root, name);
	if (!fs.statSync(file, { throwIfNoEntry: false })?.isFile()) fail(`repository has no root ${name}`);
	return file;
};

const readJson = (file) => parseJson(path.basename(file), fs.readFileSync(file, "utf8"));

const resolveProjectPath = (root, value, label) => {
	const resolved = path.resolve(root, value);
	const relative = path.relative(root, resolved);
	if (relative.startsWith("..") || path.isAbsolute(relative))
		fail(`${label} must stay inside the project root`);
	return resolved;
};

export const validateRepository = (root) => {
	const manifest = validateManifest(readJson(requiredFile(root, "manifest.json")));
	requiredFile(root, "README.md");
	requiredFile(root, "LICENSE");
	return manifest;
};

const packagePath = (root, file) => path.relative(root, file).split(path.sep).join("/");

const assertSafePath = (name) => {
	if (!name || name.includes("\0") || path.posix.isAbsolute(name)) fail(`unsafe package path "${name}"`);
	if (name.split("/").includes("..") || path.posix.normalize(name) !== name) {
		fail(`unsafe package path "${name}"`);
	}
};

const collectFiles = (root, directory = root, found = []) => {
	for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
		const file = path.join(directory, entry.name);
		const name = packagePath(root, file);
		assertSafePath(name);
		if (entry.isSymbolicLink()) fail(`package entry "${name}" is a symbolic link`);
		if (entry.isDirectory()) collectFiles(root, file, found);
		else if (entry.isFile()) found.push({ name, data: fs.readFileSync(file) });
		else fail(`package entry "${name}" is not a regular file`);
	}
	return found;
};

export const validateSvg = (data, name) => {
	const svg = data.toString("utf8");
	if (!/<svg(?:\s|\/?>)/i.test(svg)) fail(`package icon "${name}" is not an SVG document`);
	if (/<(?:[a-z][\w.-]*:)?(?:script|foreignObject)\b/i.test(svg)) {
		fail(`package icon "${name}" contains an unsafe element`);
	}
	if (/\son[a-z][\w:-]*\s*=/i.test(svg)) fail(`package icon "${name}" contains an event attribute`);
	if (/<!DOCTYPE|<!ENTITY|<\?xml-stylesheet/i.test(svg))
		fail(`package icon "${name}" contains an external reference`);

	const references = svg.matchAll(/(?:href|xlink:href)\s*=\s*(["'])(.*?)\1/gi);
	if ([...references].some((match) => !match[2].startsWith("#"))) {
		fail(`package icon "${name}" contains an external reference`);
	}
	const urls = svg.matchAll(/url\(\s*(["']?)(.*?)\1\s*\)/gi);
	if ([...urls].some((match) => !match[2].startsWith("#"))) {
		fail(`package icon "${name}" contains an external reference`);
	}
	if (/@import/i.test(svg)) fail(`package icon "${name}" contains an external reference`);
};

export const validatePackageFiles = (root, manifest) => {
	if (!fs.statSync(root, { throwIfNoEntry: false })?.isDirectory())
		fail(`no built dist directory at ${root}`);
	const files = collectFiles(root).sort((left, right) => left.name.localeCompare(right.name));

	const names = new Set();
	const allowedNames = new Set(["manifest.json", "main.js", manifest.icon].filter(Boolean));
	for (const file of files) {
		const normalized = path.posix.normalize(file.name);
		if (names.has(normalized)) fail(`package contains duplicate path "${normalized}"`);
		names.add(normalized);
		if (!allowedNames.has(file.name)) fail(`package contains unexpected file "${file.name}"`);
		if (!ALLOWED_SUFFIXES.has(path.posix.extname(file.name))) {
			fail(`package entry "${file.name}" uses an unsupported suffix`);
		}
	}

	for (const required of ["manifest.json", "main.js"]) {
		if (!names.has(required)) fail(`package has no root ${required}`);
	}
	if (manifest.icon) {
		if (!names.has(manifest.icon)) fail(`package has no manifest icon "${manifest.icon}"`);
		validateSvg(files.find((file) => file.name === manifest.icon).data, manifest.icon);
	}
	return files;
};

const CRC_TABLE = Array.from({ length: 256 }, (_, index) => {
	let value = index;
	for (let bit = 0; bit < 8; bit += 1) value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
	return value >>> 0;
});

const crc32 = (data) => {
	let crc = 0xffffffff;
	for (const byte of data) crc = CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
	return (crc ^ 0xffffffff) >>> 0;
};

const localHeader = (name, data, compressed) => {
	const header = Buffer.alloc(30);
	header.writeUInt32LE(0x04034b50, 0);
	header.writeUInt16LE(20, 4);
	header.writeUInt16LE(0x0800, 6);
	header.writeUInt16LE(8, 8);
	header.writeUInt16LE(0x21, 12);
	header.writeUInt32LE(crc32(data), 14);
	header.writeUInt32LE(compressed.length, 18);
	header.writeUInt32LE(data.length, 22);
	header.writeUInt16LE(name.length, 26);
	return header;
};

const centralHeader = (name, data, compressed, offset) => {
	const header = Buffer.alloc(46);
	header.writeUInt32LE(0x02014b50, 0);
	header.writeUInt16LE(0x0314, 4);
	header.writeUInt16LE(20, 6);
	header.writeUInt16LE(0x0800, 8);
	header.writeUInt16LE(8, 10);
	header.writeUInt16LE(0x21, 14);
	header.writeUInt32LE(crc32(data), 16);
	header.writeUInt32LE(compressed.length, 20);
	header.writeUInt32LE(data.length, 24);
	header.writeUInt16LE(name.length, 28);
	header.writeUInt32LE((0o100644 << 16) >>> 0, 38);
	header.writeUInt32LE(offset, 42);
	return header;
};

export const makeZip = (files) => {
	const localParts = [];
	const centralParts = [];
	let offset = 0;

	for (const file of files) {
		const name = Buffer.from(file.name);
		const compressed = zlib.deflateRawSync(file.data, { level: 9 });
		const local = localHeader(name, file.data, compressed);
		localParts.push(local, name, compressed);
		centralParts.push(centralHeader(name, file.data, compressed, offset), name);
		offset += local.length + name.length + compressed.length;
	}

	const central = Buffer.concat(centralParts);
	const end = Buffer.alloc(22);
	end.writeUInt32LE(0x06054b50, 0);
	end.writeUInt16LE(files.length, 8);
	end.writeUInt16LE(files.length, 10);
	end.writeUInt32LE(central.length, 12);
	end.writeUInt32LE(offset, 16);
	return Buffer.concat([...localParts, central, end]);
};

export const packageExtension = ({ root = process.cwd(), dist = "dist", output = "release", tag } = {}) => {
	const projectRoot = path.resolve(root);
	const manifest = validateRepository(projectRoot);
	const releaseTag = `v${manifest.version}`;
	if (tag !== undefined && tag !== releaseTag) {
		fail(`release tag "${tag}" must equal "${releaseTag}" for manifest version "${manifest.version}"`);
	}

	const distRoot = resolveProjectPath(projectRoot, dist, "dist directory");
	if (fs.lstatSync(distRoot, { throwIfNoEntry: false })?.isSymbolicLink()) {
		fail("dist directory must not be a symbolic link");
	}
	const builtManifest = validateManifest(
		readJson(requiredFile(distRoot, "manifest.json")),
		"dist/manifest.json",
	);
	if (!isDeepStrictEqual(builtManifest, manifest))
		fail("dist/manifest.json does not match the repository manifest");

	const archive = makeZip(validatePackageFiles(distRoot, manifest));
	if (archive.length > MAX_PACKAGE_BYTES) fail(`package is larger than ${MAX_PACKAGE_BYTES} bytes`);

	const outputRoot = resolveProjectPath(projectRoot, output, "output directory");
	fs.mkdirSync(outputRoot, { recursive: true });
	const filename = `${manifest.name.replace("/", "-")}-${manifest.version}.builderext`;
	const destination = path.join(outputRoot, filename);
	const temporary = `${destination}.tmp`;
	fs.writeFileSync(temporary, archive, { mode: 0o644 });
	fs.renameSync(temporary, destination);
	return {
		path: destination,
		filename,
		size: archive.length,
		sha256: crypto.createHash("sha256").update(archive).digest("hex"),
	};
};
