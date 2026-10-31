# Changing Bob's instructions

Bob's instructions reach the model through four homes. Every new or changed instruction goes in the narrowest home that is reliably present when it matters.

| Home | Where | Reaches the model | Holds |
|---|---|---|---|
| Core prompt | `Prompts.AGENT_SYSTEM` in `prompts.py` | every round of every turn | identity, voice, honesty rules, the one-line tool router, styling mechanics every edit uses, AI tells, memory |
| Skill | `skills/<name>.md` | when the loop attaches it for a state it can see (`AgentRunner.build_skill_context`), or when the model calls `read_skill` | a playbook for one kind of work that only some turns need |
| Tool description | the tool's `description` and parameter docs | every round, inside the tool schemas | what the tool does and takes |
| Tool result | the string a server tool returns | right after the call | what to do now that the tool ran (`preview_page`'s review rubric is the model) |

`Prompts.GENERATION_YAML` is a fifth, separate prompt: only the `generate_page` step sends it (`agent/artifact.py`).

## Placing an instruction

1. Find which turns need it, from data: each assistant `Builder AI Message` carries `metadata_json.debug.trace`, the tools of every round. Count on frappe.io and the dev sites; dev sites over-represent full builds.
2. Most turns need it: core prompt. Only after a tool runs: that tool's result. One kind of work: a skill.
3. A skill whose need the loop can see (an empty page, a component on the page) is attached in `build_skill_context`. A skill only the model can recognise the need for is read with `read_skill`, and its frontmatter `description` names the case that should trigger the read: it is the one line the core prompt carries for it (`Skills.index`).
4. Say it once. Search `prompts.py`, `skills/` and the tool descriptions for the same rule before adding it, and move or merge instead of restating.

Done when the instruction lives in exactly one place and the core prompt grew by at most a pointer line.

## Writing it

- Write specifications: the model obeys a concrete number or a named device ("the largest text is at least 3.5x the body") and drifts past advice ("vary structure first"). Numbers steer hard both ways, so change them on eval evidence.
- Prompt the behaviour you want. A ban drags the banned thing into context; pair any hard ban with its replacement.
- A rule a program can check becomes a check: add it to `eval/measures.py`, return its findings in a tool result, then delete the prose that argued for it.
- Skills cover phases and mechanisms of work (a new page, components, forms). A per-business-type playbook (portfolio, Aug 2026, `694110ef`) did not lift builds above the base rules and was removed in `7b52cd97`.
- Taste moves; it is not deleted. Hallmark's eval (github.com/nutlope/hallmark, `eval/README.md`) gave open models 96 lint failures with its short floor alone against 11 with the full guide.
- A skill the model must choose to read is a coin flip: Impeccable measured 55% load recall for its own skill on Sonnet. Anything page quality depends on is attached by state or carried by a tool result. The reverse slip happens too: models call `read_skill` for a skill the loop already attached, so `read_skill` answers those with one line, not a second copy.

## Measuring a change

Every change to a prompt, skill, tool description or tool result runs the eval on the code before and after it. The eval drives real turns on scratch pages, so the site needs a connected provider and running redis.

    bench --site builder.test execute builder.ai.eval.run --kwargs "{'model': 'codex/gpt-6-luna', 'fixture': '<a designed page>', 'label': 'before', 'repeat': 3}"
    bench --site builder.test execute builder.ai.eval.run --kwargs "{... 'label': 'after' ...}"
    bench --site builder.test execute builder.ai.eval.compare --kwargs "{'a': '<before dir>', 'b': '<after dir>'}"

To run the before side from another checkout, prefix the command with `PYTHONPATH=<that checkout>`; Python then imports its `builder` package. Leave a checkout alone while an eval runs from it: a commit's pre-commit hook stashes unstaged edits for a moment, and a run that imports during that moment measures the old code.

Done when no scenario passes fewer times than before, median prompt tokens did not rise without a reason, and the build scenarios' page measures held: photos, words and font sizes not down; micro labels, eyebrow headings, gradient text, dashes, stock phrases and missing mobile fallbacks not up. A change aimed at a behaviour adds a scenario for it to `SCENARIOS` in `eval/__init__.py`.

## Keeping the cache warm

- The tool list and the core prompt are the cached prefix (tools, then system, then history). Keep them byte-stable across rounds and turns: no per-page, per-user or time-varying text, and the same tool list for the whole turn.
- Per-turn text (page context, an attached skill, saved memory) goes in the context message after the history.
- Tool results are not saved into the chat history, so a skill read this turn is gone next turn. A multi-turn flow tells the model to read the skill again on the turn it continues.

## Next to move (Oct 2026)

Every round sends about 77KB of fixed instructions: the core prompt (35.8KB) and 35 tool schemas (~41KB). In 77 traced frappe.io turns, at most 2 built a page and 44 edited blocks. Candidates, each needed by under 6% of turns: component instances and client scripts (~6KB), forms with data scripts and bindings (~3KB), site matching and detail routes (~3KB), dark-mode images (~2KB). The `connect_form` and `update_blocks` descriptions repeat their core-prompt bullets nearly word for word; keep one copy.
