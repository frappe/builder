# Optional centralized stock library for Bob

Bob supports **Magnific (formerly Freepik) stock discovery** with one server-side
site key. It searches photographs, excluding AI-generated content. It does not
purchase, license, download, or publish Magnific assets. Results are previews
with an original library link; acquiring and importing the original is manual.

## Setup

An administrator configures these entries through the site's normal private
configuration management:

```json
{
  "bob_stock_provider": "magnific",
  "magnific_api_key": "<your organization API key>"
}
```

Both entries are required. Keep the key server-side, outside source control and
chat. Obtain it from the organization's Magnific API settings and configure
appropriate provider-side access restrictions and usage caps. No configuration
or account changes are made by installing this adapter. Remove
`bob_stock_provider` to disable it. Existing `pexels_api_key` and
`unsplash_access_key` settings continue to work; Openverse needs no key.

`search_images` accepts `provider: "auto" | "magnific" | "pexels" | "unsplash" |
"openverse"`. Auto tries configured Magnific, Pexels, Unsplash, then Openverse,
stopping at the first nonempty result. An explicit provider never silently
substitutes another library. Choose a free provider to avoid manual paid-stock
import. Each search returns at most six results and uses a ten-second timeout.

## Preview and import workflow

1. Search and display the thumbnail, original library link, credit, and
   **preview only** status. Retain the exact `magnific:<resource-id>` identity
   when the user chooses a result.
2. Open that result's `source_url` in the library. Review its applicable terms
   and download/license the chosen original using the appropriate account.
   Retain any license evidence supplied by the library.
3. Upload the licensed file through Builder's existing file upload and select
   that uploaded original for the page. The upload does not automatically prove
   a license or upgrade the earlier preview's status.

Magnific records have `url: ""`, `preview_only: true`,
`requires_acquisition: true`, and `license_status: "preview_only"`.
`thumb` and `preview_url` hold the search image; `source_url` holds the original
library page. `provider_licenses` preserves the provider's license metadata,
**not evidence that this site acquired a license**. Preview dimensions describe
the preview, not the downloadable original. Neither the thumbnail nor the
source page may become `img src`, a background, a meta image, or a generation
asset. Selecting a preview never authorizes an automatic purchase.

## Verified public API contract

The following official documentation was read without authentication on
2026-11-01. No authenticated or paid endpoint was called.

- [Search OpenAPI](https://docs.magnific.com/api-reference/resources/get-all-resources.md):
  `GET https://api.magnific.com/v1/resources` with `x-magnific-api-key`.
  Parameters: `term`, `limit`, `order=relevance`,
  `filters[content_type][photo]=1`, `filters[ai-generated][excluded]=1`, and
  optional `filters[orientation][landscape|portrait|square]=1`.
  The response's `data[]` supplies integer `id`, `title`, original resource
  `url`, `author.name`, `licenses[]`, and `image.source.{url,size,key}`.
  The adapter treats the search image as preview-only, regardless of license tier.
- [Download OpenAPI](https://docs.magnific.com/api-reference/resources/download-a-resource.md):
  `GET /v1/resources/{resource-id}/download`, optionally `image_size` (small,
  medium, large, original, or a supported pixel size). It returns
  `data.filename`, `data.url`, and optional `data.signed_url`; the schema
  explicitly describes `signed_url` as a **preview** URL.
- [Format download OpenAPI](https://docs.magnific.com/api-reference/resources/download-resource-by-id-and-format.md):
  `GET /v1/resources/{resource-id}/download/{resource-format}` returns a
  `data[]` list of download objects. Neither download endpoint is implemented.
- [Pricing](https://docs.magnific.com/pricing): Premium, Premium+ and Pro stock
  downloads are capped at 100 per day without consuming credits. Business and
  Enterprise stock downloads consume credits with no daily cap. Do not assume
  a web subscription's unlimited allowances cover API consumption. This adapter
  does not estimate charges or promise search pricing.
- The [stock overview](https://docs.magnific.com/api-reference/resources/images-and-templates-api)
  points to the [terms](https://www.magnific.com/legal/terms-of-use#api-services).
  The terms were accessible and link to separate
  [API Services terms](https://www.magnific.com/legal/api-services); fetching the
  latter returned HTTP 403. An account's complete licensing entitlement and
  authorization to redistribute originals were therefore **not verified**.

A search result's license URL is not a license receipt. The public endpoint
schemas alone do not supply a complete, budgeted acquisition workflow with
user approval and account-specific rights. Consequently there is no paid
acquisition tool, budget debit, or paid download path in this implementation.
Supporting one later requires a separate explicit user action and server-side
entitlement, budget, and license-evidence handling.

## Unsplash selected use

The exported `acquire_asset({"asset_id": "unsplash:<original-id>"})` tool
records Unsplash's required download event. It accepts only an asset already
persisted in this page's design brief with `selected: true`, checks page write
permission, locks the page record, and requires `unsplash_access_key`. Model
arguments cannot supply a replacement URL or resource ID outside the inventory.

It calls the saved `links.download_location` only after verifying its HTTPS
host and `/photos/<original-id>/download` path, without following redirects.
Success persists `download_tracked: true` and `requires_acquisition: false`.
Subsequent calls for the same saved page asset do not repeat the event. Search
and displaying choices never trigger tracking. This is a free selected-use
tracking event, not a license purchase or file download; Magnific IDs are always
refused with instructions for manual import.

The original `photo.urls.regular` hotlink, including its `ixid`, is preserved.
The tracking response is not substituted as an image URL. Credit/source links
include `utm_source=frappe_builder&utm_medium=referral`; UI and generated pages
must retain linked photographer and Unsplash attribution. See the official
[API guidelines](https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines)
and [download tracking documentation](https://unsplash.com/documentation#track-a-photo-download).

External tracking and the local database do not share a transaction. A network
timeout after provider acceptance or a later database rollback can produce a
duplicate event on retry; persistent success prevents ordinary repeated calls.
No exactly-once guarantee is claimed.

## Integration and offline checks

`images.TOOLS` exports `search_images` and `acquire_asset`. The design tool group
must activate both. The API records explicit user selections by original ID.
The brief merges by ID, preserves selected originals and acquisition metadata,
and bounds search inventory to twelve entries. Generation must exclude assets
with `preview_only` or `requires_acquisition`, or without a page URL. The image
picker must retain preview status, original link, license, and attribution
metadata; a new search must not overwrite the chosen original.

Run with the existing bench Python, without initializing a site:

```sh
<bench>/env/bin/python -m unittest builder.ai.test_assets -v
```

Tests replace HTTP and configuration access, forbid real network requests, and
use dummy keys. They cover the documented search contract, explicit opt-in,
fallbacks, preview-only output, permission/selection restrictions, tracking URL
validation, and preservation of the selected original across search and later
turns. Production credentials, account entitlement, live provider responses,
and visual/manual import behavior are outside this offline validation.
