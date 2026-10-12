# Invoiceable Lines Extend (`baff_invoiceable_lines_extend`)

Odoo 16 · Branch `stagin2` · Version 16.0.1.2

This module changes how the **Invoiceable Lines** of a quotation and sales order are built from a Job Costing Sheet:

- what the **Add Invoiceable Lines** button does on the sheet, and
- what the sheet's **approval** writes to the quotation.

All of it is in this one module. **No existing module was modified.**

| Commit | Release | Change |
|---|---|---|
| `f9ba7c1` | staging_release_10122026_#3 | New module: new pricing logic for the button |
| `0deb8e7` | staging_release_10122026_#4 | Skip ticked rows without Raw Material and cost (fixes "Description is required" on JBC-00167) |
| `01045bc` | staging_release_10122026_#5 | Button hidden when the sheet is Done; works only after the Sales Order exists |
| `1383d69` | staging_release_10122026_#6 | Approval builds the same lines, so the quotation "Send For Approval" check passes |

---

## 1. Problem that was fixed

| # | Before (vendor `odoo_job_costing_management`) | After (this module) |
|---|---|---|
| 1 | The button billed bare cost. No Labour, no Overhead share, no Gross Profit markup, no Sale Commission | Each line is priced with the client formula (section 3) |
| 2 | Ticked **component** rows were never billed (dead `elif` branch) | Ticked rows of any type are billed |
| 3 | Nothing was written unless the sheet had Overhead lines | Overhead is optional |
| 4 | `(5, 0, 0)` wiped **every** invoiceable line of the quotation, manual ones included | Only removes lines this sheet created, plus untagged lines left by the old button |
| 5 | Zero prices, with no error, when the currency rate was missing | Clear error message |
| 6 | Approval (`update_sales_price`) wrote 1 line per finished good **plus** a Labor line and an Overhead line. Labour and Overhead were counted twice, so the quotation **Send For Approval** failed with *"Total Quotation Amount should be equal to Total Amount"* | Approval keeps updating the SO line prices, but its invoiceable lines are rebuilt with the new logic and always equal the SO total |
| 7 | The button was visible and usable in every state | Hidden when Done; works only between SO creation and Done |

---

## 2. Files

```
baff_invoiceable_lines_extend/
├── __manifest__.py              depends: odoo_job_costing_management, centrics_sales_separate_process
├── models/job_costing.py        all logic (inherits job.costing)
└── views/job_costing_views.xml  hides the button when the sheet is Done
```

### Methods on `job.costing`

| Method | Type | Purpose |
|---|---|---|
| `action_add_lines` | override, **no super()** | Button. Checks the state rules, then rebuilds the lines |
| `update_sales_price` | override, **calls super()** | Approval. The vendor code updates the SO line prices; we then replace its invoiceable lines |
| `can_add_invoiceable_lines` | computed Boolean (not stored) | True when `quotation_id.sale_id` is set and state is `ready_for_production` or `waiting_production_approval` |
| `_check_can_add_invoiceable_lines` | helper | Raises the state warnings (section 4) |
| `_get_invoiceable_components` | helper | Ticked rows plus every main parent row, in sheet order |
| `_get_component_owner` | helper | Finds which billed row a cost line belongs to |
| `_compute_invoiceable_costs` | helper | Material (A) and Labour (B) per billed row |
| `_get_invoiceable_line_name` | helper | Component path for parent/BOM rows, Raw Material name otherwise |
| `_get_invoiceable_target_total` | helper | SO total the approval gives (Total Price split by finished-good qty, unit price rounded like the SO line) |
| `_prepare_invoiceable_line_values` | helper | Pricing, scaling to the target and rounding |
| `_get_replaced_invoiceable_lines` | helper | Lines to delete before writing the new ones |
| `_update_invoiceable_lines` | helper | One `write()` on the quotation with delete + create commands |

---

## 3. Calculation logic (client sheet "Invoiceable line calculation.xlsx")

### 3.1 Which rows become invoiceable lines

1. Every Materials row ticked **Is Included In Report** (normally the child BOMs).
2. Every **main parent** row (`material_type = 'parent'`). It carries the cost of all its rows that are **not** ticked.
   - If nothing is ticked, each parent is billed with its full cost.
   - A parent that isn't ticked and has no cost left is dropped.
3. A row with no Raw Material and no Component path:
   - with no cost → skipped;
   - with a cost → error (section 4).

### 3.2 How cost lines are assigned (A = Material, B = Labour)

- **Leaf materials** are rows with `material_type = 'component'`. These are the same rows the sheet's Total Material Cost counts.
- **Labour** is every line in the Workcenters & Labours tab that has a Component path.
- Each cost line goes to the **deepest billed row above it**, matched by:
  - `component` path: equal, or starting with `<row path>/`;
  - `material_index` / `labour_index` prefix as a tie-breaker. If the rows were renumbered and no index matches, the path alone decides.

  This means a line is never counted twice. It also means "PULSE C60 – Hull" does **not** pick up the rows of "PULSE C60 – Hull, deck and GRP assembly".

> The vendor's **Sub Total** column on header rows (`rollup_cost`) matches by plain substring, so it can show more than our line uses. On JBC-00169 the Hull row shows 2,934,209.50 but really holds 2,069,602.05. That is a display issue in the vendor module and doesn't affect the invoiceable lines.

### 3.3 Price of each line

```
A = Material cost of the row (sheet currency)
B = Labour cost of the row
C = Overhead total (Overhead tab) / Σ A of all billed rows × A      ← overhead split by MATERIAL only
D = A + B + C
E = D × Gross Profit % Markup / 100
F = (D + E) × p / (100 − p)        p = "Sale Commission, After Sales Service and Design Royalties" %
G = D + E + F
G is converted with the sheet Currency Rate when the customer currency differs (G / rate)
```

This is the same formula as the sheet's own Total Price, so when every cost is billed, Σ G = **Total Price**.

### 3.4 Bringing the lines to the Sales Order total

The quotation check compares invoiceable lines with the order lines, so the lines are adjusted to the **SO total**:

- **Target:**
  - with finished goods: Total Price split by finished-good qty, unit price rounded to *Product Price* precision (3 decimals), × qty. This is exactly what approval puts on the SO lines.
  - without finished goods: Σ G, rounded.
- Every line is scaled by `target / Σ G`. Any cost that the billed rows didn't reach is spread proportionally. Examples: labour with no matching parent row; a parent duplicated with the same name.
- `price_unit = amount / qty`, rounded to 3 decimals. The final rounding difference goes to the **last line with qty 1** (or the last line).

### 3.5 Values written per line

| Field | Value |
|---|---|
| `product_id`, `product_uom`, `product_uom_qty` | from the sheet row (qty 0 → 1) |
| `price_unit` | see 3.4 |
| `name` | Component path (parent/BOM) or Raw Material display name |
| `category` | `'product'` |
| `job_costing_id` | the sheet |
| `order_id` | the quotation (through the One2many) |
| `so_order_id` | `quotation_id.sale_id` (so the line also shows on the SO) |
| `tax_id` | not set |

### 3.6 Lines that are replaced

- Lines with `job_costing_id = this sheet`. This includes the vendor approval's product, Labor and Overhead lines.
- Untagged legacy lines from the old button: no `job_costing_id`, no `category`, not a section or note, product used on the sheet, and description equal to a sheet path or product name.

Manual lines, sections and notes are kept.

---

## 4. When it runs and the messages

### 4.1 Sheet flow

| Step | Sheet state | Invoiceable lines |
|---|---|---|
| Draft → Review → Approval | → `approved` | **Approval writes them** (new logic) and updates the SO line prices |
| Quotation Confirm (needs `approved`) → SO created automatically | → `ready_for_production` | Button **works** |
| Send For Production Approval | `waiting_production_approval` | Button **works** |
| Production Approve | → `done` | Button **hidden** |

The lines live on the quotation (`order_id`) and on the SO (`so_order_id`) as **the same records**, so a rebuild updates both.

### 4.2 Messages

| Situation | Message |
|---|---|
| Sheet Done (if called from code) | Job Costing Sheet … is Done: its invoiceable lines can no longer be changed. |
| No Sales Order yet | Create the Sales Order of Job Costing Sheet … before adding invoiceable lines. |
| SO exists but state Canceled / Revised / other | Invoiceable lines of Job Costing Sheet … cannot be added in state … |
| No quotation | Link a Quotation to Job Costing Sheet … before adding invoiceable lines. |
| Nothing to bill | Job Costing Sheet … has no Materials line to invoice. / … has no cost to invoice. |
| Ticked row with cost but no Raw Material | Set a Raw Material on line(s) … of Job Costing Sheet …, or untick 'Is Included In Report'. |
| Overhead but billed rows have no material | The Overhead of Job Costing Sheet … cannot be allocated … |
| Sale Commission ≥ 100 | … must be below 100%. |
| Foreign customer currency, rate 0 | Set the Currency Rate of Job Costing Sheet … to convert its prices to … |

> The messages raised from the approval (`update_sales_price`) stop the approval itself. This is intended: for example, it blocks approval when the rate is missing.

---

## 5. Install / upgrade

1. Pull branch `stagin2` (commit `1383d69` or later).
2. **Apps → Update Apps List** (first time only).
3. **Apps → Invoiceable Lines Extend → Install / Upgrade**.
4. Upgrade only this module. **Do not run `-u all`** on a database built from newer code: on a test copy it deleted fields and views (for example the `baff_reports` VAT Type) that are missing in this branch.

---

## 6. Test checklist

| # | Steps | Expected |
|---|---|---|
| 1 | Sheet with Overhead and/or Labour → approve it | Quotation invoiceable lines = one per ticked child BOM, plus parent line(s). **No** "Labor —" / "Overhead —" lines |
| 2 | After #1, quotation **Send For Approval** | No "Total Quotation Amount should be equal to Total Amount" error. Invoiceable total = order total |
| 3 | Confirm quotation (SO created) → sheet Ready for Production → press button | Same total; lines visible on the quotation **and** the SO |
| 4 | Same in Waiting Production Approval | Works |
| 5 | Sheet Done | Button hidden |
| 6 | Press the button on a Draft / Reviewed / Approved sheet | Warning "Create the Sales Order …" |
| 7 | Cancelled or Revised sheet with SO | Warning "… cannot be added in state …" |
| 8 | Tick a row with no Raw Material and 0 cost (e.g. JBC-00167 index 00196) | Row skipped, no error |
| 9 | Same row with a cost | Warning "Set a Raw Material on line(s) …"; nothing written |
| 10 | Add a manual line and a section on the quotation, then rebuild | Both kept |
| 11 | Press twice | Lines replaced, never duplicated |
| 12 | Foreign currency with rate 0 | Rate warning |

### Reference case (verified on staging #5): JBC-00169 → S00045

Sheet: Material 12,340,615.04 · Labour 0 · Overhead 110,000 · Markup 20 % · Commission 15 % · Total Price 17,577,338.88 LKR · rate 250 → **70,309.356 AUD**.
Ticked: Hull, DECK, Console.

| Line | Material (LKR) | AUD |
|---|---|---|
| PULSE C60 (parent, all unticked rows) | 8,423,639.46 | 47,992.800 |
| PULSE C60 – Hull | 2,069,602.05 | 11,791.340 |
| PULSE C60 – DECK | 1,521,232.24 | 8,667.060 |
| PULSE C60 – Console | 326,141.29 | 1,858.155 |
| **Total** | 12,340,615.04 | **70,309.355** = order total |

Each row: material × (1 + 110,000 / 12,340,615.04) × 1.20 / 0.85 / 250.

### Local regression (copy of baff_test, rolled back)

- Approval simulated on all 9 sheets with finished goods: **9 / 9** equal to the order total (JBC-00153, 154, 156, 157, 162, 163, 167, 168, 169).
- JBC-00163 (labour + overhead) before the fix: order 28,959.84 vs invoiceable 37,753.36 → FAIL. After: 28,959.84 = 28,959.84 → PASS.

---

## 7. Known limitations / open points

1. **No user-group restriction** on the button. Anyone who can open the sheet and write the quotation can rebuild the lines.
2. **Not blocked after the SO is invoiced** (only blocked when the sheet is Done). Invoices keep their own copies of the lines.
3. **Taxes** are not set on the lines. The quotation check compares untaxed invoiceable lines with the **taxed** order total, so a taxed order line would still fail that check (vendor check in `centrics_sale_multi_user_approval/models/sale_order.py:164-168`).
4. **Record rule** `job_cost_line_production_rule`: users of *Job Costing Production* don't see every cost line, so if they rebuild the lines, the split between lines uses partial data (the total is still brought to the SO total).
5. **Rows with no Type and no Component** (added by hand, e.g. many on JBC-00167) are not part of the sheet Total Price. If ticked, they're billed at their own cost and then scaled into the SO total.
6. Quotations that already have the old approval lines (e.g. QO0077) are only corrected when the sheet is approved again, or with the button once the SO exists.
7. The vendor's header **Sub Total** display can overstate a row whose name is a prefix of another row's name (see 3.2).
