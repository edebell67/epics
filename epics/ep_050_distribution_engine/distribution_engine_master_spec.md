# Distribution Engine

## Master Concept, Architecture and MVP Foundation

**Status:** Working master specification\
**Purpose:** Capture the product concept, operating principles,
architecture, demand-capture model, lead intelligence model, and agreed
direction before expanding the system into a full visual workflow and
defining the 24--48 hour MVP.

------------------------------------------------------------------------

## 1. Executive Summary

The **Distribution Engine** is a standalone demand-acquisition and
lead-generation platform designed to solve the recurring "zero
distribution" problem across a portfolio of apps, websites, directories,
local news properties, and future products.

The core principle is simple:

> **Distribution is not a feature of an individual website or app. It is
> shared infrastructure that products plug into.**

The engine accepts a target market, service, product, app, audience
and/or geography as an input. It then discovers demand, identifies the
paths people follow while trying to solve that demand, creates useful
assets for those paths, distributes those assets, captures intent,
converts that intent into attributable leads, qualifies and routes those
leads, records outcomes, and feeds the resulting intelligence back into
the engine.

The desired closed loop is:

**Discover demand → Map demand paths → Create useful assets → Place
assets in those paths → Capture intent → Generate leads → Qualify →
Route → Measure outcomes → Identify winners → Acquire more of what
works**

Every lead must remain traceable from **origin to outcome**.

This platform is initially motivated by an existing website-delivery
operation, business directory service, and local business news network.
However, the Distribution Engine must remain independent of those
products. They are consumers of the engine, not the engine itself.

------------------------------------------------------------------------

## 2. Business Context

The current operation already contains several useful components:

-   Website creation and delivery for local businesses.
-   Localized business directory services.
-   Local business/news publishing properties.
-   The ability to connect websites to directory and local-information
    ecosystems.
-   A developing backend capable of handling leads and distributing them
    to businesses.
-   "Smart site" concepts that can respond to demand signals and
    potentially alter promotions or offers dynamically.

The missing component is a repeatable, scalable source of **qualified
demand and leads**.

A conventional website provider primarily sells a website. The proposed
model is stronger:

> **"We do not merely build your website. We connect your business to an
> acquisition system designed to generate opportunities and feed them
> into the website/business."**

If the lead stream produces sufficient commercial value, the website and
associated monthly service can effectively pay for themselves. This
creates a much stronger reason for customers to remain subscribed.

The website therefore becomes a **front door and endpoint** connected to
a broader demand network.

------------------------------------------------------------------------

## 3. Strategic Separation of Responsibilities

The architecture should deliberately separate three concepts.

### 3.1 Distribution / Demand Acquisition Engine

Responsible for:

-   Discovering demand.
-   Understanding pain points and intent.
-   Discovering the paths through which demand travels.
-   Creating appropriate assets.
-   Placing assets in those paths.
-   Capturing intent.
-   Producing leads.
-   Qualifying leads.
-   Attributing leads.
-   Learning from outcomes.
-   Amplifying successful acquisition patterns.

### 3.2 Lead / Service Platform

Responsible for:

-   Receiving leads.
-   Managing availability.
-   Publishing or exposing active opportunities.
-   Allocating/routing leads.
-   Handling subscriptions/access.
-   Providing feeds to participating businesses.
-   Supporting multiple lead-distribution models.

### 3.3 Smart Websites

Responsible for:

-   Receiving traffic and leads.
-   Capturing first-party enquiries.
-   Recording the same rich lead attributes used by the Distribution
    Engine.
-   Feeding first-party demand intelligence back into the wider engine.
-   Reacting to local demand changes.
-   Potentially changing content, offers, calls to action, or promotions
    in response to demand spikes.

The three systems should exchange data but remain modular.

------------------------------------------------------------------------

## 4. The Core Operating Model

At the highest level:

``` text
TARGET / APP / SERVICE / MARKET
             |
             v
      PRODUCT INGESTION
             |
             v
      DEMAND DISCOVERY
             |
             v
      PATH DISCOVERY
             |
             v
     OPPORTUNITY SCORING
             |
             v
       CONTENT / UTILITY
           FACTORY
             |
             v
      PATH PLACEMENT &
        DISTRIBUTION
             |
             v
       INTENT CAPTURE
             |
             v
       LEAD GENERATION
             |
             v
     QUALIFY & ATTRIBUTE
             |
             v
          ROUTE
             |
             v
     OUTCOME / REVENUE
             |
             v
        LEARNING LOOP
             |
             +--------------------> DEMAND / STRATEGY
```

This is not primarily a content-generation machine. Content is one
mechanism used to intercept demand.

The real product is a **demand-to-lead machine**.

------------------------------------------------------------------------

## 5. The Critical Problem: Capturing Demand

A major distinction emerged during the discussion:

**Finding demand is not the same as capturing demand.**

Suppose the engine discovers a Reddit discussion in which people
repeatedly ask why their boiler pressure is falling.

The Reddit discussion is a **demand signal**. It does not automatically
provide the acquisition route.

The engine must answer four separate questions:

1.  **What are people trying to solve?**
2.  **Where else do people with that problem naturally go before,
    during, or after asking the question?**
3.  **What asset would be most useful at each point on that journey?**
4.  **How do we place that asset so the person can naturally progress
    toward a destination we control?**

This introduces a crucial layer:

## 6. Path Discovery

The engine should map the existing journey rather than simply asking:

> "We have created a video. Where should we publish it?"

The better question is:

> **"When this need occurs, what paths do people naturally follow, and
> where can we become the most useful next step?"**

For a boiler-pressure problem, possible paths include:

``` text
Problem occurs
    |
    +--> Google search
    |
    +--> YouTube how-to search
    |
    +--> Reddit / forum discussion
    |
    +--> AI assistant question
    |
    +--> Manufacturer/support information
    |
    +--> Local plumber search
    |
    +--> Recommendation / social community
```

The engine therefore discovers **repeated patterns of behaviour**,
rather than chasing individual posts.

A forum may reveal the question.\
Google may capture the informational search.\
YouTube may capture the visual explanation.\
An AI answer may capture research intent.\
A diagnostic tool may capture active problem-solving.\
A local service page may capture commercial intent.

This creates a **Demand Path Map**.

------------------------------------------------------------------------

## 7. Capture Through Utility, Not Promotion

The strongest acquisition philosophy identified is:

> **Become the most useful next step after the question is asked.**

For example:

**Demand:** "Why does my boiler pressure keep dropping?"

Instead of merely promoting a plumbing service, the system could
produce:

-   A concise explanatory video.
-   A short-form video.
-   A detailed article.
-   A diagnostic questionnaire/tool.
-   An FAQ.
-   A local service landing page.
-   Structured answers suitable for search/AI discovery.
-   Helpful community participation where appropriate.

The content answers the immediate question.

The tool provides the next level of value.

The commercial destination becomes a natural continuation:

``` text
QUESTION
   |
   v
USEFUL ANSWER
   |
   v
USEFUL NEXT STEP
   |
   v
DIAGNOSTIC / CALCULATOR / GUIDE / TOOL
   |
   v
SERVICE / BOOKING / QUOTE / LEAD
```

The landing page is therefore not simply "where we send traffic." It is
the destination at the end of a deliberately constructed value path.

------------------------------------------------------------------------

## 8. Two Demand Modes

The Distribution Engine should support two distinct operating modes.

### Mode A --- Portfolio Discovery

The engine explores broadly and asks:

-   Which services have strong demand?
-   Which problems are underserved?
-   Which local categories have attractive economics?
-   Which markets appear suitable for a new app/site/product?
-   What should we build or target next?

This mode can inform product creation and portfolio strategy.

### Mode B --- Market Expansion

The input is already known.

For example:

-   Plumbing.
-   Boiler repair.
-   Accountancy.
-   Roofing.
-   Dental services.
-   A specific app.

The engine asks:

> **"Find everything people want, ask, fear, compare, search for and
> attempt to solve around this service."**

It expands outward into:

-   Pain points.
-   Questions.
-   Search queries.
-   Intent.
-   Geography.
-   Competitors.
-   Alternatives.
-   Communities.
-   Trends.
-   Content opportunities.
-   Conversion opportunities.
-   Demand paths.

For the current website/service model, **Market Expansion should be the
default operating mode**, while Portfolio Discovery can run separately
to identify future opportunities.

------------------------------------------------------------------------

# 9. Full Logical Node Architecture

These are logical capabilities, not necessarily individual software
services. Multiple nodes may eventually be implemented within the same
component.

## A. Product / Market Ingestion

### Node 01 --- App / Service Registration

Create a unique target identity.

Example fields:

-   `target_id`
-   `target_type`
-   `app_id`
-   `service`
-   `product`
-   `market`
-   `geography`
-   `domain`
-   `status`

### Node 02 --- Product Intelligence

Describe:

-   Problem.
-   Solution.
-   Features.
-   Benefits.
-   Differentiators.
-   Commercial model.
-   Customer outcome.

### Node 03 --- Audience Definition

Define relevant customer segments, not merely one generic target
audience.

### Node 04 --- Conversion Definition

Define valuable outcomes:

**Visit → Engage → Tool use → Enquiry → Lead → Qualified lead → Booking
→ Sale → Revenue**

------------------------------------------------------------------------

# 10. Demand Intelligence

## Node 05 --- Search Demand Discovery

Discover what people search for and how language changes with intent.

## Node 06 --- Question Discovery

Discover explicit questions and problem statements.

## Node 07 --- Social / Video Discovery

Identify themes, discussions, content formats and emerging attention.

## Node 08 --- Competitor Intelligence

Understand where competing services acquire attention and which
topics/queries appear valuable.

## Node 09 --- Community Intelligence

Observe forums, Reddit, Q&A communities, specialist communities and
other places where real needs are expressed.

The objective is intelligence, not automated spam.

## Node 10 --- Trend Detection

Detect changes in demand, emerging topics and unusual spikes.

------------------------------------------------------------------------

# 11. Opportunity Database

Demand signals should be normalized into structured opportunity records.

Example:

``` text
OPPORTUNITY
|
+-- opportunity_id
+-- target_id
+-- topic
+-- question
+-- pain_point
+-- audience
+-- intent
+-- geography
+-- source
+-- source_type
+-- observed_at
+-- demand_strength
+-- trend_velocity
+-- competition
+-- commercial_value
+-- channel_fit
+-- path_hypothesis
+-- opportunity_score
+-- status
```

The raw signal and the normalized opportunity should both be retained.

------------------------------------------------------------------------

# 12. Strategy and Path Intelligence

## Node 11 --- Intent Classification

Potential progression:

``` text
INFORMATIONAL
     |
PROBLEM AWARE
     |
SOLUTION AWARE
     |
COMMERCIAL
     |
TRANSACTIONAL
```

## Node 12 --- Opportunity Scoring

A proprietary **Distribution Opportunity Score (DOS)** can rank
opportunities.

Conceptually:

``` text
Demand
x Relevance
x Commercial potential
x Trend / urgency
x Achievability
x Channel suitability
--------------------------------
Competition / acquisition effort
```

The exact scoring formula should evolve from real outcome data.

## Node 13 --- Demand Path Discovery

For each opportunity, determine:

-   Where the demand originates.
-   What people do next.
-   Which channels they use.
-   What information they seek at each stage.
-   Where commercial intent emerges.
-   Which touchpoints can realistically be influenced.
-   Which destination represents the natural next step.

## Node 14 --- Channel / Placement Selection

Score channel fit for each opportunity.

Example:

``` text
"Boiler losing pressure"

Google Search      *****
YouTube            *****
AI discovery       ****
Local search       ****
Community          ***
Short video        ***
Generic LinkedIn   *
```

## Node 15 --- Campaign / Cluster Generation

Group related opportunities into coherent demand clusters rather than
treating every query independently.

------------------------------------------------------------------------

# 13. Knowledge and Asset Factory

## Node 16 --- Canonical Knowledge Object

Create one authoritative underlying knowledge object for each
topic/cluster.

Example:

``` text
TOPIC: Boiler losing pressure

- Problem definition
- Causes
- Symptoms
- Diagnostic questions
- Solutions
- Safety / warnings
- FAQs
- Evidence / sources
- Geography
- Commercial relevance
- Recommended next step
- CTA options
```

This prevents each channel from independently inventing facts.

## Node 17 --- Asset Generator

Render the knowledge object into the formats appropriate to identified
demand paths:

-   Article.
-   Landing page.
-   FAQ.
-   Search-oriented page.
-   YouTube script.
-   YouTube Short.
-   TikTok/Reel.
-   Social post.
-   Email.
-   Graphic.
-   Diagnostic.
-   Calculator.
-   Checklist.
-   Comparison.
-   Local page.
-   AI-discovery-friendly structured answer.

The rule is not "publish everywhere."

It is:

> **Create the format appropriate to the path.**

## Node 18 --- Video Factory

Potential flow:

``` text
SCRIPT
  |
VOICE
  |
SCENES
  |
MEDIA
  |
CAPTIONS
  |
BRANDING
  |
CTA
  |
RENDER
```

Programmatic video tooling can make this highly scalable.

## Node 19 --- Quality / Compliance

Check:

-   Factual accuracy.
-   Duplication.
-   Hallucinations.
-   Broken links.
-   Brand consistency.
-   Inappropriate claims.
-   Copyright/licensing.
-   Safety/compliance.
-   Channel-specific requirements.

------------------------------------------------------------------------

# 14. Distribution and Placement

## Node 20 --- Publishing Scheduler

Determine:

**what → where → when → for which audience → with which CTA**

## Node 21 --- Search Distribution

Includes:

-   Articles.
-   Landing pages.
-   FAQs.
-   Structured data.
-   Internal linking.
-   Sitemap/indexing support.
-   Localized pages.

## Node 22 --- Video Distribution

Publish and optimize appropriate long-form and short-form video assets.

## Node 23 --- Social Distribution

Use platform-specific formats rather than identical cross-posting.

## Node 24 --- Community Participation

Identify relevant conversations and opportunities to help.

This should **not** become a spam bot.

Possible operating modes:

-   Intelligence only.
-   Draft response for human approval.
-   Approved brand participation.
-   Useful answer without link.
-   Link/tool only where genuinely appropriate and permitted.

## Node 25 --- Syndication / Partnership Distribution

Potential routes:

-   Directories.
-   Local publications.
-   News properties.
-   Newsletters.
-   Affiliates.
-   Industry sites.
-   Partners.
-   Existing owned media.

------------------------------------------------------------------------

# 15. Intent Capture and Conversion

## Node 26 --- Smart Destination Router

Route a user according to:

-   Topic.
-   Intent.
-   Geography.
-   Service.
-   Channel.
-   Asset.
-   Stage of journey.

Destinations may include:

-   Landing page.
-   Diagnostic tool.
-   Calculator.
-   Quote form.
-   Booking flow.
-   Chat interface.
-   App.
-   Service page.
-   Relevant business website.

## Node 27 --- Conversion / Lead Capture

Convert engagement into a structured lead while preserving acquisition
context.

------------------------------------------------------------------------

# 16. Lead Identity, Attribution and Lifecycle Intelligence

This is a foundational design requirement.

Every lead should receive a persistent unique identifier at the earliest
possible point.

Example:

`lead_id = immutable lifecycle identifier`

The lead record must preserve sufficient attributes to answer questions
such as:

-   Where did this lead originate?
-   Which demand signal ultimately led to it?
-   Which topic?
-   Which question/pain point?
-   Which channel?
-   Which asset?
-   Which campaign?
-   Which geography?
-   Which service?
-   Which CTA?
-   Which landing page/tool?
-   Was it qualified?
-   Where was it routed?
-   Was it accepted?
-   Did it book?
-   Did it convert?
-   What revenue resulted?
-   Where did it drop out?

## Node 28 --- Attribution

Potential dimensions:

``` text
lead_id
target_id
app_id
service_id
market_id
geography_id
opportunity_id
campaign_id
knowledge_object_id
asset_id
publication_id
channel
platform
source
source_detail
keyword / query / topic
intent
cta_id
destination_id
session_id
created_at
```

Not every field will always be populated, but the schema should be
capable of retaining the full lineage.

------------------------------------------------------------------------

# 17. Lead Qualification

This was identified as an architectural gap and should be explicit.

## Node 29 --- Lead Qualification

Possible attributes:

-   Correct service?
-   Correct geography?
-   Urgency.
-   Budget/value.
-   Contactability.
-   Customer type.
-   Problem specificity.
-   Purchase intent.
-   Duplicate?
-   Spam/fraud?
-   Existing customer?
-   Estimated commercial value.

The engine should distinguish **traffic**, **raw enquiries**,
**qualified leads**, and **commercial outcomes**.

------------------------------------------------------------------------

# 18. Lead Routing

## Node 30 --- Lead Routing

Routing logic may eventually consider:

-   Service match.
-   Geography.
-   Client subscription.
-   Availability.
-   Capacity.
-   Lead value.
-   Exclusivity.
-   Performance history.
-   Response speed.
-   Customer preference.
-   Allocation rules.

The current website/platform may be one destination, but the engine must
support many future destinations.

------------------------------------------------------------------------

# 19. Outcome Capture

## Node 31 --- Lifecycle / Outcome Tracking

The system should capture stages such as:

``` text
CREATED
  |
VALIDATED
  |
QUALIFIED
  |
ROUTED
  |
DELIVERED
  |
ACCEPTED
  |
CONTACTED
  |
BOOKED
  |
WON / LOST
  |
REVENUE
```

Loss/drop-off reasons are important intelligence:

-   Wrong service.
-   Wrong location.
-   Duplicate.
-   Could not contact.
-   Too expensive.
-   No availability.
-   Competitor selected.
-   Low intent.
-   Invalid.
-   Other.

------------------------------------------------------------------------

# 20. Performance Intelligence

## Node 32 --- Performance Warehouse

Combine acquisition and outcome data:

-   Impressions.
-   Rankings.
-   Views.
-   Clicks.
-   CTR.
-   Visits.
-   Engagement.
-   Tool usage.
-   Enquiries.
-   Leads.
-   Qualified leads.
-   Bookings.
-   Sales.
-   Revenue.
-   Cost.
-   Time-to-response.
-   Drop-off stage.

This enables analysis such as:

> "For plumbing in Location X, leads originating from YouTube assets
> about boiler pressure convert at Y%, generate average revenue Z, and
> outperform generic plumbing content by N."

The system should optimize for **commercial value**, not vanity metrics.

------------------------------------------------------------------------

# 21. Feedback Engine

This was another important gap identified in discussion.

## Node 33 --- Outcome Feedback

Outcome information must flow back from:

-   Websites.
-   Clients.
-   CRM/service platform.
-   Booking systems.
-   Sales outcomes.
-   Lead rejection reasons.
-   Revenue records.

Without this, the engine knows what generated clicks but not what
generated value.

------------------------------------------------------------------------

# 22. Winner Detection

## Node 34 --- Winner Detection

The engine continuously identifies unusually productive combinations of:

-   Service.
-   Pain point.
-   Topic.
-   Intent.
-   Geography.
-   Channel.
-   Asset type.
-   CTA.
-   Destination.
-   Customer segment.

A winner does not need high traffic.

A low-volume opportunity with a high conversion rate and high customer
value may be more important than a viral asset.

------------------------------------------------------------------------

# 23. Amplification

## Node 35 --- Amplification Engine

Once a winner is found:

``` text
WINNER
  |
  +--> Create related search assets
  +--> Create related video assets
  +--> Strengthen landing experience
  +--> Expand geographic variants
  +--> Explore adjacent questions
  +--> Improve internal linking
  +--> Increase publishing effort
  +--> Test stronger CTAs
  +--> Allocate more resources
  |
  v
MORE QUALIFIED DEMAND
```

------------------------------------------------------------------------

# 24. Neighbourhood Expansion

The system should not simply clone a successful asset.

It should discover the semantic and behavioural neighbourhood around the
winning demand.

Example:

**Winner:** "Boiler losing pressure overnight"

Possible adjacent demand:

-   Pressure drops when heating is on.
-   Pressure rises to 3 bar.
-   Pressure falls after bleeding radiators.
-   Boiler needs topping up every day.
-   Boiler pressure at zero.
-   Expansion vessel symptoms.
-   Boiler leaking but leak not visible.
-   Manufacturer-specific pressure problems.

The winner has discovered a **vein of demand**.

The engine should mine the vein.

------------------------------------------------------------------------

# 25. Resource Allocation / Investment Engine

Another gap identified was deciding where finite acquisition capacity
should be deployed.

## Node 36 --- Distribution Investment

Given limited resources, the system should eventually answer:

-   Which services deserve more acquisition effort?
-   Which geographies?
-   Which channels?
-   Which content clusters?
-   Which clients?
-   Which formats?
-   Which experiments should stop?
-   Where is marginal effort most likely to generate commercial value?

This can eventually become portfolio-level capital allocation for
distribution.

------------------------------------------------------------------------

# 26. Proprietary Knowledge Repository

## Node 37 --- Distribution Knowledge Base

Over time, preserve learned relationships such as:

-   Which questions convert.
-   Which services perform.
-   Which locations respond.
-   Which channels generate quality.
-   Which formats work for which intent.
-   Which CTAs work.
-   Which destinations convert.
-   Which lead attributes predict sales.
-   Which demand patterns precede spikes.
-   Which businesses convert leads well.

This accumulated outcome-linked intelligence becomes a major proprietary
advantage.

Competitors can copy a website or individual content asset. It is much
harder to copy years of structured demand-to-revenue intelligence.

------------------------------------------------------------------------

# 27. Portfolio Intelligence

The Distribution Engine should serve multiple products.

``` text
                 PORTFOLIO BRAIN
                       |
       +---------------+---------------+
       |               |               |
     APP 01          APP 02          APP 03
       |               |               |
       +---------------+---------------+
                       |
                       v
              DISTRIBUTION ENGINE
                       |
                       v
                 LEAD OUTPUTS
```

Eventually the system can compare expected returns across the portfolio
and allocate acquisition effort accordingly.

------------------------------------------------------------------------

# 28. Smart Websites as Bidirectional Nodes

Client websites are not merely destinations.

They can also become **sensors**.

Suppose a plumbing website suddenly receives unusual first-party demand
for a particular service in one locality.

That demand may not yet be visible to the broader Distribution Engine.

The website should capture:

-   Service requested.
-   User language.
-   Geography.
-   Timing.
-   Traffic source.
-   Search/referral context where available.
-   Conversion behaviour.
-   Lead outcome.

That information can flow back into the Distribution Engine.

The engine may then identify a local phenomenon and respond by:

-   Producing relevant content.
-   Increasing distribution.
-   Creating local assets.
-   Adjusting offers.
-   Testing promotions.
-   Alerting other relevant sites/businesses.

The smart site and Distribution Engine therefore form a bidirectional
intelligence network.

------------------------------------------------------------------------

# 29. Lead Data Principle

A major conclusion from the discussion:

> **The intelligence available later is determined by the attributes
> captured at the beginning.**

Therefore, before implementation, the team must ask:

> "What might we ever want this lead to tell us?"

Then capture the necessary identifiers and attributes as early as
practical.

Two non-negotiable principles follow:

### Principle 1 --- Structured Data at Intake

Every meaningful entity should receive structured identifiers and
attributes at creation.

### Principle 2 --- Outcomes Flow Back

The lifecycle must not terminate when a lead is delivered.

Results must return to the intelligence layer.

Together these principles create the learning loop.

------------------------------------------------------------------------

# 30. Core Data Lineage

The platform should ultimately be able to reconstruct:

``` text
DEMAND SIGNAL
      |
OPPORTUNITY
      |
DEMAND PATH
      |
CAMPAIGN
      |
KNOWLEDGE OBJECT
      |
ASSET
      |
PUBLICATION
      |
VISIT / INTERACTION
      |
LEAD
      |
QUALIFICATION
      |
ROUTING
      |
CLIENT / DESTINATION
      |
OUTCOME
      |
REVENUE
```

This lineage is one of the most important architectural requirements.

------------------------------------------------------------------------

# 31. Key Objects for the Future Data Model

The next data-design stage should formalize at least:

-   `TARGET`
-   `APP`
-   `SERVICE`
-   `MARKET`
-   `GEOGRAPHY`
-   `AUDIENCE`
-   `DEMAND_SIGNAL`
-   `OPPORTUNITY`
-   `DEMAND_PATH`
-   `CAMPAIGN`
-   `KNOWLEDGE_OBJECT`
-   `ASSET`
-   `CHANNEL`
-   `PUBLICATION`
-   `CTA`
-   `DESTINATION`
-   `VISITOR`
-   `SESSION`
-   `LEAD`
-   `LEAD_ATTRIBUTE`
-   `QUALIFICATION`
-   `ROUTING`
-   `CLIENT`
-   `OUTCOME`
-   `REVENUE`
-   `EXPERIMENT`
-   `PERFORMANCE_METRIC`

Relationships and immutable identifiers will be defined during the data
architecture exercise.

------------------------------------------------------------------------

# 32. Guiding Principles

## 32.1 Distribution Is Infrastructure

Do not rebuild acquisition separately for every app/site.

## 32.2 Leads Are the Primary Output

Content, impressions and traffic are intermediate products.

## 32.3 Demand Before Content

Do not create assets simply because production is easy.

## 32.4 Paths Before Placement

Identify where demand naturally travels before deciding where to
publish.

## 32.5 Utility Before Promotion

Aim to become the most useful next step.

## 32.6 Attribution From Origin to Outcome

Every lead should be traceable as far back through its lineage as data
permits.

## 32.7 Commercial Outcomes Beat Vanity Metrics

Optimize for qualified leads, bookings, revenue and lifetime value.

## 32.8 Feedback Is Mandatory

The engine cannot learn if outcomes disappear after routing.

## 32.9 Winners Should Be Amplified

Use evidence to allocate future acquisition resources.

## 32.10 Keep the Engine Standalone

The current platform is an important customer of the Distribution
Engine, not its architectural boundary.

## 32.11 Build Modularly

The same acquisition engine should eventually support many verticals,
geographies, apps and lead destinations.

## 32.12 Start Narrow, Preserve the Long-Term Spine

The first implementation can target one service and one geography, while
retaining identifiers and interfaces that allow later expansion.

------------------------------------------------------------------------

# 33. Important Architectural Gaps Identified

The discussion surfaced several areas that must explicitly exist in the
final architecture:

1.  **Demand Path Discovery** --- the bridge between observing demand
    and placing an asset where it can capture that demand.
2.  **Lead Qualification** --- distinguishing useful commercial
    opportunities from raw enquiries.
3.  **Lead Routing** --- deciding where qualified opportunities should
    go.
4.  **Outcome Feedback** --- knowing what happened after delivery.
5.  **Resource Allocation** --- deciding where acquisition effort should
    be increased or reduced.
6.  **Proprietary Knowledge Repository** --- preserving accumulated
    demand-to-outcome learning.
7.  **First-Party Website Feedback** --- allowing smart websites to act
    as demand sensors.
8.  **Lifecycle Attribution** --- ensuring every lead retains its origin
    and progression.
9.  **Cross-Vertical Modularity** --- preventing the system from
    becoming specific to plumbing or any other initial test market.

These gaps are now incorporated into the logical node architecture
above.

------------------------------------------------------------------------

# 34. What the Distribution Engine Is Not

It is not:

-   Merely a social media scheduler.
-   Merely an SEO tool.
-   Merely a content generator.
-   Merely a video factory.
-   Merely a scraper.
-   Merely a lead marketplace.
-   Merely part of the website builder.
-   A spam bot for communities.
-   A system optimized only for traffic.

Those capabilities may exist inside it, but the product is the **closed
demand-to-outcome loop**.

------------------------------------------------------------------------

# 35. Product Definition

A concise definition:

> **The Distribution Engine is a standalone, multi-channel
> demand-acquisition platform that discovers market demand, maps the
> paths through which that demand travels, places useful assets into
> those paths, converts intent into attributable and qualified leads,
> routes those leads to appropriate destinations, captures commercial
> outcomes, and uses the resulting intelligence to continuously improve
> acquisition.**

An even shorter operational definition:

> **Input: a market/service/product. Output: attributable qualified
> leads plus the intelligence required to generate more of them.**

------------------------------------------------------------------------

# 36. MVP Philosophy

The final architecture is intentionally extensive.

The first implementation must **not** attempt to build every node.

The objective of the MVP is to prove the smallest complete learning
loop:

``` text
KNOWN SERVICE / LOCATION
          |
          v
   DISCOVER DEMAND
          |
          v
   SELECT OPPORTUNITY
          |
          v
    CREATE ASSET
          |
          v
   PLACE / DISTRIBUTE
          |
          v
     CAPTURE LEAD
          |
          v
 TAG ORIGIN + ATTRIBUTES
          |
          v
    RECORD OUTCOME
          |
          v
       LEARN
```

A good MVP is not the smallest number of features.

It is the **smallest end-to-end system capable of producing and learning
from a real lead**.

The working target discussed is to identify a subset of nodes that can
become operational within approximately **24--48 hours**, using existing
components and pragmatic/manual steps where necessary.

The exact MVP node selection should be made **after the full workflow is
visualized**, so that shortcuts are deliberate rather than architectural
accidents.

------------------------------------------------------------------------

# 37. Recommended Next Work Product: Full Workflow

The next stage is to convert this architecture into a full workflow.

The workflow should show:

### Inputs

-   Product/app/service.
-   Geography.
-   Audience.
-   Existing assets.
-   Existing websites.
-   Existing directory/news properties.
-   Constraints.
-   Commercial objectives.

### Processing

Every major node, decision, branch, loop, datastore and human approval
point.

### Outputs

-   Assets.
-   Publications.
-   Visits.
-   Leads.
-   Qualified leads.
-   Routed leads.
-   Outcomes.
-   Revenue.
-   Intelligence.
-   Amplification instructions.

### Feedback Loops

Particularly:

-   Outcome → attribution.
-   Website demand → demand intelligence.
-   Winner → opportunity generation.
-   Conversion → scoring.
-   Lead rejection → qualification rules.
-   Revenue → resource allocation.

------------------------------------------------------------------------

# 38. Workflow Design Questions

The visual workflow should force answers to questions such as:

-   What initiates a demand scan?
-   What sources are queried?
-   How are raw signals stored?
-   When do multiple signals become one opportunity?
-   How is opportunity score calculated?
-   How is a demand path inferred?
-   What determines asset type?
-   What requires human approval?
-   What determines channel placement?
-   What is the first attributable touch?
-   When is a `lead_id` created?
-   How are anonymous interactions linked to later leads?
-   What attributes are mandatory?
-   What makes a lead qualified?
-   How is routing decided?
-   How are outcomes returned?
-   What constitutes a winner?
-   What triggers amplification?
-   What triggers a new opportunity scan?
-   What can be automated now versus later?

------------------------------------------------------------------------

# 39. MVP Selection Criteria

After the workflow is complete, each node should be classified:

### A --- Required for First Live Loop

Without it, the system cannot acquire and learn from a lead.

### B --- Manual Initially

Required conceptually, but a person can perform it during the first
test.

### C --- Automate Next

High-value automation once the loop works.

### D --- Scale Capability

Important when multiple services/locations/clients are running.

### E --- Advanced Intelligence

Optimization and portfolio-level capability that should follow
accumulated data.

This will make it possible to reduce the large architecture into a
credible 24--48 hour MVP without losing the intended final design.

------------------------------------------------------------------------

# 40. MVP Success Test

The first operational version should be able to answer, for at least one
real lead:

1.  What service did the person need?
2.  What problem or intent did they express?
3.  Where was the demand originally identified?
4.  Which opportunity did we pursue?
5.  Which asset did we create?
6.  Where was it placed?
7.  How did the person reach us?
8.  Which CTA/destination converted them?
9.  Was the lead qualified?
10. Where was the lead routed?
11. What happened to it?
12. Did it generate commercial value?
13. Based on that outcome, what should the engine do next?

If those questions can be answered, the first complete learning loop
exists.

------------------------------------------------------------------------

# 41. North-Star Test

Every component can ultimately be challenged with one question:

> **Does this help the system generate more qualified, attributable,
> commercially valuable leads more efficiently for the products and
> clients connected to it?**

If not, it is probably secondary to the core engine.

------------------------------------------------------------------------

# 42. Agreed Build Sequence

The discussion established the following sequence:

``` text
1. MASTER ARCHITECTURE DOCUMENT
             |
             v
2. FULL END-TO-END WORKFLOW
             |
             v
3. CLASSIFY / PRIORITIZE NODES
             |
             v
4. DEFINE 24–48 HOUR MVP
             |
             v
5. BUILD FIRST LIVE LOOP
             |
             v
6. MEASURE REAL LEADS
             |
             v
7. ITERATE & ADD NODES
```

This document completes **Step 1** at the conceptual level.

The immediate next exercise is **Step 2: the full visualized workflow
process**.

------------------------------------------------------------------------

# 43. Working Vision

The long-term vision is not a collection of disconnected marketing
automations.

It is a shared distribution layer capable of serving an entire
portfolio:

``` text
             DEMAND SOURCES
                   |
                   v
        +----------------------+
        | DISTRIBUTION ENGINE  |
        |                      |
        | Discover             |
        | Understand           |
        | Map paths            |
        | Create               |
        | Place                |
        | Capture              |
        | Qualify              |
        | Attribute            |
        | Learn                |
        | Amplify              |
        +----------+-----------+
                   |
                   v
             LEAD NETWORK
                   |
        +----------+----------+
        |          |          |
        v          v          v
     WEBSITE    PLATFORM    APP
        |          |          |
        +----------+----------+
                   |
                   v
             OUTCOMES / VALUE
                   |
                   v
               FEEDBACK
                   |
                   +-----------> DISTRIBUTION ENGINE
```

The strategic objective is to move from:

> **"We build websites/apps and then face the problem of
> distribution."**

to:

> **"We own a reusable distribution capability, and every website/app we
> build can plug into it."**

That is the central product thesis.

------------------------------------------------------------------------

## 44. Decision Log --- Current

  -----------------------------------------------------------------------
  Decision                            Current Direction
  ----------------------------------- -----------------------------------
  Is distribution embedded inside     No. Standalone platform.
  each website?                       

  Primary output                      Qualified, attributable leads.

  Can current websites consume leads? Yes.

  Can other future systems consume    Yes.
  leads?                              

  Can websites feed demand            Yes.
  intelligence back?                  

  Default demand mode                 Expand from a known
                                      service/product.

  Can engine also discover            Yes, via Portfolio Discovery mode.
  markets/services?                   

  Community strategy                  Intelligence/helpful participation,
                                      not spam.

  Optimization target                 Commercial outcomes, not vanity
                                      metrics.

  Attribution requirement             Origin-to-outcome lineage wherever
                                      possible.

  First build goal                    Smallest complete live learning
                                      loop.

  Initial time-box                    Identify a version capable of
                                      operation in \~24--48 hours.

  Next deliverable                    Full end-to-end visual workflow.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 45. Closing Principle

The metaphor used during the discussion is useful:

> **Leads are the lifeblood.**

Without a reliable source of demand, otherwise capable websites, apps
and platforms can suffocate on arrival.

The Distribution Engine is intended to create that circulation: a
reusable system for finding demand, entering its natural paths,
converting it into measurable commercial opportunity, and learning how
to repeat the process more effectively.

Once that circulation exists, the existing website platform,
directories, news properties, future apps and other products can all
become stronger because they no longer begin from zero distribution.
