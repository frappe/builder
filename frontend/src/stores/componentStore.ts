import type Block from "@/block";
import { useLatestRequest } from "@/composables/useLatestRequest";
import { getVersionedDoc } from "@/data/snapshot";
import { webPages } from "@/data/webPage";
import webComponent from "@/data/webComponent";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { BuilderComponent } from "@/types/doctypes";
import getBlockTemplate from "@/utils/blockTemplate";
import { alert, confirm, getBlockInstance, getBlockObject, parseJSONWithFallback } from "@/utils/helpers";
import { createDocumentResource, createResource, toast } from "frappe-ui";
import { defineStore } from "pinia";
import { markRaw } from "vue";

export const COMPONENT_DATA_FRAGMENT_KEY = "__fragment__";

export type ComponentDataStore = Record<string, Record<string, Record<string, any>>>;

const { run: runLatestRequest } = useLatestRequest();

// key used to track a pinned (component, version) pair
const pinKey = (componentId: string, version: string) => `${componentId}::${version}`;

// visit a block and all its descendants
const walkBlocks = (block: Block | null | undefined, visitor: (block: Block) => void) => {
	if (!block) return;
	visitor(block);
	(block.children || []).forEach((child) => walkBlocks(child, visitor));
};

// set the component version on every block belonging to `componentId` (instance root + materialized
// children) in a subtree. When `onlyPinned` is true, only blocks that already have a componentVersion
// are touched (used for re-pin); otherwise all matching blocks are pinned (used for fresh instances).
const setSubtreeComponentVersion = (
	block: Block | null | undefined,
	componentId: string,
	version: string,
	onlyPinned = false,
) =>
	walkBlocks(block, (b) => {
		if (
			(b.extendedFromComponent === componentId || b.isChildOfComponent === componentId) &&
			(!onlyPinned || b.componentVersion)
		) {
			b.componentVersion = version;
		}
	});

const useComponentStore = defineStore("componentStore", {
	state: () => ({
		components: <BlockComponent[]>[],
		componentMap: <Map<string, Block>>new Map(),
		componentDocMap: <Map<string, BuilderComponent>>new Map(),
		fetchingComponent: new Set(),
		selectedComponent: null as string | null,
		// frozen component versions, keyed by the version snapshot name (the pin)
		componentVersionMap: <Map<string, BuilderComponent>>new Map(),
		fetchingComponentVersion: new Set(),
		// `${componentId}::${version}` for pinned instances whose live component changed
		outdatedPins: <Set<string>>new Set(),
		// bumped on re-pin to force pinned `referenceComponent` computeds to recompute
		// (their closure captures the pre-reactive block, so a changed componentVersion
		// alone doesn't invalidate them — see getComponentVersionBlock)
		versionBump: 0,
		componentData: <ComponentDataStore>{},
	}),
	actions: {
		async editComponent(block?: Block | null, componentName?: string) {
			if (!block?.isExtendedFromComponent() && !componentName) {
				return;
			}
			componentName =
				componentName || (block?.extendedFromComponent as string) || (block?.isChildOfComponent as string);
			await this.loadComponent(componentName);
			const component = this.getComponent(componentName);
			const componentBlock = this.getComponentBlock(componentName);

			// Fetch component data for preview when entering fragment mode
			// const defaultProps = getComponentDefaultProps(componentBlock);
			// this.setComponentData(componentName, defaultProps);

			const canvasStore = useCanvasStore();
			canvasStore.editOnCanvas(
				componentBlock,
				(block: Block) => {
					this.saveComponent(block, componentName);
				},
				"Save Component",
				component.component_name,
				component.name,
				true,
			);
		},
		saveComponent(block: Block, componentName: string) {
			const pageStore = usePageStore();
			const doc = this.getComponent(componentName);
			return webComponent.setValue
				.submit({
					name: componentName,
					block: getBlockObject(block),
					component_props: doc?.component_props || {},
					component_data_script: doc?.component_data_script || "",
					component_js: doc?.component_js || "",
					component_css: doc?.component_css || "",
				})
				.then(async (data: BuilderComponent) => {
					this.setComponentMap(data);
					toast.success("Component saved!", {
						duration: 5000,
						action: {
							label: "Sync in all pages",
							onClick: async () => {
								const componentResource = createResource({
									url: "builder.api.sync_component",
									method: "POST",
									params: {
										component_id: data.name,
									},
									auto: true,
								});
								await toast.promise(componentResource.promise, {
									loading: "Syncing component in all the pages...",
									success: () => {
										pageStore.fetchActivePage().then(() => {
											pageStore.setPage(pageStore.activePage?.name as string);
										});
										return "Component synced in all the pages!";
									},
									error: () => "Error syncing component in all the pages!",
								});
							},
						},
					});
				});
		},
		isComponentUsed(componentName: string) {
			// TODO: Refactor or reduce complexity
			const checkComponent = (block: Block) => {
				if (block.extendedFromComponent === componentName) {
					return true;
				}
				if (block.children) {
					for (const child of block.children) {
						if (checkComponent(child)) {
							return true;
						}
					}
				}
				return false;
			};
			const canvasStore = useCanvasStore();
			for (const block of canvasStore.activeCanvas?.getRootBlock()?.children || []) {
				if (checkComponent(block)) {
					return true;
				}
			}
			return false;
		},
		getComponentBlock(componentName: string) {
			return (
				(this.componentMap.get(componentName) as Block) ||
				getBlockInstance(getBlockTemplate("empty-component"))
			);
		},
		async loadComponent(componentName: string) {
			if (!this.componentMap.has(componentName) && !this.fetchingComponent.has(componentName)) {
				this.fetchingComponent.add(componentName);
				return this.fetchComponent(componentName)
					.then((componentDoc) => {
						this.setComponentMap(componentDoc);
					})
					.catch(() => {
						const missingComponentDoc = {
							name: componentName,
							block: JSON.stringify(getBlockTemplate("missing-component")),
							creation: "",
							modified: "",
							owner: "Administrator",
							modified_by: "Administrator",
						};
						this.setComponentMap(missingComponentDoc);
					})
					.finally(() => {
						this.fetchingComponent.delete(componentName);
					});
			}
		},
		setComponentMap(componentDoc: BuilderComponent) {
			componentDoc.component_props = parseJSONWithFallback(componentDoc.component_props, {});
			this.componentDocMap.set(componentDoc.name, componentDoc);
			this.componentMap.set(componentDoc.name, markRaw(getBlockInstance(componentDoc.block)));
		},
		async fetchComponent(componentName: string) {
			const webComponentDoc = await createDocumentResource({
				doctype: "Builder Component",
				name: componentName,
				auto: true,
			});
			await webComponentDoc.get.promise;
			return webComponentDoc.doc as BuilderComponent;
		},
		getComponentVersionBlock(versionName: string) {
			// touch versionBump so a re-pin (which changes a block's componentVersion to a
			// brand-new key this computed never read) still invalidates the computed
			this.versionBump;
			const doc = this.componentVersionMap.get(versionName);
			return doc ? (markRaw(getBlockInstance(doc.block)) as Block) : null;
		},
		getComponentVersionDoc(versionName: string) {
			this.versionBump;
			return this.componentVersionMap.get(versionName) ?? null;
		},
		async loadComponentVersion(versionName: string, componentId: string) {
			if (this.componentVersionMap.has(versionName) || this.fetchingComponentVersion.has(versionName)) {
				return;
			}
			this.fetchingComponentVersion.add(versionName);
			try {
				// fetch the component doc as it was at this version (versioned fields overlaid)
				const doc = await getVersionedDoc(versionName);
				if (doc?.block) {
					const versionedDoc = { ...doc } as BuilderComponent;
					versionedDoc.component_props = parseJSONWithFallback(versionedDoc.component_props, {});
					this.componentVersionMap.set(versionName, versionedDoc);
				} else {
					// pruned/missing version — show the live component instead
					await this.loadComponent(componentId);
				}
			} finally {
				this.fetchingComponentVersion.delete(versionName);
			}
		},
		// collect the pinned (component, version) pairs in the current canvas
		getPinnedComponents() {
			const pins = new Map<string, { component_id: string; version: string }>();
			walkBlocks(useCanvasStore().activeCanvas?.getRootBlock(), (block) => {
				if (block.extendedFromComponent && block.componentVersion) {
					pins.set(pinKey(block.extendedFromComponent, block.componentVersion), {
						component_id: block.extendedFromComponent,
						version: block.componentVersion,
					});
				}
			});
			return Array.from(pins.values());
		},
		// ask the server which pinned instances have a newer live component
		async refreshComponentUpdates() {
			const pageStore = usePageStore();
			const pins = this.getPinnedComponents();
			if (!pageStore.selectedPage || !pins.length) {
				this.outdatedPins = new Set();
				return;
			}
			const res = await webPages.runDocMethod.submit({
				name: pageStore.selectedPage as string,
				method: "get_outdated_component_pins",
				// stringify so the array survives the doc-method param encoding intact
				pins: JSON.stringify(pins),
			});
			const outdated = (res?.message || []) as { component_id: string; version: string }[];
			this.outdatedPins = new Set(outdated.map((p) => pinKey(p.component_id, p.version)));
			// load the live component docs so the roll-up panel can show friendly names
			outdated.forEach((p) => this.loadComponent(p.component_id));
		},
		isPinOutdated(componentId?: string, version?: string) {
			if (!componentId || !version) return false;
			return this.outdatedPins.has(pinKey(componentId, version));
		},
		// mint the component's latest version and pin a freshly-used instance to it
		async pinComponentInstance(block: Block, componentName: string) {
			const pageStore = usePageStore();
			if (!pageStore.selectedPage) return;
			const res = await webPages.runDocMethod.submit({
				name: pageStore.selectedPage as string,
				method: "get_current_component_version",
				component_id: componentName,
			});
			const version = (res?.message ?? res) as string;
			if (!version) return;
			await this.loadComponentVersion(version, componentName);
			setSubtreeComponentVersion(block, componentName, version);
			this.versionBump++;
		},
		// mint the component's latest version, apply the given re-pin, and persist
		async repinToLatest(
			componentId: string,
			repin: (newVersion: string, newComponentBlock: Block) => Promise<void> | void,
			refresh = true,
		) {
			const pageStore = usePageStore();
			const res = await webPages.runDocMethod.submit({
				name: pageStore.selectedPage as string,
				method: "get_current_component_version",
				component_id: componentId,
			});
			const newVersion = (res?.message ?? res) as string;
			if (!newVersion) return;
			await this.loadComponentVersion(newVersion, componentId);
			const newComponentBlock = this.getComponentVersionBlock(newVersion);
			if (!newComponentBlock) return;
			await repin(newVersion, newComponentBlock);
			this.versionBump++;
			useCanvasStore().activeCanvas?.toggleDirty(true);
			pageStore.savePage();
			if (refresh) await this.refreshComponentUpdates();
		},
		// re-pin an instance to the latest version and rebuild its subtree from the new version,
		// preserving user overrides on matched children via three-way diff against the old version
		async rebuildInstance(
			block: Block,
			componentId: string,
			newVersion: string,
			newComponentBlock: Block,
		) {
			const oldVersion = block.componentVersion;
			let oldComponentBlock: Block | null = null;
			if (oldVersion) {
				await this.loadComponentVersion(oldVersion, componentId);
				oldComponentBlock = this.getComponentVersionBlock(oldVersion);
			}
			if (!oldComponentBlock) {
				oldComponentBlock = this.getComponentBlock(componentId);
			}
			block.componentVersion = newVersion;
			block.rebuildWithComponent(
				componentId,
				newComponentBlock.children,
				oldComponentBlock?.children || [],
			);
		},
		// re-pin a single instance (and its materialized children) to the latest version
		updatePinnedComponent(block: Block) {
			const componentId = block.extendedFromComponent;
			if (!componentId) return;
			return this.repinToLatest(componentId, (newVersion, newComponentBlock) =>
				this.rebuildInstance(block, componentId, newVersion, newComponentBlock),
			);
		},
		// re-pin every instance of a component on the page to the latest version
		updateComponentInstances(componentId: string, refresh = true) {
			return this.repinToLatest(
				componentId,
				async (newVersion, newComponentBlock) => {
					const roots: Block[] = [];
					walkBlocks(useCanvasStore().activeCanvas?.getRootBlock(), (b) => {
						if (b.extendedFromComponent === componentId && b.componentVersion) {
							roots.push(b);
						}
					});
					for (const root of roots) {
						await this.rebuildInstance(root, componentId, newVersion, newComponentBlock);
					}
				},
				refresh,
			);
		},
		// first instance block of a component on the current page (for canvas highlight on hover)
		getComponentInstanceBlock(componentId: string) {
			let instance: Block | null = null;
			walkBlocks(useCanvasStore().activeCanvas?.getRootBlock(), (block) => {
				if (!instance && block.extendedFromComponent === componentId) {
					instance = block;
				}
			});
			return instance as Block | null;
		},
		// summary of outdated pinned components on the page (for the roll-up panel)
		getOutdatedComponentList() {
			const counts = new Map<string, number>();
			walkBlocks(useCanvasStore().activeCanvas?.getRootBlock(), (block) => {
				if (this.isPinOutdated(block.extendedFromComponent, block.componentVersion)) {
					counts.set(
						block.extendedFromComponent as string,
						(counts.get(block.extendedFromComponent as string) || 0) + 1,
					);
				}
			});
			return Array.from(counts.entries()).map(([component_id, count]) => ({
				component_id,
				component_name: this.getComponentName(component_id),
				count,
			}));
		},
		async updateAllOutdatedComponents() {
			const items = this.getOutdatedComponentList();
			for (const item of items) {
				await this.updateComponentInstances(item.component_id, false);
			}
			await this.refreshComponentUpdates();
		},
		getComponent(componentName: string) {
			return this.componentDocMap.get(componentName) as BuilderComponent;
		},
		createComponent(obj: BuilderComponent, updateExisting = false) {
			const component = this.getComponent(obj.name);
			if (component) {
				const existingComponent = component.block;
				const newComponent = obj.block;
				if (updateExisting && existingComponent !== newComponent) {
					return webComponent.setValue.submit({
						name: obj.name,
						block: obj.block,
					});
				} else {
					console.warn("Skipping component update", obj.name);
					return;
				}
			}
			return webComponent.insert
				.submit(obj)
				.then(() => {
					this.setComponentMap(obj);
				})
				.catch((e: { response: { status: number } }) => {
					if (e?.response?.status === 409) {
						if (updateExisting) {
							return webComponent.setValue.submit({
								name: obj.name,
								block: obj.block,
							});
						}
					}
				});
		},
		getComponentName(componentId: string, componentVersion?: string) {
			let componentObj = this.componentDocMap.get(componentId);
			if (!componentObj && componentVersion) {
				componentObj = this.componentVersionMap.get(componentVersion);
			}
			if (!componentObj) {
				return componentId;
			}
			return componentObj.component_name;
		},
		async deleteComponent(component: BlockComponent) {
			if (this.isComponentUsed(component.name)) {
				alert("Component is used in current page. You cannot delete it.");
			} else {
				const confirmed = await confirm(
					`Are you sure you want to delete component: ${component.component_name}?`,
				);
				if (confirmed) {
					webComponent.delete.submit(component.name).then(() => {
						this.componentMap.delete(component.name);
					});
				}
			}
		},
		getComponentInstanceData(componentId: string, blockId: string | null = null) {
			const instanceKey = blockId ?? COMPONENT_DATA_FRAGMENT_KEY;
			return this.componentData[componentId]?.[instanceKey] ?? {};
		},
		async setComponentData(
			componentId: string,
			props: Record<string, any> = {},
			blockId: string | null = null,
			componentVersion?: string,
		) {
			const instanceKey = blockId ?? COMPONENT_DATA_FRAGMENT_KEY;
			const requestKey = `${componentId}::${instanceKey}`;
			// use the data script from the pinned version when available, else live component
			const versionedDoc = componentVersion ? this.getComponentVersionDoc(componentVersion) : this.getComponent(componentId);
			const script = versionedDoc?.component_data_script ?? undefined;
			const result = await runLatestRequest(requestKey, () =>
				createResource({
					url: "builder.api.get_component_data",
					method: "GET",
					auto: false,
				})
					.fetch({
						component_name: componentId,
						props: JSON.stringify(props),
						script,
					})
					.then((data: { [key: string]: any }) => data ?? {})
					.catch((e: { message: string }) => {
						console.error("Failed to fetch component data:", e.message);
						return {};
					}),
			);
			if (result.stale) {
				return;
			}

			if (!this.componentData[componentId]) {
				this.componentData[componentId] = {};
			}
			this.componentData[componentId][instanceKey] = result.value;
		},
		async deleteComponentData(componentId: string, blockId: string | null = null) {
			const instanceKey = blockId ?? COMPONENT_DATA_FRAGMENT_KEY;
			if (!this.componentData[componentId]) return;
			this.componentData[componentId][instanceKey] = {};
		},
	},
});

export default useComponentStore;
