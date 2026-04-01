# Design System: Premium Salon Sales Tool (V20260331_1605)

## 1. Vision & Strategy
The goal is to create a "finished" website that feels like a premium upgrade the client can immediately imagine owning. 
- **Emotional Impact:** High-end, clean, and welcoming. Focus on the "experience" of the salon.
- **Professionalism:** Remove all "internal" meta-data (legacy scores, audit notes). 
- **Conversion-Ready:** Clear "Book Appointment" and "Call Now" triggers.
- **Vercel Standards:** Apply semantic HTML, performance-first animations, and perfect accessibility.

## 2. Aesthetic & Palette
- **The "High-End" Canvas:** 
  - **Primary Background:** `#FAFAFA` (Pure, clean) or `#111111` (Moody/Modern for Barbers).
  - **Surface:** `#FFFFFF` with ultra-soft shadows (`0 4px 20px rgba(0,0,0,0.02)`).
- **Typography Stacks:**
  - **Serif (Elegant):** `Cormorant Garamond` for Headlines — suggests heritage and craftsmanship.
  - **Sans (Modern):** `Outfit` or `Inter` for UI and body — suggests efficiency and precision.
- **Accents:** 
  - **Gold/Bronze:** `#B8860B` for high-end salons.
  - **Deep Charcoal:** `#262626` for modern barbers.
  - **Single Signature Color:** Tailored to the business name (e.g., "Fun Cuts" might use a soft playful teal, "Damascus" a deep desert earth).

## 3. Component Standards (Vercel Guidelines)
- **Hero Section:** 
  - Editorial layout. Large, high-quality placeholder imagery (via Unsplash/Picsum).
  - Headline focuses on the *benefit* (e.g., "Your Best Look, Refined.").
- **Service Menu:** 
  - Clean, list-based menu with clear pricing and descriptions.
  - Avoid generic grid cards; use a more "menu-like" sophisticated layout.
- **Interactivity:**
  - `IntersectionObserver` for staggered reveals.
  - Sticky navigation with a glassmorphism (backdrop-filter) effect.
  - Clear `:focus-visible` states for accessibility.
- **Content:**
  - Expand on the salon's value. 
  - Include "Why Choose Us" and "Client Experience" sections.

## 4. Technical Constraints
- No `transition: all`.
- No layout shifts (CLS).
- Responsive from 320px to 1920px.
- Semantic landmarks (`<header>`, `<main>`, `<nav>`, `<section>`, `<footer>`).

## 5. Sales Framing
- The "Upgrade Notes" from the original task will be converted into a "Professional Web Standards" badge or a subtle "Modern Tech" section in the footer, showing the client that the site is "Fast, Accessible, and SEO-Optimized" without using the word "Legacy".
