---
description: "Use when writing, editing, or reviewing AI/LLM features: prompt engineering, litellm calls, block YAML compression, AI session management, task classification, or the AIPageGeneratorModal. Covers conventions for extending the AI generation system."
applyTo: "builder/ai_page_generator.py,frontend/src/components/AIPageGeneratorModal.vue,builder/builder/doctype/builder_ai*/**"
---

# AI / LLM Integration — Frappe Builder

## Stack

- **litellm** ≥ 1.83.7 — multi-provider LLM abstraction (OpenAI, Anthropic, etc.)
- Configured via `BuilderSettings.ai_api_key` and `BuilderSettings.ai_model`
- All AI backend logic lives in `builder/ai_page_generator.py`
- Frontend UI: `frontend/src/components/AIPageGeneratorModal.vue`

---

## Task Classification

Every request is classified as `"simple"` or `"complex"` before calling the LLM:

```python
TASK_PARAMS = {
    "simple": {"max_tokens": 1000, "temperature": 0.5},
    "complex": {"max_tokens": 22000, "temperature": 0.7},
}
```

- **Simple**: Style tweaks, text rewrites, image replacement — fast, low token budget
- **Complex**: Full page generation, large structural changes — higher budget and temperature

When adding new task types, classify them into one of these two tiers. Do not add a third tier.

---

## System Prompts

System prompts are module-level string constants in `ai_page_generator.py`. Keep them:
- Compact (every token counts)
- Precise about the expected output format (YAML only, no markdown fences)
- Explicit about schema constraints and edge cases

```python
MODIFY_PROMPT = (
    "You modify web sections in Frappe Builder's block system.\n"
    "Return ONLY valid and compact YAML array. No markdown, no explanations.\n\n"
    "# Schema\n"
    "el: str\n"
    "id: str  # MUST preserve existing\n"
    "style?: dict  # CSS-in-JS camelCase. Support hover:backgroundColor, active:color.\n"
    "c?: [el]\n"
    "attrs?: dict\n"
    "text?: str\n"
    "m_style?: dict\n\n"
    "Rules: Preserve ALL existing 'id' values. Return COMPLETE structure. "
    "Use %, rem for widths. Top-level sections MUST be 100% width.\n"
    "Gradients: ALWAYS use 'backgroundImage' NOT 'background'. Quote gradient values.\n"
    "Example: backgroundImage: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'\n"
    "Omit any key whose value is empty, null, or {}."
)
```

---

## Block Compression for LLM

Before sending to the LLM, blocks are compressed to compact YAML via `compress_block_to_yaml()`. This reduces token usage significantly.

**Compressed block schema** (YAML keys):
| YAML key | Block field |
|----------|------------|
| `el` | `element` |
| `id` | `blockId` (MUST preserve) |
| `name` | `blockName` |
| `style` | `baseStyles` |
| `m_style` | `mobileStyles` |
| `t_style` | `tabletStyles` |
| `attrs` | `attributes` |
| `c` | `children` |
| `text` | `innerText` |

```python
from builder.utils import to_compact_yaml

compressed = compress_block_to_yaml(blocks)  # list of block dicts → YAML string
```

---

## litellm Call Pattern

```python
import litellm

litellm.drop_params = True  # ignore unsupported params per provider

def call_llm(
    system_prompt: str,
    user_message: str,
    task_type: str = "complex",
) -> str:
    settings = frappe.get_cached_doc("Builder Settings", "Builder Settings")
    response = litellm.completion(
        model=settings.ai_model,
        api_key=settings.ai_api_key,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        **TASK_PARAMS[task_type],
    )
    return response.choices[0].message.content
```

- Always read `ai_model` and `ai_api_key` from `BuilderSettings` — never hardcode
- `litellm.drop_params = True` must remain set at module level
- Do not expose the API key to the frontend

---

## Output Parsing

The LLM returns YAML. Parse it and convert back to block dicts:

```python
import yaml

def parse_llm_blocks(raw: str) -> list[dict]:
    # Strip any accidental markdown fences
    raw = raw.strip().removeprefix("```yaml").removeprefix("```").removesuffix("```").strip()
    blocks = yaml.safe_load(raw)
    if not isinstance(blocks, list):
        frappe.throw("AI returned unexpected format")
    return blocks
```

Always use `yaml.safe_load` — never `yaml.load`.

---

## AI Session & Memory Doctypes

- `BuilderAISession` — tracks conversation turns per page edit session
- `BuilderAIMemory` — stores embeddings or distilled context (currently minimal)

When extending AI session management:
- Link sessions to `BuilderPage` via `page` link field
- Store each turn as a child row or separate doc
- Do not store API keys or raw user PII in session records

---

## Frontend Integration

The modal (`AIPageGeneratorModal.vue`) follows this flow:

1. User types a prompt
2. Frontend calls backend resource:
   ```typescript
   const aiResource = createResource({
       url: "builder.ai_page_generator.modify_blocks",  // example endpoint
       method: "POST",
       auto: false,
   });
   await aiResource.fetch({ page: pageId, prompt: userPrompt, blocks: compressedBlocks });
   ```
3. Backend returns YAML → parsed → merged into block tree
4. Canvas re-renders reactively

**UX rule**: Show a loading state on the button and disable the input while the request is in flight. On error, show `toast.error()` with the backend message.

---

## Security

- Never expose `ai_api_key` in API responses or frontend state
- All AI endpoints must have `@frappe.whitelist()` + `@has_page_write()` (or equivalent)
- Validate and sanitize LLM output before merging into the block tree — never trust raw YAML without schema validation
- Never `eval()` or `exec()` LLM-returned code strings; use `safe_exec()` from Frappe if script execution is needed

---

## Adding a New AI Task

1. Define a system prompt constant at the module level in `ai_page_generator.py`
2. Classify the task as `"simple"` or `"complex"` in `TASK_PARAMS`
3. Create a `@frappe.whitelist()` endpoint function that:
   - Checks `is_ai_enabled()` or `builderSettings.ai_api_key`
   - Compresses blocks if needed
   - Calls `litellm.completion()` with the right prompt
   - Parses and returns the result
4. Add a frontend button/flow in `AIPageGeneratorModal.vue` using `createResource`
