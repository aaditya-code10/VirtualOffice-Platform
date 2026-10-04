FIX THE CURRENT VIRTUALOFFICE LIQUID GLASS UI LAYOUT.

IMPORTANT:
DO NOT REDESIGN THE UI.
DO NOT CHANGE THE COLOR PALETTE.
DO NOT REMOVE THE LIQUID GLASS EFFECTS.
DO NOT CHANGE THE CURRENT VISUAL STYLE.

The current design is visually good, but there is a serious desktop layout/overflow issue.

I have attached a screenshot showing the current problem.

==================================================
CURRENT PROBLEMS
==================================================

1. The main content extends beyond the right side of the viewport.

2. The Command Center hero/input area is wider than the available viewport.

3. The "Execute Deep Assessment" button is partially outside the visible screen.

4. The Autonomous Multi-Agent Execution Pipeline extends horizontally beyond the viewport.

5. The top-right AI Workforce status / model badge / notification / avatar are being squeezed.

6. The floating action button is too close to the right edge.

7. The page appears to have an unintended minimum/fixed width.

8. The layout should never require horizontal scrolling on normal desktop resolutions.

9. The sidebar + main content + page padding must fit inside:
   100vw.

==================================================
DESIRED LAYOUT
==================================================

Use this structure:

BODY
└── APP SHELL
    ├── SIDEBAR
    │   fixed / controlled width
    │
    └── MAIN AREA
        ├── TOP BAR
        └── CONTENT
            ├── COMMAND CENTER
            ├── EXECUTION PIPELINE
            └── DASHBOARD SECTIONS

The main area must use:

width: calc(100vw - sidebarWidth)

and:

min-width: 0;

The content itself must use:

width: 100%;
max-width: none;
min-width: 0;

Do NOT use large hardcoded widths such as:

width: 1400px;
width: 1600px;
min-width: 1200px;

unless absolutely necessary.

==================================================
SIDEBAR
==================================================

Desktop sidebar:

width approximately:
260px

Use:

flex: 0 0 260px;

The main content must shrink correctly beside it.

For the main application shell use something similar to:

display: flex;
width: 100%;
min-height: 100vh;
overflow-x: hidden;

Main:

flex: 1;
min-width: 0;
width: 0;

The combination of:

flex: 1;
min-width: 0;

is important.

==================================================
TOP BAR
==================================================

The top bar must never overflow.

Use:

display: flex;
align-items: center;
justify-content: space-between;
min-width: 0;

Left section:

flex: 1;
min-width: 0;

Right controls:

display: flex;
align-items: center;
flex-shrink: 0;

At smaller desktop widths, the model badge can become smaller or disappear.

Do not allow the top bar to create horizontal overflow.

==================================================
COMMAND CENTER
==================================================

The Command Center must fit entirely inside the available content width.

The command panel should use:

width: 100%;
max-width: 100%;
min-width: 0;
box-sizing: border-box;

The command input area must be responsive.

Current problem:

The Execute Deep Assessment button extends beyond the right edge.

Fix using a responsive layout.

Desktop:

INPUT + BUTTON

At normal width:

grid-template-columns:
minmax(0, 1fr) auto;

Example:

display: grid;
grid-template-columns: minmax(0, 1fr) auto;
gap: 12px;

Input:

min-width: 0;

Button:

flex-shrink: 0;

At smaller widths:

grid-template-columns: 1fr;

Then the button goes below the input.

==================================================
SECTOR FILTERS
==================================================

The sector pills must not force the page wider.

Use:

display: flex;
gap: 8px;
overflow-x: auto;
max-width: 100%;

The scrollbar can be visually hidden.

The pills themselves should have:

flex: 0 0 auto;

Do NOT let them increase the width of the entire page.

==================================================
QUICK PROMPTS
==================================================

Same principle.

Use:

display: flex;
flex-wrap: wrap;

or:

overflow-x: auto;

Never allow quick prompt chips to expand the page width.

==================================================
MULTI-AGENT EXECUTION PIPELINE
==================================================

THIS IS THE MOST IMPORTANT FIX.

The current pipeline is wider than the viewport.

Do NOT keep one enormous horizontal fixed-width pipeline.

Create a responsive pipeline.

Desktop:

display: grid;

with stages that can shrink.

Example:

grid-template-columns:
minmax(150px, 1fr)
minmax(150px, 1fr)
minmax(280px, 2fr)
minmax(180px, 1fr)
minmax(150px, 1fr);

But:

min-width: 0;

must be applied to every stage.

For the specialist group:

allow the agents to wrap.

Example:

display: flex;
flex-wrap: wrap;

Each agent chip:

flex: 1 1 auto;

Do NOT use fixed widths that exceed the available space.

==================================================
PIPELINE RESPONSIVE BREAKPOINT
==================================================

At approximately:

1200px

compress the pipeline.

At approximately:

1000px

change the pipeline into a vertical/stacked workflow:

01 Venture Intent
↓
02 Dynamic Router
↓
03 Parallel Specialist Evaluation
↓
04 Executive Synthesis
↓
05 Decision

This is much better than clipping the content.

==================================================
MAIN DASHBOARD GRID
==================================================

For dashboard cards use:

grid-template-columns:
repeat(auto-fit, minmax(280px, 1fr));

instead of fixed columns where possible.

Cards must have:

min-width: 0;

overflow: hidden;

box-sizing: border-box;

==================================================
GLOBAL OVERFLOW
==================================================

Fix the root layout.

Use:

html,
body,
#root {
    width: 100%;
    min-height: 100%;
    margin: 0;
}

body {
    overflow-x: hidden;
}

Do NOT use:

overflow-x: hidden

as the ONLY fix.

The actual child elements must be corrected so they do not exceed the viewport.

==================================================
GLASS CARDS
==================================================

Preserve:

backdrop-filter
blur
border
violet glow
dark glass surfaces

But make every card:

width: 100%;
max-width: 100%;
min-width: 0;
box-sizing: border-box;

==================================================
FLOATING AI BUTTON
==================================================

The floating AI button must use:

position: fixed;
right: 24px;
bottom: 24px;

with:

z-index: high;

At mobile:

right: 16px;
bottom: 16px;

It must never cause horizontal overflow.

==================================================
RESPONSIVE BREAKPOINTS
==================================================

Implement at least:

>= 1440px
Full desktop layout.

1200–1439px
Compressed desktop.

900–1199px
Tablet/compact desktop.

< 900px
Sidebar becomes collapsible/drawer.

< 640px
Single-column mobile layout.

==================================================
IMPORTANT CSS RULE
==================================================

Search the entire frontend for:

width:
min-width:
100vw
px fixed widths
white-space: nowrap
flex-shrink
grid-template-columns

and identify anything that can create horizontal overflow.

Especially inspect:

- App shell
- Sidebar
- TopBar
- CommandCenter
- Command input
- Sector chips
- Quick prompts
- Execution pipeline
- Dashboard grids
- Floating buttons

==================================================
DO NOT CHANGE
==================================================

Do NOT change:

- current purple/violet palette
- glass effect
- animations
- logo
- typography
- sidebar design
- Command Center visual design
- AI workforce concept
- backend
- APIs
- authentication
- PostgreSQL
- work-order logic

Only correct layout, sizing, responsiveness and overflow.

==================================================
VALIDATION
==================================================

After making the changes:

Test at:

1920x1080
1600x900
1440x900
1366x768
1280x720
1024x768
900x768
768x1024
390x844

There must be:

NO horizontal scrollbar.

The Execute button must remain visible.

The complete execution pipeline must remain visible.

The sidebar must remain usable.

The top-right controls must remain usable.

The floating AI button must remain inside the viewport.

The Liquid Glass visual quality must remain unchanged.

Do not stop after changing CSS.

Run:

npm run build

and fix any TypeScript/build errors.

Then inspect the browser at 1440px and 1280px width and verify the entire page fits correctly.