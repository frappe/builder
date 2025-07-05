import type Block from "@/block";
import { builderSettings } from "@/data/builderSettings";
import { webPages } from "@/data/webPage";
import router from "@/router";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore.js";
import { posthog } from "@/telemetry";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import getBlockTemplate from "@/utils/blockTemplate";
import {
	confirm,
	generateId,
	getBlockInstance,
	getCopyWithoutParent,
	getRouteVariables,
} from "@/utils/helpers";
import { createDocumentResource, createListResource, createResource } from "frappe-ui";
import { defineStore } from "pinia";
import { nextTick } from "vue";
import { toast } from "vue-sonner";
import { BuilderClientScript } from "../types/Builder/BuilderClientScript";

const usePageStore = defineStore("pageStore", {
	state: () => ({
		routeVariables: <{ [key: string]: string }>{},
		pageData: <{ [key: string]: [] }>{},
		pageName: "Home",
		route: "/",
		selectedPage: <string | null>null,
		pageBlocks: <Block[]>[],
		saveId: null as string | null,
		activePage: <BuilderPage | null>null,
		activePageScripts: <BuilderClientScript[]>[],
		savingPage: false,
		settingPage: false,
	}),
	actions: {
		async setPage(pageName: string, resetCanvas = true, routeParams = null as Object | null) {
			this.settingPage = true;
			if (!pageName) {
				return;
			}

			const page = await this.fetchActivePage(pageName);
			if (!page) {
				toast.error("Page not found", {
					duration: Infinity,
				});
				return;
			}
			this.activePage = page;

			const blocks = JSON.parse(page.draft_blocks || page.blocks || "[]");
			this.editPage(!resetCanvas);
			if (!Array.isArray(blocks)) {
				const canvasStore = useCanvasStore();
				canvasStore.pushBlocks([blocks]);
			}
			this.pageBlocks = [getBlockInstance(blocks[0] || getBlockTemplate("body"))];
			this.pageName = page.page_name as string;
			this.route = page.route || "/" + this.pageName.toLowerCase().replace(/ /g, "-");
			this.selectedPage = page.name;
			const variables = localStorage.getItem(`${page.name}:routeVariables`) || "{}";
			this.routeVariables = JSON.parse(variables);
			if (routeParams) {
				Object.assign(this.routeVariables, routeParams);
			}
			await this.setPageData(this.activePage);

			const canvasStore = useCanvasStore();
			canvasStore.activeCanvas?.setRootBlock(this.pageBlocks[0], resetCanvas);

			if (page.client_scripts?.length) {
				// Fetch full script documents for each script
				const scriptsResource = createListResource({
					doctype: "Builder Client Script",
					fields: ["script_type", "name", "script"],
					filters: [["name", "in", page.client_scripts.map((script) => script.builder_script)]],
					auto: true,
				});

				await scriptsResource.list.promise;
				this.activePageScripts = scriptsResource.data as BuilderClientScript[];
			} else {
				this.activePageScripts = [];
			}

			nextTick(() => {
				const componentStore = useComponentStore();
				const interval = setInterval(() => {
					if (!componentStore.fetchingComponent.size) {
						this.settingPage = false;
						window.name = `editor-${pageName}`;
						clearInterval(interval);
					}
				}, 50);
			});
		},

		async setActivePage(pageName: string) {
			this.selectedPage = pageName;
			const page = await this.fetchActivePage(pageName);
			if (!page) {
				return;
			}
			this.activePage = page;
		},

		async fetchActivePage(pageName?: string) {
			const webPageResource = await createDocumentResource({
				doctype: "Builder Page",
				name: pageName,
				auto: true,
			});
			try {
				await webPageResource.get.promise;
			} catch (e) {
				return null;
			}

			const page = webPageResource.doc as BuilderPage;
			return page;
		},

		editPage(retainSelection = false) {
			const canvasStore = useCanvasStore();
			if (!retainSelection) {
				canvasStore.activeCanvas?.clearSelection();
			}
			canvasStore.editingMode = "page";
		},

		async duplicatePage(page: BuilderPage) {
			toast.promise(
				createResource({
					url: "builder.api.duplicate_page",
					method: "POST",
					params: {
						page_name: page.name,
					},
				}).fetch(),
				{
					loading: "Duplicating page",
					success: async (page: BuilderPage) => {
						// load page and refresh
						router.push({ name: "builder", params: { pageId: page.page_name } }).then(() => {
							router.go(0);
						});
						return "Page duplicated";
					},
				},
			);
		},

		deletePage: async (page: BuilderPage) => {
			const confirmed = await confirm(
				`Are you sure you want to delete page: ${page.page_title || page.page_name}?`,
			);
			if (confirmed) {
				await toast.promise(webPages.delete.submit(page.name), {
					loading: "Deleting page",
					success: () => {
						return "Page deleted";
					},
					error: (e) => {
						return "Page deletion failed";
					},
				});
			}
		},

		async publishPage(openInBrowser = true) {
			await this.waitTillPageIsSaved();
			return webPages.runDocMethod
				.submit({
					name: this.selectedPage as string,
					method: "publish",
					route_variables: this.routeVariables,
				})
				.then(async () => {
					posthog.capture("builder_page_published", {
						page: this.selectedPage,
					});
					this.activePage = await this.fetchActivePage(this.selectedPage as string);
					if (openInBrowser) {
						this.openPageInBrowser(this.activePage as BuilderPage);
					}
				});
		},

		async revertChanges() {
			const confirmed = await confirm(
				"This will revert all changes made to the page since the last publish. Are you sure you want to continue?",
			);
			if (confirmed) {
				await this.updateActivePage("draft_blocks", null);
				this.setPage(this.activePage?.name as string);
			}
		},

		async unpublishPage() {
			const confirmed = await confirm(
				"Are you sure you want to unpublish this page? It will no longer be accessible on the website.",
			);
			if (!confirmed) {
				return;
			}
			return webPages.setValue
				.submit({
					name: this.selectedPage,
					published: false,
				})
				.then(() => {
					toast.success("Page unpublished");
					this.setPage(this.selectedPage as string);
					builderSettings.reload();
				});
		},

		updateActivePage(key: keyof BuilderPage, value: any) {
			if (!this.activePage) {
				return;
			}
			return webPages.setValue
				.submit({
					name: this.activePage.name as string,
					[key]: value,
				})
				.then(() => {
					if (this.activePage) {
						this.activePage[key] = value;
					}
				});
		},

		savePage() {
			const canvasStore = useCanvasStore();
			const pageData = JSON.stringify(
				canvasStore
					.getPageBlocks()
					.filter((block): block is Block => block !== undefined)
					.map((block: Block) => getCopyWithoutParent(block)),
			);
			const saveId = generateId();

			// more save requests can be triggered till the first one is completed
			this.saveId = saveId;
			const args = {
				name: this.selectedPage,
				draft_blocks: pageData,
			};
			return webPages.setValue
				.submit(args)
				.then((page: BuilderPage) => {
					this.activePage = page;
				})
				.finally(() => {
					if (this.saveId === saveId) {
						this.saveId = null;
						this.savingPage = false;
					}
					canvasStore.activeCanvas?.toggleDirty(false);
				});
		},

		setPageData(page?: BuilderPage) {
			if (!page || !page.page_data_script) {
				this.pageData = {};
				return;
			}
			return webPages.runDocMethod
				.submit({
					method: "get_page_data",
					name: page.name,
					route_variables: this.routeVariables,
				})
				.then((data: { message: { [key: string]: [] } }) => {
					this.pageData = data.message;
				})
				.catch((e: { exc: string | null }) => {
					const error_message = e.exc?.split("\n").slice(-2)[0];
					toast.error("There was an error while fetching page data", {
						description: error_message,
					});
				});
		},

		setRouteVariable(variable: string, value: string) {
			this.routeVariables[variable] = value;
			localStorage.setItem(`${this.selectedPage}:routeVariables`, JSON.stringify(this.routeVariables));
			this.setPageData(this.activePage as BuilderPage);
		},

		openPageInBrowser(page: BuilderPage) {
			let route = page.route;
			if (this.pageData) {
				const routeVariables = getRouteVariables(route || "");
				routeVariables.forEach((variable: string) => {
					const routeVariableValue = this.routeVariables[variable];
					if (routeVariableValue) {
						if (route?.includes(`<${variable}>`)) {
							route = route?.replace(`<${variable}>`, routeVariableValue);
						} else if (route?.includes(`:${variable}`)) {
							route = route?.replace(`:${variable}`, routeVariableValue);
						}
					}
				});
			}
			const targetWindow = window.open(`/${route}`, "builder-preview");
			if (targetWindow?.location.pathname === `/${route}`) {
				targetWindow?.location.reload();
			} else {
				setTimeout(() => {
					// wait for the page to load
					targetWindow?.location.reload();
				}, 50);
			}
		},

		async waitTillPageIsSaved() {
			// small delay so that all the save requests are triggered
			if (!this.savingPage) {
				await new Promise((resolve) => setTimeout(resolve, 300));
			}
			return new Promise((resolve) => {
				const interval = setInterval(() => {
					if (!this.savingPage) {
						clearInterval(interval);
						resolve(null);
					}
				}, 100);
			});
		},
		isHomePage(page: BuilderPage | null = null) {
			return builderSettings.doc?.home_page === (page || this.activePage)?.route;
		},
	},
});

export default usePageStore;
