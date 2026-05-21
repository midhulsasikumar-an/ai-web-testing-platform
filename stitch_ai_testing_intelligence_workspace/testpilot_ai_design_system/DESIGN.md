---
name: TestPilot AI Design System
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#ccc3d8'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#958da1'
  outline-variant: '#4a4455'
  surface-tint: '#d2bbff'
  primary: '#d2bbff'
  on-primary: '#3f008e'
  primary-container: '#7c3aed'
  on-primary-container: '#ede0ff'
  inverse-primary: '#732ee4'
  secondary: '#ffb95f'
  on-secondary: '#472a00'
  secondary-container: '#ee9800'
  on-secondary-container: '#5b3800'
  tertiary: '#7bd0ff'
  on-tertiary: '#00354a'
  tertiary-container: '#006e95'
  on-tertiary-container: '#caeaff'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#eaddff'
  primary-fixed-dim: '#d2bbff'
  on-primary-fixed: '#25005a'
  on-primary-fixed-variant: '#5a00c6'
  secondary-fixed: '#ffddb8'
  secondary-fixed-dim: '#ffb95f'
  on-secondary-fixed: '#2a1700'
  on-secondary-fixed-variant: '#653e00'
  tertiary-fixed: '#c4e7ff'
  tertiary-fixed-dim: '#7bd0ff'
  on-tertiary-fixed: '#001e2c'
  on-tertiary-fixed-variant: '#004c69'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-sm:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 38px
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
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
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 0.5rem
  sm: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  gutter: 24px
  margin-mobile: 16px
  container-max: 1440px
---

## Brand & Style

The design system is engineered for **TestPilot AI**, an enterprise-grade AI Operating System. The brand personality is authoritative yet visionary, combining the stability of a high-end financial institution with the cutting-edge aesthetic of a futuristic cockpit. It targets developers and C-suite executives who require precision, speed, and clarity.

The visual style is a refined blend of **Modern Minimalism** and **Glassmorphism**. It utilizes depth through translucency, light-refraction effects, and subtle "border-glows" to suggest a UI that exists as a light-based projection rather than a flat surface. Every interaction should feel responsive and high-tech, evoking the emotional response of being in total control of a sophisticated machine.

## Colors

The palette is anchored in a **Deep Navy** spectrum to provide a high-contrast foundation for luminous accents. 

- **Primary Violet (#7C3AED):** Used for core actions and brand presence. It represents the "intelligence" of the system.
- **Warm Amber (#F59E0B):** Reserved for high-value data points, alerts, and active "attention" states.
- **Glass Surfaces:** Surface colors should be applied with 60–80% opacity, utilizing `backdrop-filter: blur(12px)` to maintain legibility over complex backgrounds.
- **Border Glows:** Use the Primary Violet at 10–20% opacity for borders to create the "active energy" effect.

## Typography

This design system utilizes **Inter** as the primary typeface for its exceptional readability in dense data environments. To lean into the "AI Operating System" narrative, **JetBrains Mono** is used for technical labels, metadata, and code snippets.

- **Headlines:** Should be tight and impactful with slight negative letter-spacing.
- **Technical Data:** Use monospaced labels for any automated output or system status updates.
- **Hierarchy:** Maintain clear distinction by using font weight rather than size alone to indicate importance.

## Layout & Spacing

The system follows a **12-column fluid grid** for desktop, transitioning to a **4-column grid** for mobile. 

- **Layout Philosophy:** Use generous internal padding within cards (minimum 24px) to emphasize the "Glassmorphism" effect. 
- **Rhythm:** Spacing is based on a 4px baseline, ensuring all elements align to a consistent vertical and horizontal rhythm. 
- **Reflow:** On tablet/mobile, sidebars should collapse into a bottom navigation bar or a translucent overlay drawer to preserve screen real estate for data visualization.

## Elevation & Depth

Depth is conveyed through **Tonal Glassmorphism** rather than traditional heavy shadows.

1.  **Level 0 (Base):** Deep Navy (#0F172A).
2.  **Level 1 (Cards/Panels):** Translucent Navy (#1E293B at 70%) with a 1px border (#FFFFFF at 10%) and a 12px background blur.
3.  **Level 2 (Modals/Popovers):** Higher opacity (#1E293B at 90%) with a subtle Primary Violet outer glow (blur: 20px, spread: -5px, opacity: 15%).
4.  **Interactive States:** On hover, borders should transition from neutral grey-blue to Primary Violet to indicate focus.

## Shapes

The shape language is sophisticated and approachable. A consistent **12px to 16px corner radius** (defined as level 2) is applied to all primary containers and buttons. 

- **Buttons:** 12px rounded corners.
- **Main Cards:** 16px rounded corners.
- **Inputs:** 8px rounded corners to maintain a slightly more technical, structured appearance.
- **Avatars/Status Indicators:** Circular (Full pill) to contrast against the geometric grid.

## Components

- **Glowing Primary Buttons:** Features a linear gradient (Primary Violet to a slightly lighter tint) with a soft outer glow in the same hue. Text is always white for maximum contrast.
- **Floating Cards:** Glass panels with a 1px border. Use "inner-glow" (box-shadow: inset) to simulate light hitting the edges of the glass.
- **Futuristic Toggles:** Instead of a simple sliding dot, use a shape-shifting track that glows Amber when "On" and remains a muted Navy when "Off."
- **Data Chips:** Monospaced text inside semi-transparent capsules. Use Primary Violet for system tags and Warm Amber for "active" or "warning" tags.
- **Input Fields:** Minimalist design with only a bottom border that expands to a full "glow" box on focus.
- **Terminal Component:** A dedicated area for AI logs using JetBrains Mono, styled with a darker, 90% opaque background to differentiate from standard UI cards.