# UI Prototype

Static, mobile-first HTML/CSS mockups for core LifePilot screens. They are concept-only (no backend); links between pages work in any browser.

## Folder layout

```
ui-prototype/
  index.html          # Hub — links to all screens
  tasks.html          # Today’s tasks (+ New task, Focus today list)
  categories.html     # Category grid (2×4)
  calendar.html       # Month view with tasks on days
  add-task.html
  add-shopping-item.html   # Shopping list only (no schedule)
  add-pantry-item.html     # Pantry inventory only (no schedule)
  styles.css
  prototype.js
  categories/         # One panel per life area
    shopping.html        # Shopping list (reference)
    pantry.html          # Pantry inventory with +/−
    chores.html
    personal.html
    health.html
    hobbies.html
    goals.html
    automation.html
```

## Screens

| Screen | File | Description |
|--------|------|-------------|
| Hub | [ui-prototype/index.html](ui-prototype/index.html) | Links to all prototype pages |
| Tasks | [ui-prototype/tasks.html](ui-prototype/tasks.html) | **+ New task** + scrollable **Focus today** list (sample of 15 items) |
| Categories | [ui-prototype/categories.html](ui-prototype/categories.html) | 2×4 grid of life areas with status borders |
| Category panels | [ui-prototype/categories/shopping.html](ui-prototype/categories/shopping.html), [pantry.html](ui-prototype/categories/pantry.html) (examples) | One panel per life area; see `categories/` |
| Calendar | [ui-prototype/calendar.html](ui-prototype/calendar.html) | Month grid with task markers; selected day task list |
| Add task | [ui-prototype/add-task.html](ui-prototype/add-task.html) | New task form (category, schedule; no priority) |
| Add shopping item | [ui-prototype/add-shopping-item.html](ui-prototype/add-shopping-item.html) | Shopping buy list only — type, quantity; no date/time |
| Add pantry item | [ui-prototype/add-pantry-item.html](ui-prototype/add-pantry-item.html) | Pantry inventory — required & at-home qty; no date/time |

## Navigation

Bottom bar on every screen (three shortcuts):

1. **Tasks** — today’s list and focus items
2. **Categories** — area status grid
3. **Calendar** — month view with scheduled tasks

**Add task** is reached from the **+ New task** button on Tasks and from most category pages (not a fourth tab). **Shopping** and **Pantry** use dedicated add forms ([add-shopping-item.html](ui-prototype/add-shopping-item.html), [add-pantry-item.html](ui-prototype/add-pantry-item.html)) with no schedule fields.

## Calendar view

The **Calendar** tab (`calendar.html`) shows a month grid (weeks **Mon–Sun**, short weekday labels). Days with tasks use colored dots or a count; **today** (24 May in the sample) is highlighted, with that day’s tasks listed below the grid.

## Categories grid

Eight blocks on the grid: **Shopping**, **Pantry**, **Chores**, **Tasks**, **Health**, **Hobbies**, **Goals**, and **Automation**. **Calendar** is not on the grid — use the bottom-nav **Calendar** tab ([calendar.html](ui-prototype/calendar.html)) for the month view.

Each tile links to a page under `categories/`. **Shopping** (`shopping.html`) is the task-list reference; **Pantry** (`pantry.html`) is the inventory reference with **−1** / **+1** quantity controls.

## Status colors (green, yellow, red)

The prototype uses the same three border colours in two places, but **the rules differ**. Category tiles summarise area health; task rows reflect schedule urgency.

### Categories (grid tiles)

Meaning **depends on the life area** — each category defines its own thresholds (Chores, Health, Goals, etc.), not the task due-date logic below. See [categories.md](categories.md) for per-category tile colours and panel layout.

### Tasks (list rows)

Task rows use an **MS To Do–style card**: title on the first line, category · date · details on the second (dot-separated), and a rounded-square check control that fills with a checkmark when done.

Same colours on **Tasks**, **Focus today**, category task lists, and the calendar day panel. Rules are **schedule-based** (date and optional time):

| Color | Meaning |
|-------|---------|
| Red | **Overdue** — due date is in the past, or due **today** but the scheduled time has already passed (e.g. due 10:00, now 13:00) |
| Yellow | Due **today**, and the scheduled time is **within 2 hours or less** (approaching or at risk of becoming overdue) |
| Green | **Regular** — not overdue and not in the 2-hour urgent window (includes tasks with no time set that are not past their date) |

## How to view

Open `doc/concept/ui-prototype/index.html` in a browser (double-click or **Simple Browser: Show** in VS Code/Cursor). Most screens fill the window without page scroll; **Tasks → Focus today** scrolls inside its section. Layout and typography scale with viewport size (`vmin` / `dvh`).

Shared styles: [ui-prototype/styles.css](ui-prototype/styles.css).
