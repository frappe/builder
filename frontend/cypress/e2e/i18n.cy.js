const translationsUrl = "**/api/method/builder.api.get_translations";
const permissionUrl = "**/api/method/frappe.client.has_permission";

function allowBuilderAccess(onRequest = () => {}) {
	cy.intercept("POST", permissionUrl, (request) => {
		onRequest();
		request.reply({ message: { has_permission: true } });
	}).as("hasPermission");
}

describe("Builder translations", () => {
	beforeEach(() => {
		cy.login();
	});

	it("loads translations before the first router navigation", () => {
		let translationsLoaded = false;

		cy.intercept("GET", translationsUrl, (request) => {
			request.on("response", () => {
				translationsLoaded = true;
			});
			request.reply({
				delay: 1000,
				body: { message: { "All Pages": "Alle Seiten" } },
			});
		}).as("translations");
		allowBuilderAccess(() => expect(translationsLoaded).to.equal(true));

		cy.visit("/builder/home");
		cy.get("#app").children().should("have.length", 0);
		cy.wait("@translations").its("response.statusCode").should("equal", 200);
		cy.wait("@hasPermission");
		cy.contains("Alle Seiten").should("exist");
		cy.contains("All Pages").should("not.exist");
	});

	it("starts with English source strings after a translation error", () => {
		cy.intercept("GET", translationsUrl, {
			statusCode: 500,
			body: { exc_type: "TranslationError" },
		}).as("translations");
		allowBuilderAccess();

		cy.visit("/builder/home");
		cy.wait("@translations").its("response.statusCode").should("equal", 500);
		cy.wait("@hasPermission");
		cy.contains("All Pages").should("exist");
	});

	it("starts after the translation request timeout", () => {
		cy.intercept("GET", translationsUrl, {
			delay: 10000,
			body: { message: { "All Pages": "Zu spät" } },
		}).as("translations");
		allowBuilderAccess();
		const startedAt = Date.now();

		cy.visit("/builder/home");
		cy.wait("@hasPermission", { timeout: 8000 });
		cy.contains("All Pages", { timeout: 8000 })
			.should("exist")
			.then(() => {
				expect(Date.now() - startedAt).to.be.lessThan(8000);
			});
		cy.contains("Zu spät").should("not.exist");
	});
});
