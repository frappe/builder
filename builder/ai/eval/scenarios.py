"""The eval's scenarios: what each asks Bob, on which page, and the tools that must
(or must not) run for a pass."""

from dataclasses import dataclass


@dataclass
class Scenario:
	name: str
	prompt: str
	on_fixture: bool = False
	# at least one of these tools must run, and none of `forbid`
	expect_any: tuple = ()
	forbid: tuple = ()
	# load the built page in a browser and drag its canvas (RuntimeCheck)
	runtime: bool = False


EDITS = ("update_block", "update_blocks", "add_block", "remove_block", "move_block")

KILN_AND_CLAY = (
	"Build the landing page for Kiln & Clay, a pottery studio in Bandra, Mumbai, run by Meera Iyer "
	"since 2019. Sections: a hero; the classes (Wheel throwing, four Saturdays, ₹2,800; Hand building, "
	"₹2,200; Kids clay club, ₹1,500); open studio hours (Tuesday to Sunday, 10am to 8pm); the glaze "
	"wall where students pick their finishes; and a visit section with the address, 14 Chapel Road, "
	"Bandra West."
)

SCENARIOS = (
	Scenario(
		"bare-build", "Make a page for my yoga studio.", expect_any=("present_ui",), forbid=("generate_page",)
	),
	Scenario(
		"brief-build",
		f"{KILN_AND_CLAY} Earthy terracotta and cream palette, editorial feel. Give it a look of its own, "
		"don't copy the site's other pages. Pick the photos yourself and build it now.",
		expect_any=("generate_page",),
	),
	# the look left open: where a page lands on its own, the category default or not
	Scenario(
		"free-build",
		f"{KILN_AND_CLAY} Give it a look of its own, don't copy the site's other pages. Pick the look "
		"and the photos yourself and build it now.",
		expect_any=("generate_page",),
	),
	Scenario(
		"edit",
		"Make the hero headline shorter and punchier, and give the main hero button our accent colour.",
		on_fixture=True,
		expect_any=EDITS,
		forbid=("generate_page",),
	),
	Scenario(
		"translate",
		"Translate all the text on this page into Hindi.",
		on_fixture=True,
		expect_any=("update_blocks",),
		forbid=("generate_page",),
	),
	Scenario(
		"redesign",
		"Redesign this whole page with a completely new look.",
		on_fixture=True,
		expect_any=("present_ui", "generate_page"),
	),
	Scenario(
		"opinion",
		"Should I use Comic Sans for the headings?",
		on_fixture=True,
		forbid=("generate_page", *EDITS),
	),
	Scenario(
		"3d-product",
		"Build a landing page for Orbit, a desk lamp with a magnetic swivel head, made by a two-person "
		"studio in Pune. The hero is an interactive 3D model of the lamp that visitors drag to turn. "
		"Sections: the lamp, the three finishes (Graphite ₹8,900, Brass ₹10,400, Sage ₹8,900), how the "
		"magnet joint works, and where to buy. Pick the look and the photos yourself and build it now.",
		expect_any=("generate_page",),
		runtime=True,
	),
	Scenario(
		"3d-scene",
		"Make an interactive 3D page for Saturn Nights, a planetarium show at the Nehru Planetarium, "
		"Mumbai, Fridays at 8pm, ₹250 a seat. The hero is a 3D Saturn with its rings that visitors orbit "
		"with the mouse; then the show, the timings and booking. Pick the look yourself and build it now.",
		expect_any=("generate_page",),
		runtime=True,
	),
	Scenario(
		"law-firm",
		"Build the home page for Mehta & Rao, a two-partner employment law firm in Bengaluru that helps "
		"startup employees with ESOP and termination disputes. Sections: what they handle, how a first "
		"consultation works (free, 30 minutes), the partners, and contact. Pick the look and the photos "
		"yourself and build it now.",
		expect_any=("generate_page",),
	),
	Scenario(
		"dev-tool",
		"Build a landing page for Tracebit, an open-source CLI that records a failing test's network "
		"calls so you can replay them offline. Sections: the problem, a terminal demo, install (brew "
		"install tracebit), pricing (free, or Team at $12 a seat), and the GitHub link. Pick the look "
		"yourself and build it now.",
		expect_any=("generate_page",),
	),
	Scenario(
		"festival",
		"Build a page for Monsoon Static, a two-day indie electronic music festival in Shillong, 14 and "
		"15 August, ₹3,500 for a pass. The lineup isn't announced yet, so show the venue, the passes "
		"and how to get there. Pick the look and the photos yourself and build it now.",
		expect_any=("generate_page",),
	),
	Scenario(
		"portfolio-designer",
		"Make a portfolio site for Ananya Rao, an independent product designer in Bengaluru who designs "
		"payment and savings flows for fintech apps. Show three case studies (a UPI checkout redesign, "
		"onboarding for a savings app, a lending dashboard), how she works, and a contact section. Pick "
		"the look and the photos yourself and build it now.",
		expect_any=("generate_page",),
	),
	Scenario(
		"portfolio-photographer",
		"Make a portfolio for Kabir Sethi, a documentary photographer in Kolkata. His two series are "
		"Tram Lines, on the city's last tram routes, and Monsoon Markets. Show the series, a short bio, "
		"commissions, and contact. Pick the look and the photos yourself and build it now.",
		expect_any=("generate_page",),
	),
	Scenario(
		"portfolio-developer",
		"Make a personal site for Riya Menon, a backend engineer in Pune who writes about Postgres "
		"internals. Show her open-source projects (pgwatch-lite, and a query-plan visualiser), her "
		"writing, two conference talks, and contact. Pick the look yourself and build it now.",
		expect_any=("generate_page",),
	),
	Scenario(
		"portfolio-3d",
		"Make a portfolio for Ishaan Kapoor, a 3D motion designer in Mumbai. The hero is an interactive "
		"3D piece that visitors drag to explore; then selected work (title sequences, product films), "
		"the kinds of clients he works with, and contact. Pick the look yourself and build it now.",
		expect_any=("generate_page",),
		runtime=True,
	),
)
