import type Block from "@/block";
import { builderSettings } from "@/data/builderSettings";
import { webPages } from "@/data/webPage";
import router from "@/router";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore.js";
import { BuilderClientScript, BuilderPage } from "@/types/doctypes";
import getBlockTemplate from "@/utils/blockTemplate";
import {
	confirm,
	generateId,
	getBlockInstance,
	getCopyWithoutParent,
	getRouteVariables,
} from "@/utils/helpers";
import { createDocumentResource, createListResource, createResource, toast } from "frappe-ui";
import { defineStore } from "pinia";
import { nextTick } from "vue";

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
		pageLoadToken: 0,
		snapshotsVersion: 0,
	}),
	actions: {
		async setPage(pageName: string, resetCanvas = true, routeParams = null as Object | null) {
			this.settingPage = true;
			if (!pageName) {
				return;
			}

			this.selectedPage = pageName;
			const pageLoadToken = ++this.pageLoadToken;

			const page = await this.fetchActivePage(pageName);
			if (pageLoadToken !== this.pageLoadToken || this.selectedPage !== pageName) {
				return;
			}
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
			const variables = localStorage.getItem(`${page.name}:routeVariables`) || "{}";
			this.routeVariables = JSON.parse(variables);
			if (routeParams) {
				Object.assign(this.routeVariables, routeParams);
			}
			await this.setPageData(this.activePage);

			const canvasStore = useCanvasStore();
			// switching pages always exits any active version preview
			canvasStore.clearVersionPreview();
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
						// detect pinned component instances whose live component drifted
						componentStore.refreshComponentUpdates();
						// surface any warnings stashed by a just-completed snapshot restore
						const restoreWarnings = sessionStorage.getItem("builder:restoreWarnings");
						if (restoreWarnings) {
							sessionStorage.removeItem("builder:restoreWarnings");
							for (const message of JSON.parse(restoreWarnings) as string[]) {
								toast.warning(message);
							}
						}
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
				name: pageName as string,
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
					error: () => {
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
					this.activePage = await this.fetchActivePage(this.selectedPage as string);
					this.snapshotsVersion++;
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

		async createManualSnapshot(label?: string) {
			const res = await webPages.runDocMethod.submit({
				name: this.selectedPage as string,
				method: "create_manual_snapshot",
				label: label || null,
			});
			this.snapshotsVersion++;
			return res;
		},

		async restoreSnapshot(snapshotName: string) {
			// wait out any in-flight autosave so it can't clobber the restored draft
			await this.waitTillPageIsSaved();
			const res = await webPages.runDocMethod.submit({
				name: this.selectedPage as string,
				method: "restore_snapshot",
				snapshot: snapshotName,
			});
			// surface any deleted-dependency warnings after the upcoming reload
			const warnings = (res?.message?.warnings || []) as string[];
			if (warnings.length) {
				sessionStorage.setItem("builder:restoreWarnings", JSON.stringify(warnings));
			}
			// router.go(0);
			// Instead of a hard reload, we could are just re-fetching the page document
			this.setPage(this.selectedPage as string, false);
			toast.success("Version restored");
		},

		async unpublishPage(page?: BuilderPage) {
			const targetName = page?.name || this.selectedPage;
			const targetTitle = page?.page_title || page?.page_name || "this page";
			const confirmed = await confirm(
				`Are you sure you want to unpublish "${targetTitle}"? It will no longer be accessible on the website.`,
			);
			if (!confirmed) {
				return;
			}
			return webPages.setValue
				.submit({
					name: targetName,
					published: false,
				})
				.then(() => {
					toast.success("Page unpublished");
					if (page) {
						page.published = 0;
					} else {
						this.setPage(this.selectedPage as string);
					}
					builderSettings.reload();
				});
		},

		updateActivePage(key: keyof BuilderPage, value: any) {
			if (!this.activePage) {
				return;
			}
			// Optimistically update in-place so reactive bindings stay consistent
			this.activePage[key] = value;
			return webPages.setValue.submit({
				name: this.activePage.name as string,
				[key]: value,
			});
		},

		savePage() {
			const builderStore = useBuilderStore();
			if (builderStore.readOnlyMode || builderStore.aiBuildingCanvas) {
				// callers may have optimistically set this before invoking savePage
				this.savingPage = false;
				return;
			}

			// Own the flag here (not only in the editor watch) so every caller —
			// including direct savePage() calls — keeps waitTillPageIsSaved reliable.
			this.savingPage = true;

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
				name: this.activePage?.name || this.selectedPage,
				draft_blocks: pageData,
			};
			return webPages.setValue
				.submit(args)
				.then((page: BuilderPage) => {
					if (this.activePage) {
						Object.assign(this.activePage, page);
					} else {
						this.activePage = page;
					}
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

		/** Persist a generated page_data_script (the static-repeater data shim) and
		 * refresh pageData so repeaters render immediately in the editor. The script
		 * is code we generate from the AI's JSON data — never AI-authored. */
		applyRepeaterDataScript(script: string) {
			const name = this.activePage?.name || this.selectedPage;
			if (!name) return;
			if (this.activePage) this.activePage.page_data_script = script;
			return webPages.setValue
				.submit({ name, page_data_script: script })
				.then((page: BuilderPage) => {
					this.activePage = page;
					this.setPageData(page);
				})
				.catch(() => null);
		},

		setRouteVariable(variable: string, value: string) {
			this.routeVariables[variable] = value;
			localStorage.setItem(`${this.selectedPage}:routeVariables`, JSON.stringify(this.routeVariables));
			this.setPageData(this.activePage as BuilderPage);
		},

		openPageInBrowser(page: BuilderPage) {
			const pageURL = this.getResolvedPageURL(true, page);
			const targetWindow = window.open(pageURL, "builder-preview");
			if (targetWindow?.location.pathname === pageURL) {
				targetWindow?.location.reload();
			} else {
				setTimeout(() => {
					// wait for the page to load
					targetWindow?.location.reload();
				}, 50);
			}
		},

		getResolvedPageURL(prependSlash = true, page: BuilderPage | null = null) {
			let route = page?.route || this.activePage?.route || "/";
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
			return `${prependSlash ? "/" : ""}${route}`;
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
