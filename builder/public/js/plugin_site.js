// what a plugin's site code calls on a published page: mount once on each matching block.
// The editor defines its own builderSite, which also remounts as blocks change on the canvas.
window.builderSite = window.builderSite || {
	onBlock: function (selector, mount) {
		function run() {
			document.querySelectorAll(selector).forEach(function (element) {
				try {
					mount(element, { editor: false });
				} catch (error) {
					console.error("[builder] a plugin effect failed", error);
				}
			});
		}
		if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
		else run();
	},
};
