# LODEX Turnkey Catalog + Retail Sourcing

## Objective

Turn LODEX from a service catalog into a design-to-delivery commerce workflow:

**design inspiration -> configurable concept -> sourced products/materials -> current availability/pricing -> LODEX markup -> delivery/install/fabrication -> turnkey quote/order**

The system should support categories such as premium dog houses, backyard offices, sheds/workshops, kids playhouses/tiny houses, remodeling packages, furnished rooms, outdoor kitchens, pergolas, and similar build/design offerings.

LODEX should be able to publish many concept designs even when they have not yet been physically built. These must be clearly labeled as concept/prototype designs until a real project exists.

## Product principles

1. A concept is a sellable specification, not just an image.
2. Customer-facing prices are LODEX prices. Do not expose internal acquisition cost or margin.
3. Retailer products are replaceable fulfillment options. A design should survive one SKU going out of stock.
4. Availability and price data must carry timestamps and source/provider metadata.
5. Prefer official APIs, affiliate/product feeds, approved catalogs, retailer APIs, or explicitly permitted integrations. Do not build a scraping dependency that violates retailer terms.
6. Never imply retailer endorsement, partnership, warranty, or authorization unless it actually exists.
7. Every generated concept must distinguish `CONCEPT` from `BUILT_PROJECT`.
8. Any customer quote using volatile third-party prices must have a validity window and substitution policy.

## Customer experience

Each concept page should eventually support:

- hero image/render
- concept name and category
- status badge: `Concept Design` or `Built Project`
- approximate dimensions
- intended use/customer profile
- included features
- configurable options
- estimated lead time
- three commercial modes where applicable:
  - Design Only
  - Build Only
  - Turnkey / Move-In Ready
- turnkey price or preliminary price range
- `Build this design` CTA
- `Customize this concept` CTA
- optional `Save/Favorite`
- product/material detail groups without exposing LODEX cost basis
- availability caveat and substitute-product language

For furnished/remodeled concepts, group included items by room/function rather than dumping an unstructured cart.

Example groups:

- structure / construction
- electrical / lighting
- flooring / surfaces
- furniture
- storage
- textiles
- decor
- appliances/equipment
- delivery
- assembly/install

## Core data model

Implement the smallest durable domain model first. Exact persistence mechanism should follow current LODEX backend conventions.

### Concept

Suggested fields:

```text
id
slug
name
category
summary
description
status: CONCEPT | BUILT_PROJECT | RETIRED
publication_status: DRAFT | PUBLISHED | ARCHIVED
width/length/height + unit (optional)
hero_media
source_design_prompt / provenance metadata (admin only)
base_labor_estimate
base_project_overhead
lead_time_min_days
lead_time_max_days
price_validity_hours
default_markup_policy_id
created_at
updated_at
published_at
```

### ConceptComponent

A design should refer primarily to requirements/components, not hard-code one retailer SKU.

```text
id
concept_id
group
name
description
quantity
unit
required: bool
selection_mode: FIXED | SUBSTITUTE_ALLOWED | CUSTOMER_CHOICE
requirement_spec_json
preferred_offer_id (nullable)
sort_order
```

Examples of `requirement_spec_json`:

```json
{
  "type": "desk",
  "minWidthIn": 60,
  "maxWidthIn": 76,
  "finish": ["oak", "walnut", "light wood"],
  "style": ["modern", "minimal"]
}
```

or

```json
{
  "type": "roofing",
  "coverageSqFt": 120,
  "material": ["architectural shingle", "metal"],
  "weatherRating": "exterior"
}
```

### Retailer

```text
id
key
name
homepage_url
integration_type: API | AFFILIATE_FEED | PRODUCT_FEED | MANUAL | OTHER
active
terms_notes
last_sync_at
```

Initial retailer targets for adapters/configuration:

- IKEA
- Target
- Walmart
- Crate & Barrel
- Arhaus

Architecture must make Home Depot, Lowe's, Wayfair and other sources easy to add later.

### Product

Canonical product identity independent of a single live offer.

```text
id
retailer_id
retailer_product_id
brand
name
description
product_url
image_url
category
attributes_json
active
created_at
updated_at
```

### ProductOffer

Current purchasable state. Keep history or snapshots rather than overwriting all evidence.

```text
id
product_id
sku
currency
regular_price
sale_price
availability_status: IN_STOCK | LOW_STOCK | OUT_OF_STOCK | UNKNOWN
available_quantity (nullable)
location_scope / postal_code (nullable)
fulfillment_json
source_timestamp
fetched_at
expires_at
raw_source_ref (non-secret)
```

### MarkupPolicy

Support markup without hard-coding percentages in UI code.

```text
id
name
scope: GLOBAL | CATEGORY | RETAILER | CONCEPT | COMPONENT
scope_key
method: PERCENT | FIXED | TIERED
value / tiers_json
minimum_margin_amount
active
```

Markup is computed server-side.

### QuoteSnapshot

When a user requests or accepts a quote, freeze the commercial assumptions.

```text
id
concept_id
customer/lead_id
currency
retail_subtotal
procurement_markup
labor
freight_delivery
assembly_install
project_management
contingency
tax_if_applicable
total
valid_until
component_snapshot_json
pricing_snapshot_json
created_at
```

Do not reconstruct an old quote from today's retailer prices.

## Pricing engine

Implement pricing as explicit server-side functions/services with tests.

Conceptual formula:

```text
selected merchandise/material acquisition basis
+ sourcing/procurement markup
+ freight/delivery/logistics
+ assembly/install labor
+ fabrication/construction labor
+ project management / overhead
+ contingency where configured
+ applicable taxes
= LODEX customer price
```

Requirements:

- never accept client-supplied markup values as trusted inputs
- all monetary arithmetic uses decimal/fixed-precision values, never binary floating point
- support percentage and fixed markup
- support category/retailer/concept overrides
- keep internal cost breakdown admin-only
- customer endpoints return only permitted commercial totals/details
- store price source time and quote validity

## Product substitution engine

Do not couple a concept to one SKU.

A component may have:

- preferred offer
- approved alternatives
- requirement-based alternatives

When preferred inventory is unavailable or stale:

1. find active offers satisfying the component requirement
2. rank by compatibility
3. rank by availability
4. rank by price/value
5. preserve design intent/style where metadata allows
6. flag material price delta
7. require admin/customer approval when substitution materially changes appearance, dimensions, function, or total price beyond configured tolerance

Start deterministic. Do not require an LLM for core substitution logic. An LLM may assist in enrichment/ranking later, but server-side validation remains authoritative.

## Retail integration boundary

Create a provider interface so retailer-specific code stays isolated.

Suggested conceptual contract:

```ts
interface RetailCatalogProvider {
  retailerKey: string;
  searchProducts(query, context): Promise<ProductSearchResult[]>;
  getProduct(externalId, context): Promise<ProductDetails | null>;
  getOffers(externalId, context): Promise<ProductOffer[]>;
  healthCheck(): Promise<ProviderHealth>;
}
```

Backend language/types should follow the existing codebase rather than forcing TypeScript into Python services.

Provider context should be capable of carrying postal code/location because stock, shipping, pickup, tax and pricing may vary by market.

### First implementation

Do **not** block the platform waiting for five live retailer integrations.

Ship an adapter architecture plus a `manual/catalog fixture` provider that lets admins enter/import products and offers. Build UI and pricing against that stable contract. Then add retailer providers one at a time when a legitimate data source is available.

## Admin workflow

Add an admin experience for:

- create/edit concept
- set category/status/publication state
- attach media
- create component groups
- define component requirements
- search/select preferred retailer offers
- approve alternatives
- configure pricing/markup policy
- preview internal cost vs customer price
- publish/unpublish
- refresh stale offers
- duplicate a concept into a new variant

Important: internal cost, markup and supplier notes must never appear in public concept payloads.

## Daily design factory

The architecture should support adding at least one new design per major category per day without developer involvement.

A design generation/import pipeline should eventually produce a draft containing:

- concept name
- category
- description
- dimensions
- feature list
- visual/render references
- component requirements
- likely materials/furnishings
- preliminary price assumptions
- SEO title/description
- social caption suggestions

Generated concepts remain `DRAFT` until reviewed/published. Do not auto-claim that generated imagery depicts completed LODEX work.

Recommended major category seeds:

- Dog Houses
- Backyard Offices
- Kids Playhouses / Tiny Houses
- Sheds / Workshops
- Outdoor Kitchens / Bars / Pergolas
- Room Remodel + Furnish
- Rental / Airbnb Turnkey Packages

The goal is a large searchable inspiration catalog. Most concepts may remain prototypes; analytics should reveal which deserve real prototypes and inventory investment.

## Analytics events

Instrument at minimum:

```text
concept_impression
concept_view
concept_save
concept_customize_start
concept_build_cta
concept_quote_request
concept_quote_created
concept_quote_accepted
concept_deposit_started
concept_deposit_paid
component_substitution_viewed
```

Include `concept_id`, category, source/referrer and variant where safe. Never put secrets or sensitive customer content in analytics events.

Use conversion data to rank concepts and identify which prototypes should actually be built.

## SEO

Each published concept gets a stable canonical route such as:

```text
/designs/:category/:slug
```

Requirements:

- unique title/meta description
- semantic headings
- descriptive image alt text
- OpenGraph metadata
- sitemap inclusion
- structured data only where accurate
- concept/built-project language must be truthful
- avoid generating thousands of near-duplicate thin pages

## API outline

Exact routes should match existing backend conventions. Suggested capabilities:

Public:

```text
GET /api/concepts
GET /api/concepts/{slug}
POST /api/concepts/{id}/quote-preview
POST /api/concepts/{id}/quote-request
```

Admin:

```text
POST/PATCH /api/admin/concepts
POST/PATCH /api/admin/concepts/{id}/components
GET /api/admin/retail/search
POST /api/admin/retail/refresh
GET/POST/PATCH /api/admin/markup-policies
POST /api/admin/concepts/{id}/publish
```

Do not expose arbitrary retailer proxy endpoints to anonymous users.

## Security / reliability

- retailer API keys/tokens only in server-side secret storage
- never expose provider credentials to frontend
- validate remote URLs and data before storing/rendering
- rate-limit refresh/search endpoints
- cache retailer results with explicit staleness
- graceful provider failure: a retailer outage must not break concept pages
- log provider errors without secrets
- sanitize imported product text/HTML
- admin auth follows existing LODEX auth boundary
- public price should clearly indicate when it is preliminary vs quote-locked

## Phase plan

### Phase 1 — Domain + manual catalog

Deliver:

- schema/models/migrations
- concept CRUD
- concept components
- retailer/product/offer models
- markup policies
- quote pricing service
- manual/fixture provider
- public concept list/detail
- admin concept editor minimal viable flow
- tests

Acceptance:

- admin can create a concept and attach several components/products
- customer sees a concept page and turnkey price
- internal cost/markup is absent from public payload
- quote snapshot stays unchanged when a product's current price later changes

### Phase 2 — Inventory-aware fulfillment

Deliver:

- retailer provider interface
- first legitimate live provider/feed
- offer refresh/cache
- stale price indicators
- availability by location where provider permits
- deterministic substitutions

Acceptance:

- preferred out-of-stock SKU can be replaced with an approved alternative
- price delta is surfaced internally and applied correctly
- provider outage does not take down the concept page

### Phase 3 — Design factory + analytics

Deliver:

- draft concept generation/import workflow
- admin review/publish queue
- SEO routes/metadata/sitemap
- analytics events and ranking dashboard
- duplicate/variant workflow

Acceptance:

- non-developer can publish a reviewed concept without code changes
- conversion funnel is measurable per concept
- `CONCEPT` vs `BUILT_PROJECT` is visible and enforced

### Phase 4 — Turnkey checkout/invoicing

Integrate with the existing LODEX lead/estimate/payment workflow rather than building a parallel CRM.

Deliver:

- quote acceptance
- deposit/payment handoff
- procurement checklist
- substitution approval
- order/build status
- invoice/estimate export/integration as appropriate

## Instructions for Codex / Copilot / KiloCode

When implementing this feature:

1. Read repository `AGENTS.md` and follow it exactly.
2. Start from current `origin/main`; do not develop against a stale checkout.
3. Inspect the existing backend persistence, auth, lead, estimate, pricing and frontend routing patterns before choosing libraries or creating parallel infrastructure.
4. Implement Phase 1 first. Do not attempt five retailer integrations in one PR.
5. Prefer small reviewable PRs with migrations + tests.
6. Do not rewrite unrelated intake functionality.
7. Do not introduce a second frontend framework; the current frontend is Vue/Vite.
8. Do not expose internal costs or markup in public API responses, rendered HTML, analytics payloads, source maps, logs, or client state.
9. Use fixed-precision money arithmetic.
10. Treat all live retailer pricing as volatile and timestamped.
11. Any retailer integration must document its data source and allowed usage in code/docs.
12. If an official integration cannot be obtained, leave that provider unimplemented and use the manual provider; do not silently add brittle/unauthorized scraping.
13. Add tests for pricing, quote snapshot immutability, public/admin serialization boundaries, substitutions and provider failure.
14. Run the repository validation commands from `AGENTS.md` and report exactly what ran.

### Suggested PR sequence

PR 1: `feat/catalog-domain`
- persistence models/migrations
- backend services
- pricing engine
- serialization boundaries
- unit tests

PR 2: `feat/concept-catalog-ui`
- public list/detail routes
- admin minimal editor
- manual product/offer management
- tests/build

PR 3: `feat/retail-provider-interface`
- provider contract
- caching/staleness
- manual provider refactor
- first legitimate live provider only if credentials/feed are available

PR 4: `feat/concept-substitutions`
- deterministic matching
- availability handling
- approval/price-delta workflow

PR 5: `feat/design-factory-analytics`
- draft generation/import
- publishing controls
- SEO
- event instrumentation

## First agent task

Start by producing an implementation inventory before editing code:

1. identify current backend framework and persistence layer
2. locate current lead/estimate/payment models and APIs
3. locate admin auth implementation
4. locate frontend router/page conventions
5. identify migration mechanism
6. identify existing money/pricing utilities
7. propose exact files to modify/create for Phase 1
8. call out any ambiguity or conflict with this document

Then implement the smallest vertical slice:

**one persisted concept -> two component requirements -> manually entered retailer offers -> server-side markup -> public concept detail showing customer turnkey price -> admin view showing internal breakdown -> immutable quote snapshot test.**

Do not expand scope until that vertical slice is working and tested.
