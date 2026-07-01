describe("Iframe canvas", () => {
	before(() => {
		cy.login();
	});

	it("renders the page tree inside a replaceable breakpoint frame", () => {
		cy.visit("builder/page/new");

		cy.get('iframe[data-canvas-breakpoint="desktop"]')
			.should("be.visible")
			.then(($frame) => {
				const firstFrame = $frame[0];
				const frameDocument = firstFrame.contentDocument;

				expect(frameDocument?.body.querySelector(".canvas[data-breakpoint='desktop']")).to.exist;
				expect(frameDocument?.body.querySelector(".__builder_component__")).to.exist;
				expect(firstFrame.ownerDocument.body.querySelector(".__builder_component__")).not.to.exist;

				cy.get('[data-testid="run-canvas-scripts"]').click();
				cy.get('iframe[data-canvas-breakpoint="desktop"]').should(($replacement) => {
					expect($replacement[0]).not.to.equal(firstFrame);
				});
			});
	});
});
