---
name: TestPilot AI
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#434655'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#006591'
  on-secondary: '#ffffff'
  secondary-container: '#39b8fd'
  on-secondary-container: '#004666'
  tertiary: '#46566c'
  on-tertiary: '#ffffff'
  tertiary-container: '#5e6e85'
  on-tertiary-container: '#e9f0ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#c9e6ff'
  secondary-fixed-dim: '#89ceff'
  on-secondary-fixed: '#001e2f'
  on-secondary-fixed-variant: '#004c6e'
  tertiary-fixed: '#d3e4fe'
  tertiary-fixed-dim: '#b7c8e1'
  on-tertiary-fixed: '#0b1c30'
  on-tertiary-fixed-variant: '#38485d'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
  max-width: 1440px
---

## Brand & Style
This design system embodies a high-velocity, AI-first enterprise aesthetic. It blends the precision of modern developer tools with the approachability of premium consumer software. The brand personality is **intelligent, surgical, and forward-leaning**, designed to evoke a sense of trust and technological edge.

The visual style is a sophisticated mix of **Corporate Modern** and **Glassmorphism**. It prioritizes extreme clarity through heavy whitespace and a refined color palette, while using translucent layers and subtle background blurs to signify "intelligence" and depth. Inspired by the lean, functional elegance of industry leaders like Linear and Stripe, the UI remains unobtrusive, allowing the user's data and the AI's insights to remain the focal point.

## Colors
The palette is rooted in a "Global Blue" spectrum, utilizing a range of high-clarity blues to establish hierarchy and action. 

- **Primary & Accent:** The Primary Blue (#2563EB) is used for core actions and brand presence. The Sky Accent (#0EA5E9) is reserved for AI-driven highlights or secondary interactive elements to provide a "futuristic" glow.
- **Neutrals:** We utilize a Slate-based neutral scale. This ensures that text has high legibility without the harshness of pure black, maintaining a premium "software" feel.
- **Backgrounds:** A tiered system starting from a cool Slate-50 (#F8FAFC) for the base, rising to pure White for elevated surfaces, and using a soft Blue-50 (#EFF6FF) for subtle grouping or active areas.

## Typography
We exclusively use **Inter** to maintain a systematic, utilitarian, and modern feel. The typographic scale emphasizes tight tracking and generous line heights to ensure readability in data-heavy enterprise environments.

- **Headlines:** Use Semi-Bold (600) with slight negative letter-spacing to create a "locked-in" professional appearance.
- **Body:** Standardized at 16px for optimal legibility.
- **Labels:** Used for metadata, small buttons, and table headers. The small label uses an uppercase transformation with increased letter-spacing to distinguish it from body copy.

## Layout & Spacing
The layout follows a **Fixed-Fluid hybrid model**. Core dashboard views are constrained to a 1440px max-width container to maintain focus, while internal components utilize a fluid 12-column grid.

The spacing rhythm is built on an **8px base unit**. Generous margins (40px on desktop) and gutters (24px) create a "spacious" feeling that reduces cognitive load—essential for AI-assisted workflows. On mobile, margins compress to 16px, and multi-column layouts reflow into a single-stack vertical stream. Use `gap-md` (16px) for standard component spacing and `gap-lg` (24px) for major section separation.

## Elevation & Depth
Hierarchy is conveyed through **Glassmorphism and Ambient Shadows**. 

1.  **Level 0 (Base):** The #F8FAFC background.
2.  **Level 1 (Cards):** White surfaces with a very soft, diffused shadow (0px 4px 20px rgba(15, 23, 42, 0.05)) and a subtle 1px border (#E2E8F0).
3.  **Level 2 (Floating/Modals):** Pure white with a slightly stronger shadow and a `backdrop-filter: blur(12px)` on the layer immediately beneath.
4.  **Interactive Elements:** Hover states use a subtle "lift"—increasing shadow spread and reducing border opacity to create a tactile sense of interaction.

Avoid heavy black shadows. Use tinted shadows (Indigo-900 at 5-8% opacity) to keep the "light and airy" enterprise feel.

## Shapes
The design system uses a **Rounded** shape language to soften the technical nature of the AI platform. 

- **Standard Elements:** 0.5rem (8px) for buttons, input fields, and small chips.
- **Containers:** 1rem (16px) for primary cards and content blocks.
- **Large Layouts:** 1.5rem (24px) for main dashboard sections or large promotional banners.

This consistent rounding ensures the UI feels approachable and modern, steering clear of the "sharpness" often associated with legacy enterprise software.

## Components
- **Buttons:** Primary buttons use a solid #2563EB fill with white text. Secondary buttons use a #FFFFFF background with a 1px border (#E2E8F0) and slate text. Active states should include a subtle 2px outer glow in the primary color.
- **Glass Cards:** Used for AI insights. These should have a slight transparency (90-95% opacity white), a 1px white border for a "highlighted edge," and a background blur.
- **Inputs:** Clean, white backgrounds with #E2E8F0 borders. On focus, the border transitions to #3B82F6 with a soft 4px blue shadow ring (10% opacity).
- **Chips:** Small, rounded-pill shapes. For status (Success/Error), use a 10% opacity fill of the status color with high-contrast text.
- **AI Signature:** Any AI-generated content should be housed in a card with a subtle linear gradient border (Primary Blue to Sky Accent) to denote its origin.
- **Lists:** Clean rows with 1px bottom borders. Hovering a row should apply the #EFF6FF background color with a 4px corner radius.