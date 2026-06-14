import { createResource } from "frappe-ui";

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
