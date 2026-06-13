import { createResource } from "frappe-ui";

// Return the referenced doc as it looked at `snapshotName`, with the snapshot's versioned
// fields overlaid on the current doc. Doctype-agnostic — reusable for any versioned doctype.
export async function getVersionedDoc(snapshotName: string): Promise<Record<string, any> | null> {
	try {
		return await createResource({ url: "builder.api.get_versioned_doc", method: "POST" }).submit({
			snapshot: snapshotName,
		});
	} catch {
		// pruned / missing snapshot
		return null;
	}
}
