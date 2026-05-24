# Category panels and status colours

Per–life-area reference for the **Categories** grid and each category detail page in the [UI prototype](ui-prototype.md). Nine planned feature labels map to **eight category tiles** (Shopping and Pantry are separate; **Calendar** is a bottom-nav view, not a grid tile). See [planned features](planned-features.md) for capability overview.

## Two colour systems

The prototype uses green, yellow, and red in two places. **Do not mix the rules.**

| Where | What it reflects |
|-------|------------------|
| **Category tile** (grid) | Overall health of that life area — rules are **defined per category** below |
| **Task row** (lists) | Schedule urgency — **same everywhere** (overdue, due within 2 hours, regular). See [Status colours in ui-prototype.md](ui-prototype.md#status-colors-green-yellow-red) |

Each category section documents **tile colours** and **panel layout**. Task-row colours follow the global schedule rules unless a category explicitly adds extra row semantics.

---

## Document status

| Category | Tile label | Documented |
|----------|------------|------------|
| Shopping | Shopping | Documented |
| Pantry | Pantry | Documented |
| Chores | Chores | Documented |
| Personal tasks | Tasks | — |
| Health | Health | — |
| Hobbies | Hobbies | — |
| Goals | Goals | — |
| Automation | Automation | — |

---

## Shopping

**Planned area:** [Household Shopping Management](planned-features.md#household-shopping-management)

**Prototype page:** [categories/shopping.html](ui-prototype/categories/shopping.html)

### Purpose

Track items to buy across food, drinks, household supplies, hygiene, and other shopping categories. Lists can be built manually or generated from low pantry stock.

### Category tile (grid)

**Sample subtitle:** `7 to buy`

**Prototype tile colour:** Green (`square-link--ok`) — sample data has 7 open shopping-list rows (&lt; 10).

| Colour | Meaning |
|--------|---------|
| Green | Fewer than **10** open shopping-list items |
| Yellow | **More than 10** open shopping-list items |
| Red | *(reserved — e.g. very large backlog; not used in prototype sample)* |

**Thresholds and edge cases**

- **Shopping count** = open (unchecked) rows on the Shopping detail page.
- **Empty list** → green; subtitle e.g. `List clear`.
- **Completed rows** do not count toward the threshold.
- Tile colour is independent of task-row schedule colours.

### Category panel (detail page)

**Layout:** single scrollable **To buy** list (same task-row UI as [Tasks](ui-prototype/tasks.html)).

- **Header:** title *Shopping*; subtitle with open count and auto-import note (e.g. `7 to buy · includes missing pantry items automatically`).
- **Top actions:** header back arrow (**←**) to categories grid and a **+ Add** button.
- **Main:** checkbox, title, meta (sub-category · need qty · schedule hint). Scrolls when long.
- **Empty state:** “Nothing on the list”.

**Actions / affordances**

- Mark bought (checkbox).
- **+ Add** — [add-shopping-item.html](ui-prototype/add-shopping-item.html): item name, type (Household, Beverages, …), quantity needed, notes. No date, time, or priority.
- Back via toolbar or header ←.

### Task row colours in this category

Uses **global schedule rules** (due date/time).

### Notes

Separate from **Pantry** on the grid. Low stock is managed on the Pantry tile; shopping list can still be generated from pantry rules in the full app.

---

## Pantry

**Planned area:** [Pantry and Home Inventory](planned-features.md#pantry-and-home-inventory)

**Prototype page:** [categories/pantry.html](ui-prototype/categories/pantry.html)

### Purpose

Track quantity at home vs required level for household inventory. Adjust stock with **−1** / **+1**; items below required can feed the Shopping list.

### Category tile (grid)

**Sample subtitle:** `5 low stock`

**Prototype tile colour:** Yellow (`square-link--warn`) — sample data has 5 items below required quantity.

| Colour | Meaning |
|--------|---------|
| Green | **No** tracked items below required quantity |
| Yellow | **1–9** items below required quantity |
| Red | **10 or more** items below required quantity |

**Thresholds and edge cases**

- **Below-required count** = tracked items where *quantity at home* &lt; *required quantity*.
- **Empty tracker** → green; subtitle e.g. `Nothing tracked`.
- **All stock at or above required** → green; subtitle e.g. `Stock OK`.
- Tile colour is independent of task-row schedule colours.

### Category panel (detail page)

**Layout:** single scrollable pantry inventory list.

- **Header:** title *Pantry*; subtitle (e.g. `8 tracked · 5 below required`).
- **Top actions:** header back arrow (**←**) to categories grid and a **+ Add** button.
- **Main:** product name, sub-category, **at home / required** meta, **−1** and **+1** buttons per row. Low-stock rows use `pantry-item--low` emphasis.
- **Empty state:** “No pantry items tracked yet”.

**Actions / affordances**

- **−1** / **+1** — decrement/increment quantity at home (prototype updates meta and header counts).
- **+ Add** — [add-pantry-item.html](ui-prototype/add-pantry-item.html): item name, type, **required** and **at home** quantities (at home defaults to 0), notes. No date, time, or priority.
- Back via toolbar or header ←.

### Task row colours in this category

No schedule-based row colours — stock status is shown in meta and low-stock border only.

### Notes

Reference example for inventory-style category panels. **Shopping** tile covers the buy list only.

---

## Chores

**Planned area:** [Chores and Home Maintenance](planned-features.md#chores-and-home-maintenance)

**Prototype page:** [categories/chores.html](ui-prototype/categories/chores.html)

### Purpose

Track **recurring household chores** with a **type** and **repeat interval** (every 7–10 days in the sample). Each chore reschedules after completion; the panel shows how far behind the cycle is, not one-off due dates only.

### Category tile (grid)

**Sample subtitle:** `2 overdue`

**Prototype tile colour:** Yellow (`square-link--warn`) — sample has two chores **8–14 days** past due; none more than 14 days late.

| Colour | Meaning |
|--------|---------|
| Green | **No** open chore is more than **7 days** past its due cycle |
| Yellow | **No** open chore is more than **14 days** late, but **at least one** is **8–14 days** late |
| Red | **At least one** open chore is more than **14 days** past its due cycle |

**Thresholds and edge cases**

- **Cycle delay** = days since the chore was due (from last completion + frequency), for open (incomplete) chores.
- **Worst delay** among open chores sets the tile colour.
- **Empty list** → green; subtitle e.g. `No chores set`.
- **All on schedule** (worst delay ≤ 7 days, including due today) → green; subtitle e.g. `All on schedule`.
- **Paused** chores are excluded from delay counts (subtitle may note e.g. `1 paused`).
- Tile colour is independent of task-row schedule colours on the list.

### Category panel (detail page)

**Layout:** scrollable recurring-chore list in **three sections** (same task-row UI as [Tasks](ui-prototype/tasks.html)).

- **Header:** title *Chores*; subtitle with counts (e.g. `7 recurring · 2 overdue`).
- **Top actions:** header back arrow (**←**) to categories grid and **+ Add** → [add-chores-item.html](ui-prototype/add-chores-item.html).
- **Sections (top to bottom):**
  - **Overdue** — cycle delay &gt; 0 days; sorted by most overdue first.
  - **Due soon** — due today or next day.
  - **On schedule** — not yet due; sorted by next due soonest.
- **Main row:** checkbox, title, meta line: **type** · **Every N days** · status (e.g. `10 days overdue`, `Due today`, `Due in 5 days`).
- **Empty state:** “No chores yet — add a recurring task”.

**Chore types** (select on add form; shown as row tag):

| Type |
|------|
| Cleaning |
| Laundry |
| Washing dishes |
| Taking out trash |
| Changing bedsheets |
| Watering plants |
| General home maintenance |

**Sample content (prototype):** seven chores with frequency **every 7–10 days** — e.g. vacuum (Cleaning, 7d, 10 days overdue), change bedsheets (12d overdue), water plants (8d, due today), take out trash (7d, tomorrow), dishwasher (7d), laundry (10d), HVAC filter (Maintenance, 10d).

**Actions / affordances**

- Mark done (checkbox) — resets the cycle from today + frequency.
- **+ Add** — chore name, **type**, **frequency** (7–10 days); no priority field.
- Back via header ←.

### Task row colours in this category

Uses **global schedule rules** (due date/time for the current cycle instance). Row border does not replace tile cycle-delay rules.

### Notes

Chores are **recurring by frequency**, not arbitrary one-off schedules. Household assignment and maintenance reminders (filters, appliances) are planned in the full app; the prototype focuses on type + interval + overdue grouping.

---

## Personal tasks

**Planned area:** [Personal Tasks and Responsibilities](planned-features.md#personal-tasks-and-responsibilities)

**Prototype page:** [categories/personal.html](ui-prototype/categories/personal.html) · Grid label: **Tasks**

### Purpose

*(to be filled)*

### Category tile (grid)

**Sample subtitle:** `3 open today`

| Colour | Meaning |
|--------|---------|
| Green | *(to be filled)* |
| Yellow | *(to be filled)* |
| Red | *(to be filled)* |

### Category panel (detail page)

**Layout:** *(to be filled)*

**Content types shown:** *(to be filled)*

**Sections or grouping:** *(to be filled)*

**Actions / affordances:** *(to be filled)*

### Task row colours in this category

Uses global schedule rules unless noted otherwise.

### Notes

*(to be filled)*

---

## Calendar (view — not on Categories grid)

**Planned area:** [Calendar and Events](planned-features.md#calendar-and-events)

**Prototype:** month view only — [calendar.html](ui-prototype/calendar.html) (bottom nav **Calendar** tab). There is **no** Calendar tile on the Categories grid; scheduling is a cross-cutting view, not a life-area category panel.

---

## Health

**Planned area:** [Health, Training, and Routines](planned-features.md#health-training-and-routines)

**Prototype page:** [categories/health.html](ui-prototype/categories/health.html)

### Purpose

*(to be filled)*

### Category tile (grid)

**Sample subtitle:** `Workout skipped`

| Colour | Meaning |
|--------|---------|
| Green | *(to be filled)* |
| Yellow | *(to be filled)* |
| Red | *(to be filled)* |

### Category panel (detail page)

**Layout:** *(to be filled)*

**Content types shown:** *(to be filled)*

**Sections or grouping:** *(to be filled)*

**Actions / affordances:** *(to be filled)*

### Task row colours in this category

Uses global schedule rules unless noted otherwise.

### Notes

*(to be filled)*

---

## Hobbies

**Planned area:** [Hobbies and Personal Development](planned-features.md#hobbies-and-personal-development)

**Prototype page:** [categories/hobbies.html](ui-prototype/categories/hobbies.html)

### Purpose

*(to be filled)*

### Category tile (grid)

**Sample subtitle:** `On track`

| Colour | Meaning |
|--------|---------|
| Green | *(to be filled)* |
| Yellow | *(to be filled)* |
| Red | *(to be filled)* |

### Category panel (detail page)

**Layout:** *(to be filled)*

**Content types shown:** *(to be filled)*

**Sections or grouping:** *(to be filled)*

**Actions / affordances:** *(to be filled)*

### Task row colours in this category

Uses global schedule rules unless noted otherwise.

### Notes

*(to be filled)*

---

## Goals

**Planned area:** [Planning and Long-Term Goals](planned-features.md#planning-and-long-term-goals)

**Prototype page:** [categories/goals.html](ui-prototype/categories/goals.html)

### Purpose

*(to be filled)*

### Category tile (grid)

**Sample subtitle:** `Review due`

| Colour | Meaning |
|--------|---------|
| Green | *(to be filled)* |
| Yellow | *(to be filled)* |
| Red | *(to be filled)* |

### Category panel (detail page)

**Layout:** *(to be filled)*

**Content types shown:** *(to be filled)*

**Sections or grouping:** *(to be filled)*

**Actions / affordances:** *(to be filled)*

### Task row colours in this category

Uses global schedule rules unless noted otherwise.

### Notes

*(to be filled)*

---

## Automation

**Planned area:** [Smart Reminders and Automation](planned-features.md#smart-reminders-and-automation)

**Prototype page:** [categories/automation.html](ui-prototype/categories/automation.html)

### Purpose

*(to be filled)*

### Category tile (grid)

**Sample subtitle:** `1 rule paused`

| Colour | Meaning |
|--------|---------|
| Green | *(to be filled)* |
| Yellow | *(to be filled)* |
| Red | *(to be filled)* |

### Category panel (detail page)

**Layout:** *(to be filled)*

**Content types shown:** *(to be filled)*

**Sections or grouping:** *(to be filled)*

**Actions / affordances:** *(to be filled)*

### Task row colours in this category

Uses global schedule rules unless noted otherwise.

### Notes

*(to be filled)*

---

## Prompt template (fill one category at a time)

Copy the block below into chat when you want to document or update a single category. Replace placeholders, fill the two sections, then send. The agent should **update both** [categories.md](categories.md) (this file) **and** the UI prototype HTML to match.

```markdown
Update the LifePilot category: **{CATEGORY}**

Apply my description to:
1. **doc/concept/categories.md** — fill or replace the matching category section (purpose, tile colours, panel layout, notes; mark the document status table as Documented).
2. **doc/concept/ui-prototype/categories/{slug}.html** — category detail page (header, toolbar, list/content structure, sample items).
3. **doc/concept/ui-prototype/categories.html** — grid tile for this category: border colour class (`square-link--ok` / `--warn` / `--alert`) and subtitle `<small>` text to reflect the colour rules below.

Reference (read only unless something is inconsistent):
- doc/concept/planned-features.md — planned capabilities for this life area
- doc/concept/ui-prototype/categories/shopping.html — shopping list reference
- doc/concept/ui-prototype/categories/pantry.html — pantry inventory reference
- doc/concept/ui-prototype.md — global task-row colour rules (schedule-based; do not change unless I say so)

---

## Category panel view

Describe how the detail page should look when the user taps this tile on the Categories grid. This drives the HTML prototype.

- **Header:** title, subtitle, counts, badges
- **Toolbar:** buttons and shortcuts (+ Add, back to Categories, filters, etc.)
- **Main content:** lists, cards, tabs, sections, empty states
- **Grouping:** sections, filters, sort order
- **Item types:** tasks, inventory rows, events, rules, habits, etc.
- **Sample content:** 4–8 example rows with realistic titles and meta lines
- **Actions:** add, complete, snooze, configure — anything unique to this life area

(Paste your panel description here)

---

## Category tile colours (grid only)

Define green / yellow / red for **this tile on the Categories grid** — not task-row due-date colours (those stay global).

| Colour | When the tile shows this |
|--------|--------------------------|
| Green | |
| Yellow | |
| Red | |

Also provide:
- **Example subtitle** under the tile label (e.g. `2 overdue`, `Stock OK`) — used in categories.html
- **Which colour** the prototype tile should show right now (green / yellow / red) for the sample data
- **Thresholds** (counts, time windows, percentages) and **edge cases** (empty, all done, paused rules, etc.)

(Paste your colour rules here)

---

Do not change other categories. Keep existing styles (styles.css); only edit HTML content and tile classes unless the layout truly needs new structure.
```

### Category name → slug

| Category | `{CATEGORY}` | `{slug}` |
|----------|--------------|----------|
| Shopping | Shopping | shopping |
| Pantry | Pantry | pantry |
| Chores | Chores | chores |
| Personal tasks | Tasks | personal |
| Health | Health | health |
| Hobbies | Hobbies | hobbies |
| Goals | Goals | goals |
| Automation | Automation | automation |
