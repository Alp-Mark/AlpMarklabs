# AlpMark Intelligence Platform — Website Brief for Replit

---

## 1. What You Are Building

A marketing/product website for **AlpMark Intelligence Platform** — a B2B SaaS decision-intelligence product for e-commerce D2C brands.

The site should feel like a premium data-intelligence product: clean, confident, fast, and trustworthy. Think Linear, Notion, or Hex — but with an analytics/finance lens. The brand has edge without being cold.

---

## 2. Brand Identity

**Product name:** AlpMark Intelligence Platform
**Tagline:** *One trusted view. Smarter decisions. Measurable profit.*
**Brand tone:** Confident, precise, direct. No fluff. Every sentence earns its place.

### 2.1 Color Palette

| Token | Hex | Use |
|---|---|---|
| Brand Blue Dark | `#0344A4` | Gradient start, nav, headings |
| Brand Blue Light | `#16A3E5` | Gradient mid, highlights, links |
| Brand Red | `#F43631` | Gradient end, CTA accents, alerts, key stat callouts |
| Dark BG | `#0A0E1A` | Dark mode page background |
| Dark Surface | `#111827` | Dark mode card/panel background |
| Dark Border | `#1F2937` | Dark mode card borders |
| Light BG | `#F9FAFB` | Light mode page background |
| Light Surface | `#FFFFFF` | Light mode card background |
| Light Border | `#E5E7EB` | Light mode card borders |
| Text Primary (dark mode) | `#F3F4F6` | Body text on dark |
| Text Primary (light mode) | `#111827` | Body text on light |
| Text Muted | `#6B7280` | Supporting text, labels |

### 2.2 Button Gradient

All primary CTA buttons use a **left-to-right gradient:**
```
background: linear-gradient(90deg, #0344A4 0%, #16A3E5 50%, #F43631 100%);
```
Text on gradient buttons: white, semibold.
Hover state: increase brightness slightly, subtle scale(1.02).
Border radius: 8px.

### 2.3 Typography

- **Headlines:** A modern geometric sans-serif (e.g. Inter, DM Sans, or Geist). Bold, generous letter-spacing at display sizes.
- **Body:** Same family, regular weight, 16–18px, comfortable line-height (1.6).
- **Monospace / data labels:** Use a monospace or tabular-figures font for metric callouts (e.g. "£1.2M recovered margin", "3.4× ROAS").

### 2.4 Aesthetic Details

- Subtle **gradient mesh or dot-grid** background texture on dark hero sections.
- Cards use **glass-morphism** on dark mode: `backdrop-filter: blur(12px)` with semi-transparent dark surface.
- Thin gradient **border glow** on featured cards: 1px border using the blue-to-red gradient.
- Section dividers: subtle, not heavy. Use spacing over lines.
- Icons: minimal outlined style (Lucide or Heroicons).
- Charts/data visualizations: use abstract/stylised chart graphics as decoration (not real data). Sparklines, bar columns, cohort curves as SVG art in hero and feature sections.

---

## 3. Modes

**Both light mode and dark mode are required.**
- Default on load: dark mode.
- Toggle: visible in top-right of nav. A simple sun/moon icon that transitions smoothly.
- Persist preference in localStorage.
- All sections must look great in both modes.

---

## 4. Site Structure (Pages and Sections)

### Page 1: Home (/)

#### Section 1 — Hero

**Headline (large, bold):**
> Stop stitching spreadsheets. Start making profitable decisions.

**Sub-headline (medium, muted):**
> AlpMark unifies your e-commerce data, surfaces what matters, and tells you exactly what to do next — with the confidence level and evidence to back it up.

**CTA buttons (two):**
- Primary gradient button: `Request Early Access`
- Secondary ghost button (outline, no fill): `See How It Works ↓`

**Hero visual:**
A stylised dark-mode dashboard mockup or abstract data visualization — cohort curves, KPI tiles, a recommendation card. Show the product feeling, not screenshots. Use the brand blue-to-red color palette in the graphic.

---

#### Section 2 — The Problem (3-column)

**Section label (small caps, gradient text):** `WHY ALPMARK EXISTS`

**Heading:** The data is there. The decisions aren't.

Three pain-point cards, each with an icon:

1. **Fragmented view**
   Your performance data is split across Shopify, Meta, Google Ads, your 3PL, and spreadsheets. Nobody has a complete picture. Decisions get made on partial information.

2. **Slow analysis cycle**
   Every strategic question requires hours of data pulling, model rebuilding, and cross-team chasing. By the time you have an answer, the opportunity has passed.

3. **Invisible margin leakage**
   Suboptimal channel mix, over-stocked SKUs, avoidable return rates, and misaligned cost assumptions are quietly eroding profit — without anyone catching it.

---

#### Section 3 — The Solution (full-width, centered)

**Heading:** One platform. Every decision lever.

**Body:**
AlpMark connects to your commerce, advertising, and operations data — then does the hard thinking. It calculates contribution margin across every channel, product, and customer segment. It generates prioritised recommendations with projected impact. It lets your team simulate decisions before acting. And it tracks outcomes after.

> No more manual analysis. No more guesswork. No more waiting.

---

#### Section 4 — How It Works (numbered steps, horizontal flow)

**Heading:** Intelligence in four steps

1. **Connect** — Link Shopify, Meta Ads, and Google Ads. AlpMark syncs automatically on a schedule and shows every source's freshness and health.
2. **Analyse** — See contribution margin, ROAS, CAC, cohort retention, inventory risk, and more — calculated daily, broken down by channel, product, and customer segment.
3. **Decide** — AlpMark surfaces prioritised recommendations with confidence levels, supporting evidence, and simulated impact. Approve, reject, or simulate alternatives — all logged and traceable.
4. **Track** — After a decision is implemented externally, AlpMark monitors whether the outcome matched the expectation. Every recommendation has a before and an after.

---

#### Section 5 — Six Core Capabilities (2×3 grid of feature cards)

Each card: gradient border glow, icon, title, 2-sentence description.

1. **Executive Intelligence**
   A single trusted business-health view: revenue, margin, KPI drift, and cross-team roll-up. Everything the owner or executive needs — ranked by impact, not by recency.

2. **Channel and Acquisition Performance**
   ROAS, CAC, payback period, and blended contribution margin — per channel, per campaign. Early warnings before declining efficiency becomes a budget problem.

3. **Retention and Cohort Analytics**
   Monthly cohort retention curves, brand-specific churn risk timing, lifecycle funnel drop-off, and segment-level margin. See exactly where post-purchase revenue is leaking.

4. **Financial Governance and Margin Intelligence**
   Contribution margin breakdown with every cost driver labeled by source and freshness. High-impact cost changes require explicit confirmation before they affect live metrics.

5. **Inventory and Operations Intelligence**
   Stockout risk with days-to-stockout, overstock detection using real velocity and seasonal context, slow-moving capital exposure, and operational anomaly detection.

6. **Recommendation and Decision Engine**
   Automatically generated recommendations from analytics signals — each with impact score, confidence level, and a full lifecycle: New → Approved → Implemented → Outcome Observed.

---

#### Section 6 — Simulation Engine Spotlight (full-width, dark panel)

**Heading:** Test the decision before you make it.

**Body:**
AlpMark's simulation workspace lets you model what-if scenarios across any domain — before anything changes in the real world. Shift budget between channels. Adjust a cost assumption. Change your reorder timing. AlpMark projects the outcome across three mandatory scenarios: **baseline, upside, and downside**.

> Simulations never touch live metrics. The risk is modelled, not taken.

**Supporting visual:** Side-by-side scenario comparison mockup (abstract, stylised).

---

#### Section 7 — Trust and Governance (3-column)

**Heading:** Built for the decisions that matter.

1. **Confidence on everything**
   Every metric, recommendation, and simulation shows a confidence level based on data freshness and completeness. AlpMark never hides uncertainty.

2. **Full decision audit trail**
   Every approval, rejection, and delegation is timestamped, logged, and queryable. AlpMark is a governance record, not just a dashboard.

3. **Decision-intelligence only**
   AlpMark recommends, simulates, and tracks. It never executes actions in external platforms. Your team stays in control of every change.

---

#### Section 8 — KPI Impact (stats row, full-width, dark gradient background)

**Heading:** What good decisions compound into.

Six metric callouts in a row (stylised, large numbers with gradient text):

- `+3–8%` Contribution Margin
- `-15–20%` CAC Payback Period
- `+10–15%` Blended ROAS
- `-10%` Return Rate
- `+8–12%` Repeat Purchase Rate
- `<1 hour` Time to Insight

Small disclaimer beneath: *Based on 6-month target ranges set at onboarding.*

---

#### Section 9 — Who It's For (tab or scroll section)

**Heading:** One platform, purpose-built for every decision-maker.

Tabs or scrollable cards (one per persona):

- **Executive Owner** — One trusted view of business health, prioritised risk alerts, and strategic simulation. The intelligence brief, not the operational noise.
- **Growth Manager** — Channel performance, early warnings, spend simulation, and budget reallocation recommendations with projected CAC, ROAS, and margin impact.
- **Retention Manager** — Cohort curves, churn risk ranked by expected repurchase cadence, segment contribution margin, and custom segment saves.
- **Finance Controller** — Contribution margin breakdown with every cost driver sourced and versioned. Drift alerts. High-impact change confirmation gates. Historical restatement.
- **Operations Manager** — Inventory health by SKU with days-to-stockout, overstock and slow-moving detection, anomaly alerts, and stockout impact in revenue terms.
- **Brand Admin** — Integration health, user access management, notification routing, audit logs, and billing governance. The operational backbone.

---

#### Section 10 — Integrations (small icons row)

**Heading:** Connects to the tools your brand already runs on.

Row of logos (styled simply): Shopify · Meta Ads · Google Ads

*More connectors coming soon.*

---

#### Section 11 — CTA Footer Banner

**Heading:** Ready to see your business clearly?

**Body:** AlpMark is currently accepting early access partners. If you run a D2C brand and want to make faster, more profitable decisions — we'd like to talk.

**CTA button (gradient):** `Request Early Access`

---

### Page 2: Features (/features)

A deeper breakdown of each of the six core capability areas from Section 5, one section per epic. Each section has:
- Short heading
- 3–4 feature bullet points (the most compelling ones)
- A stylised mockup/illustration

---

### Page 3: About (/about)

**Heading:** Built for the brands doing the hard work.

**Body:** AlpMark was built because D2C brands deserve the same quality of decision intelligence that was previously only accessible to large enterprise retail teams. Your data already tells the story — AlpMark helps you hear it, trust it, and act on it.

Small team section (placeholder: "Team coming soon").

---

### Page 4: Contact / Early Access (/contact)

Simple form:
- Brand name
- Name
- Email
- Monthly revenue range (dropdown: <£100k / £100k–£500k / £500k–£2M / £2M+)
- Message (optional)
- Submit button (gradient)

Confirmation message: "Thanks — we'll be in touch within 2 business days."

---

## 5. Navigation

**Top nav (sticky, frosted glass on scroll):**
- Logo: "AlpMark" in bold with a small mark/icon (blue-to-red gradient element)
- Links: Features · About · Contact
- CTA: `Request Early Access` (gradient button, compact)
- Dark/light toggle icon (right side)

**Footer:**
- Logo + tagline
- Links: Features · About · Contact · Privacy
- Copyright line
- Social icons (placeholder)

---

## 6. Animations and Interactions

- **Hero:** Subtle fade-up on load for headline, then sub-headline, then buttons.
- **Section entrance:** Elements fade up with a slight translateY on scroll (IntersectionObserver, not jarring).
- **Stat counters in Section 8:** Numbers count up when scrolled into view.
- **Feature cards:** Gentle lift on hover (translateY -4px, shadow increase).
- **Gradient buttons:** Shimmer or brightness increase on hover. No aggressive animations.
- Keep it elegant, not distracting. Performance matters.

---

## 7. Technical Requirements

- **Framework:** React or Next.js preferred (or whatever Replit recommends for a clean fast site).
- **Styling:** Tailwind CSS.
- **Dark/light mode:** CSS variables + Tailwind dark: classes + localStorage toggle.
- **Responsive:** Mobile-first. Everything must work on iPhone and iPad screens as well as desktop.
- **Performance:** No heavy libraries. Minimal JS on load. Fast TTI.
- **No backend needed** for the marketing site — static export is fine. Contact form can post to a simple endpoint or use a service like Formspree.

---

## 8. What Good Looks Like

Reference aesthetics (not to copy, but to calibrate the quality and feel):
- **Linear.app** — clean, fast, dark-mode-first, purposeful
- **Hex.tech** — data-product energy, confident typography
- **Vercel.com** — crisp, gradient text, hero confidence
- **Raycast.com** — bold hero, tasteful glassmorphism

AlpMark sits at the intersection of **finance intelligence** and **operational clarity** — the design should feel precise, trustworthy, and modern. Not playful. Not enterprise-grey. Sharp.

---

*End of brief.*
