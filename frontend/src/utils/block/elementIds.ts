import type Block from "@/block";

// A template, a duplicate or a pasted copy keeps the ids it came with, so its #links
// would open the first copy. Renames the ids the page already uses, and points the
// block's own #links at the new names.
export function makeIdsUnique(block: Block, pageBlock: Block) {
	const takenIds = new Set(getBlocks(pageBlock).map(getId).filter(Boolean));
	const blocks = getBlocks(block);
	const renamedIds = new Map<string, string>();

	blocks.forEach((child) => {
		const id = getId(child);
		if (!id) return;
		if (takenIds.has(id)) {
			const freeId = getFreeId(id, takenIds);
			renamedIds.set(id, freeId);
			child.setId(freeId);
			takenIds.add(freeId);
		} else {
			takenIds.add(id);
		}
	});

	blocks.forEach((child) => {
		const href = String(child.getAttribute("href") || "");
		const renamedId = href.startsWith("#") && renamedIds.get(href.slice(1));
		if (renamedId) child.setAttribute("href", `#${renamedId}`);
	});
}

function getBlocks(block: Block): Block[] {
	return [block, ...block.getChildren().flatMap(getBlocks)];
}

function getId(block: Block) {
	return String(block.getId() || "");
}

// "overlay" becomes "overlay-2", and "overlay-2" becomes "overlay-3", not "overlay-2-2"
function getFreeId(id: string, takenIds: Set<string>) {
	const name = id.replace(/-\d+$/, "");
	let count = 2;
	while (takenIds.has(`${name}-${count}`)) count++;
	return `${name}-${count}`;
}
