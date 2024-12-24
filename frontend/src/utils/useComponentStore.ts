import webComponent from "@/data/webComponent";
import useStore from "@/store";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import Block from "@/utils/block";
import getBlockTemplate from "@/utils/blockTemplate";
import { alert, getBlockInstance, getBlockObject } from "@/utils/helpers";
import { createDocumentResource } from "frappe-ui";
import { defineStore } from "pinia";
import { markRaw } from "vue";
import { toast } from "vue-sonner";

const useComponentStore = defineStore("componentStore", {
	state: () => ({
		components: <BlockComponent[]>[],
		componentMap: <Map<string, Block>>new Map(),
		componentDocMap: <Map<string, BuilderComponent>>new Map(),
		fetchingComponent: new Set(),
	}),
	actions: {
		async editComponent(block?: Block | null, componentName?: string) {
			if (!block?.isExtendedFromComponent() && !componentName) {
				return;
			}
			componentName = componentName || (block?.extendedFromComponent as string);
			await this.loadComponent(componentName);
			const component = this.getComponent(componentName);
			const componentBlock = this.getComponentBlock(componentName);
			const store = useStore();
			store.editOnCanvas(
				componentBlock,
				(block: Block) => {
					webComponent.setValue
						.submit({
							name: componentName,
							block: getBlockObject(block),
						})
						.then((data: BuilderComponent) => {
							this.componentDocMap.set(data.name, data);
							this.componentMap.set(data.name, markRaw(getBlockInstance(data.block)));
							toast.success("Component saved!");
						});
				},
				"Save Component",
				component.component_name,
			);
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
			const store = useStore();
			for (const block of store.activeCanvas?.getRootBlock()?.children || []) {
				if (checkComponent(block)) {
					return true;
				}
			}
			return false;
		},
		getComponentBlock(componentName: string) {
			return (
				(this.componentMap.get(componentName) as Block) ||
				getBlockInstance(getBlockTemplate("loading-component"))
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
							docstatus: 1 as 0 | 1 | 2,
						};
						this.setComponentMap(missingComponentDoc);
					})
					.finally(() => {
						this.fetchingComponent.delete(componentName);
					});
			}
		},
		setComponentMap(componentDoc: BuilderComponent) {
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
					return;
				}
			}
			return webComponent.insert
				.submit(obj)
				.then(() => {
					this.componentMap.set(obj.name, getBlockInstance(obj.block));
				})
				.catch(() => {
					console.log(`There was an error while creating ${obj.component_name}`);
				});
		},
		getComponentName(componentId: string) {
			let componentObj = webComponent.getRow(componentId);
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
	},
});

export default useComponentStore;
