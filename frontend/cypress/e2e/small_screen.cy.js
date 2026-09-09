describe("Small screen handling", () => {
	const pageTitle = `Small Screen Test ${Date.now()}`;
	let pageName;

	before(() => {
		cy.login();
		cy.visit("builder/home");
		cy.window()
			.its("csrf_token")
			.then((csrfToken) => {
				cy.request({
					method: "POST",
					url: "/api/resource/Builder Page",
					headers: { "X-Frappe-CSRF-Token": csrfToken },
					body: { page_title: pageTitle },
				}).then((response) => {
					pageName = response.body.data.name;
				});
			});
	});

	after(() => {
		if (!pageName) return;
		cy.login();
		cy.visit("builder/home");
		cy.window()
			.its("csrf_token")
			.then((csrfToken) => {
				cy.request({
					method: "DELETE",
					url: `/api/resource/Builder Page/${pageName}`,
					headers: { "X-Frappe-CSRF-Token": csrfToken },
					failOnStatusCode: false,
				});
			});
	});

	beforeEach(() => {
		cy.login();
		// cypress defaults to 1000px wide, which is already below tailwind's `lg` (1024px)
		cy.viewport(1440, 900);
		cy.visit(`builder/page/${pageName}`);
		cy.get(".page-builder").should("be.visible");
	});

	it("closes the page title popover and covers the editor when the viewport drops below lg", () => {
		cy.contains(".toolbar", pageTitle).click();
		cy.contains("[data-slot='content']", "Page Title").should("be.visible");

		cy.viewport(1023, 900);

		// the popover body is portalled to <body> and unmounted when closed, so it should
		// be gone entirely rather than merely hidden along with its parent
		cy.contains("[data-slot='content']", "Page Title").should("not.exist");
		cy.contains("Screen too small").should("be.visible");
		cy.get(".page-builder").should("not.be.visible");
	});

	it("restores the editor when the viewport goes back above lg", () => {
		cy.viewport(1023, 900);
		cy.contains("Screen too small").should("be.visible");

		cy.viewport(1440, 900);

		cy.contains("Screen too small").should("not.exist");
		cy.get(".page-builder").should("be.visible");
		// the popover stays closed until the user opens it again
		cy.contains("[data-slot='content']", "Page Title").should("not.exist");
	});
});