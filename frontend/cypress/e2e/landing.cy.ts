describe("Builder Landing", () => {
	before(() => {
		cy.login();
	});
	it("Open builder page", () => {
		cy.visit("builder/home");
	});
});
