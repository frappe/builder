---
description: a person's own site (personal site, portfolio, homepage, about page): the friction card, premises to choose from, a mechanic built on links, and a memorability-first review
---
# Personal site

A memorable personal site has a **premise**: one sentence, *"My site is a ___ where you ___"*, drawn from something only this person does, makes or obsesses over. The premise is the skeleton. It decides structure, interaction and look; palette and type serve it. The other route is overwhelming real substance (years of writing or work, where the plain list is the site); for someone with that, the premise can be as quiet as the shape of that list.

This skill replaces new-page's steps (2) "what it holds" and (3) "layout direction" for a person's own site. A section list (about, projects, writing, contact) is the thing it exists to avoid. new-page's build order, typography rule and self-review still apply.

## 1. Friction card
read_url whatever they point at first (their site, GitHub, blog, a talk), so the card asks only what's missing. Then one present_ui card, submitted at the end, skipping any step the request or the reads already answer:
1. Name, what you do, and who should visit (input).
2. What people tease you about, or what you do excessively (input).
3. The hard problem at the centre of your work, as you'd explain it to a neighbour (input).
4. Something you made that failed, and why you still think about it (input).
5. A place or object that keeps coming back in your life, and what you make outside work (input).
6. What a visitor should do after leaving (input).
7. Something only you could have made, to put on the site: a scan, a sketch, your handwriting, your own photos, a voice note. Describe it, then drop the file into the chat (input).
8. How far to go: 1 quiet but unmistakably mine · 2 · 3 nobody has seen this (choices).
9. Anything that must stay off the site: people, places, where you live (input).

Close with {kind:'actions', buttons:[{label:'Show me ideas'}]}. Keep their exact words; the copy is built from them, and you edit rather than ghostwrite.

## 2. Premises
Privately write at least fifteen, each naming its source fact, what the visitor does, and the first screen. Run every generator:
- **Literal:** the site performs what they do (an agents researcher's header is a live colony of agents; a text-game researcher's homepage is a text adventure).
- **Medium swap:** their work recast as a broadcast, board game, shop, instrument, museum, desktop, zine, radio, map or menu.
- **Native format:** a document from their life becomes the interface: ledger, recipe card, setlist, lab notebook, ticket, form, scorecard, syllabus.
- **Problem as play:** the hard problem at the centre of their work becomes the visitor's puzzle.
- **Threshold:** the visitor does something to get in: knock, tune, deliver, solve, wait.
- **Place:** a real place from their life is the interface: a walk, a map, a room, a desk drawer.
- **Time:** the site is their day, year or season, and changes with it.
- **Inversion:** break a convention of their field on purpose.
- **Collection:** their obsession catalogued at full density.

Eliminate a premise when the sentence a stranger would use the next day is "a website/portfolio/page with sections about…", when it would fit another person in the same job, when it needs content they don't have, or when it turns other people into props or reveals what they asked to keep off the site. Keep three survivors that differ in medium (for example a game, a document and a place), one of them a step bolder than their answer to step 8.

## 3. Let them choose
One present_ui choices card: three tiles named like the premise's own object ('The Pacing Map', 'Tonight's Specials Board'), never an adjective pair. Each tile carries the "My site is a ___ where you ___" sentence, what the first screen shows, and `colors` drawn from the premise's world and their photos. Add a last option, "None of these, here's why" (input). A rejection sends you back to step 2 carrying what they said; a mix ("the map, but end like the second one") is a normal answer, so build it without re-asking.

## 4. The mechanic, in the brief
Before generate_page, write the scene list: what a visitor does from the first screen to the end, and where every content item lives inside it. Add the plain ways in: an escape hatch ("Everything, plainly": a section at the foot of the page that links every content item in one list) and the phone version.

The mechanic is links and `:target`, with no script, so it works with JS off:
- Every scene and panel is a real block with an `[id=…]`; every choice is an `a [href=#<id>]`.
- A closed panel starts hidden, and its own `:target{…}` group opens it while the URL names its id: `div.ks-sheet [id=no-14-red] {display:none;position:fixed;…} :target{display:flex}`. One panel is open at a time, the link can be shared, and Back closes it.
- A panel lies over the page (position:fixed, under no ancestor with a transform or filter, which would trap it) and ends with a link back to where it opened (`#map`). On phones, sheets stay at or under 75vh so the scene shows above them.
- Clickable regions over an image (a scanned map, a photo) are `a` blocks inside the image's position:relative wrapper, placed and sized with left, top, width and height in %, so they stay on their region at every width. Each names its region in its text or `[aria-label]`.
- The brief names every id, link and open style, so the layout carries them.

set_page_script is optional polish on top: Escape closes the open panel, focus moves to its heading, `sessionStorage` remembers what they opened. Every item stays reachable without it.

Other people appear only as they'd agree to, and the person's home stays unlocatable. A hand artifact they haven't sent yet is a marked placeholder in its real place, never an imitation of their hand.

## 5. The look comes from the premise's world
Take materials, printed forms, signage and handwriting from that world (a courier's slip, a shop counter, graph paper and pencil), plus their own photos, unretouched. Sample colours from their images, and lock palette and fonts with set_design_token. Each choice in the brief names its source in the premise or the person.

## 6. Review after preview_page
Run these in order. A failure in 1–3 sends you back to the premise, not to the styling.
1. **One sentence:** write the sentence a stranger would use tomorrow. It names the premise and something true about them. "A clean portfolio with photos" fails.
2. **Swap:** with another person's name and photos, the site stops making sense.
3. **Consent:** nothing they asked to keep off; other people only as they'd agree.
4. **Hand:** their artifact is on the page, or a marked placeholder sits where it goes.
5. **Mechanic:** the screenshot shows panels closed, so check the page itself: every `#` link names an id on the page, every panel links back, the ending is reachable, the escape hatch is complete, and the phone version works.
6. **Substance:** every item is real or a marked placeholder; no filler summaries and no links to nowhere.
7. **Voice:** every line is something they'd say.
8. **Polish:** new-page's self-review.

Then tell them, in plain words, what's a placeholder and what to send next.
