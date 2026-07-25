---
name: Orbital Intelligence
colors:
  surface: '#0b141c'
  surface-dim: '#0b141c'
  surface-bright: '#313a43'
  surface-container-lowest: '#060f16'
  surface-container-low: '#141c24'
  surface-container: '#182028'
  surface-container-high: '#222b33'
  surface-container-highest: '#2d363e'
  on-surface: '#dae3ee'
  on-surface-variant: '#c0c7d4'
  inverse-surface: '#dae3ee'
  inverse-on-surface: '#29313a'
  outline: '#8b919d'
  outline-variant: '#414752'
  surface-tint: '#a2c9ff'
  primary: '#a2c9ff'
  on-primary: '#00315c'
  primary-container: '#58a6ff'
  on-primary-container: '#003a6b'
  inverse-primary: '#0060aa'
  secondary: '#c6c6cc'
  on-secondary: '#2f3035'
  secondary-container: '#47494e'
  on-secondary-container: '#b7b8be'
  tertiary: '#c1c7d0'
  on-tertiary: '#2b3138'
  tertiary-container: '#9da3ac'
  on-tertiary-container: '#343a41'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d3e4ff'
  primary-fixed-dim: '#a2c9ff'
  on-primary-fixed: '#001c38'
  on-primary-fixed-variant: '#004882'
  secondary-fixed: '#e2e2e8'
  secondary-fixed-dim: '#c6c6cc'
  on-secondary-fixed: '#1a1c20'
  on-secondary-fixed-variant: '#45474b'
  tertiary-fixed: '#dde3ec'
  tertiary-fixed-dim: '#c1c7d0'
  on-tertiary-fixed: '#161c23'
  on-tertiary-fixed-variant: '#41474f'
  background: '#0b141c'
  on-background: '#dae3ee'
  surface-variant: '#2d363e'
  background-deep: '#000000'
  surface-glass: rgba(22, 27, 34, 0.7)
  success-glow: '#3fb950'
  danger-alert: '#f85149'
  warning-amber: '#d29922'
  border-muted: '#30363d'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  metric-xl:
    fontFamily: JetBrains Mono
    fontSize: 40px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: -0.04em
  metric-lg:
    fontFamily: JetBrains Mono
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  metric-sm:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.1em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The design system is engineered for **CRI Metrics**, an AI infrastructure market intelligence dashboard. The brand personality is hyper-technical, authoritative, and visionary, drawing direct inspiration from aerospace command-and-control interfaces (NASA/SpaceX). It evokes an emotional response of precision, high-stakes reliability, and "mission control" oversight.

The chosen style is **Glassmorphism mixed with Technical Minimalism**. The UI utilizes deep, "true black" foundations to minimize ocular strain during long monitoring sessions, while layering translucent surfaces to establish a sense of sophisticated spatial depth. Key visual markers include:
- **Luminescent Accents:** High-saturation glows that signal "live" data and active states.
- **Precision Grids:** Subtle background patterns that reinforce the architectural nature of AI infrastructure.
- **Monospaced Data:** Treating numerical information as primary engineering data rather than mere text.

## Colors

The palette is strictly optimized for high-contrast visibility in dark environments. 

- **Foundations:** The primary background uses `#0f1115`, while deep black (`#000000`) is used for the base layout to create an infinite depth effect behind glass components.
- **Accents:** The Primary Blue (`#58a6ff`) acts as the "active signal" across the platform. 
- **Semantic Status:** 
    - **Live Mode:** Utilizes `#3fb950` with a soft outer glow to represent operational health.
    - **Simulation Mode:** Utilizes `#f85149` to signal critical testing or high-risk states.
    - **Warning:** Utilizes `#d29922` for transient issues.
- **Borders:** Borders are kept thin and low-contrast (`#30363d`) to maintain the "glass" aesthetic without creating visual clutter.

## Typography

This design system uses a dual-font strategy to differentiate between narrative interface elements and raw intelligence data.

- **UI & Navigation (Inter):** Used for all structural labels, headings, and instructional text. It provides a clean, neutral, and highly legible framework.
- **Metrics & Data (JetBrains Mono):** This is the "soul" of the dashboard. All numbers, hardware specs, timestamps, and terminal outputs must use this monospaced face. It ensures that digits align vertically in data tables and reinforces the technical nature of AI infrastructure monitoring.
- **Visual Hierarchy:** Large "Metric-XL" styles are reserved for primary KPIs, while "Label-Caps" are used for hardware metadata and small utility tags.

## Layout & Spacing

The layout utilizes a **12-column Fixed Grid** for desktop views (max-width 1440px) to maintain a "dashboard cockpit" feel where elements remain in predictable locations.

- **Rhythm:** A 4px baseline unit governs all spacing, ensuring perfect mathematical alignment.
- **Grid Layout:** Elements should prefer "stack" groupings. Gutters are kept wide (24px) to let the glass panels breathe against the black background.
- **Responsiveness:**
    - **Desktop (12 columns):** Full dashboard view with side navigation.
    - **Tablet (8 columns):** Cards reflow into a 2-stack layout.
    - **Mobile (4 columns):** Full-width card stacking with bottom-fixed navigation for high-priority alerts.
- **Grid Pattern:** A subtle 20px grid line pattern (opacity 0.05) should be overlayed on the primary background to assist with visual alignment.

## Elevation & Depth

Hierarchy is established through **optical translucency** rather than traditional drop shadows.

1.  **Level 0 (Base):** Black background (#000000) with a faint CSS `conic-gradient` or grid pattern to simulate depth.
2.  **Level 1 (Panels):** Surface-glass (22, 27, 34, 0.7) with a 10px backdrop-filter blur. These use a 1px solid border (#30363d).
3.  **Level 2 (Active/Hover):** When a card or element is focused, it gains a subtle outer glow (box-shadow: 0 0 15px rgba(88, 166, 255, 0.15)) and the border brightness increases.
4.  **Level 3 (Overlays):** Modals and tooltips use a higher opacity (0.9) and a more pronounced 1px border (#58a6ff at 0.5 opacity) to "float" above the dashboard.

## Shapes

The shape language is **Soft (0.25rem)**. This avoids the toy-like feel of heavily rounded corners while steering clear of the aggressive nature of sharp 0px corners. 

- **Primary Elements:** Buttons, input fields, and small cards use `rounded` (4px).
- **Large Containers:** Dashboard widgets and sections use `rounded-lg` (8px).
- **Status Indicators:** Use `pill` shapes for badges (Live, Sim, Active) to distinguish them from functional UI blocks.

## Components

- **Cards:** The core of the dashboard. Must feature `backdrop-filter: blur(10px)`, a 1px border, and a subtle inner-glow at the top edge to simulate light hitting a physical glass panel.
- **Buttons:**
    - *Primary:* Solid #58a6ff with black text. On hover, add a 10px blue outer glow.
    - *Ghost:* Transparent with #30363d border. On hover, border turns to #58a6ff.
- **Status Badges:** 
    - Include a "Pulse" animation (a secondary circle expanding and fading) for **LIVE** states using the success-glow color.
- **Progress Bars:** Use linear gradients. For example, a "System Load" bar should transition from #3fb950 (green) to #d29922 (amber) as it fills.
- **Input Fields:** Darker than the card surface (rgba(0,0,0,0.3)) with monospaced text for data entry.
- **Data Tables:** Row headers in Inter, but all cell data in JetBrains Mono. Use zebra-striping with subtle opacity changes (0.02) rather than solid lines.
- **Glow Accents:** Use "Glow Points" sparingly—small, 2px circles of pure color next to headers to indicate system health without overwhelming the user.