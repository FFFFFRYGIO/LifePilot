# Data (sample and reference)

Reference data for LifePilot, stored as CSV tables. Currently covers **shopping item categories** and the **shopping list**.

> **Scope note:** the *categories* described here are **product categories** for the shopping list (Household, Hygiene, …). They are **not** the same thing as the life-area category tiles on the [Categories grid](../concept/categories.md) (Shopping, Pantry, Chores, …).

## Files

| File | Description |
| --- | --- |
| [categories.csv](categories.csv) | Product categories used to group shopping items. |
| [shopping_items.csv](shopping_items.csv) | Shopping list items, each linked to a category. |

## Categories

Categories group shopping items (for example *Household* or *Beverages*). Every category has a stable numeric **id** and a name in **both Polish and English**, so the app can be presented in either language.

The category set is **not fixed**. The service must let the user **manage categories** — **add** a new category, **edit** an existing one (rename in either language), and **delete** one that is no longer needed. When a category is deleted, its items must be reassigned or handled so no item is left pointing at a missing category.

### Schema — `categories.csv`

| Column | Type | Description |
| --- | --- | --- |
| `Id` | integer | Stable unique identifier, referenced by shopping items. |
| `Name (PL)` | text | Polish display name. |
| `Name (EN)` | text | English display name. |

### Current categories

| Id | Name (PL) | Name (EN) |
| --- | --- | --- |
| 1 | Chemia domowa | Household |
| 2 | Higiena | Hygiene |
| 3 | Suplementy | Supplements |
| 4 | Żywność wygodna | Convenience food |
| 5 | Żywność | Food |
| 6 | Napoje | Beverages |
| 7 | Alkohol | Alcohol |
| 8 | Leki | Medicines |

## Shopping items

Each shopping item has a name in **both Polish and English** and **must be assigned to exactly one category** via `CategoryId`. Like categories, items are user-managed: they can be **added**, **edited**, and **removed**. Adding an item always requires picking one of the existing categories.

### Schema — `shopping_items.csv`

| Column | Type | Description |
| --- | --- | --- |
| `CategoryId` | integer | Foreign key to `categories.csv` → `Id`. Every item must reference a valid category. |
| `Item` | text | English item name. Keep it generic — put brands and specifics in the description. |
| `Item (PL)` | text | Polish item name. |
| `Description` | text | Short English note (a few words): brand, variant, or specifics. May be empty. |
| `Description (PL)` | text | Polish version of the note. May be empty. |
| `Required Quantity` | integer | How many units are needed. |

Proper names that are identical in both languages (for example *Omega 3*, *Cola Zero*) simply repeat the same value in both name columns.

The **item name stays generic**; brand and variant details go in the **description** so the list reads cleanly. For example the item is *Carbonated lemonade* with description *Sprite Zero or 7 Up Zero*, or *Mouthwash* with description *Listerine Total Care*. Descriptions focus on the specific brand/product to buy.
