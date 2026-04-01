# Design System: Product Showcase Website (V20260331_1515)

## 1. Vision & Core Principles
A high-end, systems-oriented showcase that balances editorial elegance with technical precision. This is not a brochure; it's a demonstration of capability.
- **Semantic First:** Clean HTML structure, proper ARIA labels, and logical heading hierarchy.
- **Performance Driven:** Compositor-friendly animations (opacity/transform only), no layout shifts, optimized asset loading.
- **Balanced Typography:** Precision-scaled text with 1.6+ line-height for readability and proper character entities.
- **Interactive Clarity:** Every button, link, and input must have distinct `:hover`, `:focus-visible`, and `:active` states.

## 2. Color Palette & Accessibility
- **Background (Base):** `#F8F9FA` (Soft Grey/Off-white) - High-end, clean canvas.
- **Surface (Elevated):** `#FFFFFF` - For cards and distinct panels with subtle `0 10px 30px rgba(0,0,0,0.03)` shadows.
- **Primary Text:** `#111827` (Deep Indigo Black) - Optimized for contrast (WCAG AAA).
- **Secondary Text:** `#4B5563` (Slate) - For metadata and support copy.
- **Accent (Commercial):** `#2563EB` (Vivid Blue) - Professional, high-trust accent for primary CTAs and active states.
- **Border:** `#E5E7EB` - Fine hairline dividers (1px).

## 3. Typography (Performance & Polish)
- **Primary Font:** `Inter` or `Geist` (if available via CDN) - Modern, optimized for screens.
- **Display Font:** `Outfit` (700+) - For headlines, high impact.
- **Monospace:** `JetBrains Mono` - For "metadata" (tags, numbers, technical details).
- **Guidelines:** 
  - Headlines: Tight tracking (-0.02em).
  - Body: Relaxed tracking (0.01em) and balanced measure (max-width: 65ch).

## 4. Component Standards
- **Buttons:** 
  - Primary: Solid Accent, white text, 6px border-radius, subtle transition on background-color.
  - Secondary: Ghost style with 1px border.
  - States: Scale down slightly on `:active` (98%).
- **Service Sections:** 
  - Asymmetrical grid layouts. 
  - Detailed feature lists using semantic `<ul>` and refined markers.
  - Use case boxes for social proof/application context.
- **Cards:** No heavy borders. Use subtle shadows and background shifts for elevation.

## 5. Interaction & Motion
- **Transitions:** Standardized `cubic-bezier(0.4, 0, 0.2, 1)` for all transforms.
- **Reveal:** Staggered entrance animations for content blocks as they enter the viewport.
- **Feedback:** Clear focus rings (outline: 2px solid primary accent with offset).

## 6. Content Depth Requirements
Each service must include:
1. **The Vision:** High-level value proposition.
2. **The Execution:** 3-4 bulleted technical capabilities.
3. **The Outcome:** The measurable business impact.
4. **Context:** A "Typical Engagement" or "Use Case" example.

## 7. Anti-Patterns
- No `transition: all`.
- No non-semantic `div` buttons.
- No blocking of native user actions (zoom, copy, paste).
- No generic template imagery.
- No "scroll-jacking".
