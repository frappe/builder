# Bob images and stock assets

Direction previews are **desktop WebP screenshots of real editable Builder blocks**. Choosing a direction promotes those same blocks. Rendering a layout does not call an image model. Optional generated artwork is separate; a concept stays preview-only and cannot become the whole published page. Responsive DOM checks remain available without generating a mobile preview.

## Discovery

`search_images` accepts `auto`, `magnific`, `pexels`, `unsplash`, or `openverse`. Auto tries configured Magnific, Pexels, Unsplash, then Openverse, stopping at the first nonempty result. Explicit providers never silently substitute. Responses contain at most six candidates with stable IDs, preview/original URLs, source, credit and license metadata.

Configure keys privately through normal site configuration:

```json
{
  "bob_stock_provider": "magnific",
  "magnific_api_key": "<organization API key>"
}
```

Existing `pexels_api_key` and `unsplash_access_key` work; Openverse needs no key. Remove `bob_stock_provider` to disable Magnific discovery. API search/download limits still apply.

Magnific search results are **preview only**, regardless of license tier: `url: ""`, `preview_only: true`, `requires_acquisition: true`. Source/thumbnail/license URLs are not evidence of acquisition. Page mutation and generation reject known previews. Selected IDs survive later searches, chats and reloads.

## Optional paid stock acquisition

Automatic Magnific photograph acquisition requires these administrator-supplied settings:

```json
{
  "bob_media_budget_usd": 5,
  "bob_media_daily_budget_usd": 20,
  "bob_stock_entitlement": {
    "approved": true,
    "account_reference": "<entitled organization/account>",
    "license_url": "<applicable account/API license reference>",
    "max_download_cost_usd": 1
  }
}
```

Amounts are examples, not provider price quotes. Configure conservative ceilings and provider-side limits. `bob_media_budget_usd` currently applies **per Builder page**, including pages in a multipage project; the daily cap applies across the site. Reservations estimate maximum cost, not verified invoices.

1. Shortlist an exact asset. `acquire_paid_asset` presents an acquisition confirmation.
2. Approval checks page permission, selection and configured entitlement, then commits a pending receipt before the external request.
3. It calls `GET https://api.magnific.com/v1/resources/{id}/download` with `image_size=original`. Only `data.url` supplies the original; `signed_url` is documented as a preview.
4. The downloaded raster becomes a local WebP delivery rendition. Its source ID, provider response, entitlement reference, credit and receipt persist.
5. An ambiguous failure leaves the reservation pending. Bob will not automatically charge again. After five minutes an administrator can reconcile it in **Project → Spending** from billing/support evidence: not charged, original recovered, or charged without an asset. Late provider responses cannot overwrite reconciliation.

The recorded status is `configured_account_entitlement`. The adapter **does not independently verify legal entitlement or issue a license certificate**. API Services terms returned HTTP 403 during the original review; account/multi-user redistribution rights require provider verification. Without this configuration, use manual license/download/upload or another library. No paid stock endpoint was called during implementation validation.

Public contracts reviewed on 2026-11-01: [search](https://docs.magnific.com/api-reference/resources/get-all-resources.md), [original download](https://docs.magnific.com/api-reference/resources/download-a-resource.md), [pricing](https://docs.magnific.com/pricing), [API Services terms](https://www.magnific.com/legal/api-services). Web subscription allowances do not establish API entitlement.

## Generated artwork and transformations

The current raster adapter uses OpenAI Images generations/edits. It is separate from the chat connection:

```json
{
  "bob_image_model": "<image model supporting low quality and WebP>",
  "bob_image_api_key": "<API key>",
  "bob_image_max_cost_usd": 1,
  "bob_media_budget_usd": 5,
  "bob_media_daily_budget_usd": 20
}
```

`generate_artwork` requests one 1024×1024 low-quality WebP draft. `source_asset` edits a selected acquired original. Identical page/prompt/model/source settings reuse a completed receipt before downloading source bytes or charging again. Provider usage is recorded when supplied; unknown actual cost stays null. Concepts stay private/preview-only. Provider billing and generation have mocked coverage, not a paid production acceptance test.

`transform_asset` creates cached focal crops, retaining source identity and attribution. No-derivatives licenses are rejected. Unsplash remains hotlinked; use CSS object-position rather than local transformations. `asset_contact_sheet` renders a bounded visual shortlist. Coherent art direction still requires model/user judgment.

## Uploads, references and attribution

Pasted uploads start private and undecided. **Project → Assets** offers reference/content/logo/product/team roles. References are excluded from generation's photo inventory. For page content, **Make available on published page** or `prepare_uploaded_asset` copies original bytes to a public page asset. Only its uploader or a System Manager may expose a private original. Reference-role placement is rejected even if the file was previously public.

Unsplash `acquire_asset` performs required selected-use download tracking, not a purchase. It validates the saved URL/ID and persists success. Hotlinks retain `ixid`; generated pages receive linked photographer/provider credits. A timeout after provider acceptance can duplicate tracking on retry; no distributed exactly-once guarantee is claimed. See [API guidelines](https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines) and [download tracking](https://unsplash.com/documentation#track-a-photo-download).

Openverse source/license/credit metadata remains attached. A catalog filter alone does not prove all rights to the depicted content. See [acceptance instructions](acceptance/README.md) for deterministic and live validation.
