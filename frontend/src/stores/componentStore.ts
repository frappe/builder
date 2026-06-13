import type Block from "@/block";
import webComponent from "@/data/webComponent";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { BuilderComponent } from "@/types/doctypes";
import getBlockTemplate from "@/utils/blockTemplate";
import { alert, confirm, getBlockInstance, getBlockObject } from "@/utils/helpers";
import { createDocumentResource, createResource, toast } from "frappe-ui";
import { defineStore } from "pinia";
import { markRaw } from "vue";

export const COMPONENT_DATA_FRAGMENT_KEY = "__fragment__";

export type ComponentDataStore = Record<string, Record<string, Record<string, any>>>;

const componentDataRequestSeq = new Map<string, number>();

function getComponentDataRequestKey(componentId: string, instanceKey: string) {
	return `${componentId}::${instanceKey}`;
}

function parseJSONWithFallback<T>(value: T | string | undefined, fallback: T): T {
	if (value === undefined || value === null || value === "") {
		return fallback;
	}
	if (typeof value === "string") {
		return JSON.parse(value || JSON.stringify(fallback)) as T;
	}
	return value as T;
}


const useComponentStore = defineStore("componentStore", {
	state: () => ({
		components: <BlockComponent[]>[],
		componentMap: <Map<string, Block>>new Map(),
		componentDocMap: <Map<string, BuilderComponent>>new Map(),
		fetchingComponent: new Set(),
		selectedComponent: null as string | null,
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
					this.saveComponent(block, componentName)	
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
					component_vars: doc?.component_vars || {},
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
			componentDoc.component_vars = parseJSONWithFallback(componentDoc.component_vars, {});
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
		getComponentName(componentId: string) {
			let componentObj = this.componentDocMap.get(componentId);
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
		async setComponentData(componentId: string, props: Record<string, any> = {}, blockId: string | null = null) {
			const instanceKey = blockId ?? COMPONENT_DATA_FRAGMENT_KEY;
			const requestKey = getComponentDataRequestKey(componentId, instanceKey);
			const requestSeq = (componentDataRequestSeq.get(requestKey) ?? 0) + 1;
			componentDataRequestSeq.set(requestKey, requestSeq);

			const isLatestRequest = () => componentDataRequestSeq.get(requestKey) === requestSeq;

			return createResource({
				url: "builder.api.get_component_data",
				method: "GET",
				params: {
					component_name: componentId,
					props: JSON.stringify(props),
				},
			})
				.fetch()
				.then((data: { [key: string]: any }) => {
					if (!isLatestRequest()) {
						return;
					}
					if (!this.componentData[componentId]) {
						this.componentData[componentId] = {};
					}
					this.componentData[componentId][instanceKey] = data || {};
				})
				.catch((e: { message: string }) => {
					if (!isLatestRequest()) {
						return;
					}
					console.error("Failed to fetch component data:", e.message);
					if (!this.componentData[componentId]) {
						this.componentData[componentId] = {};
					}
					this.componentData[componentId][instanceKey] = {};
				});
		},
		async deleteComponentData(componentId: string, blockId: string | null = null) {
			const instanceKey = blockId ?? COMPONENT_DATA_FRAGMENT_KEY;
			this.componentData[componentId][instanceKey] = {};
		}
	},
});

export default useComponentStore;
