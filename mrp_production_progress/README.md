# MRP Production Progress

## Overview
This module enhances Odoo's Manufacturing (MRP) functionality by adding comprehensive progress tracking for manufacturing orders, including component consumption, operation completion, and hierarchical aggregation across parent and child manufacturing orders.

**New in v16.0.1.1.0:** Manufacturing progress is now also displayed in Sales Orders!

## Features

### Manufacturing Order Progress Tracking

#### 1. Component Progress
- Tracks the consumption of raw materials
- Calculates: `(quantity_done / quantity_required) × 100`
- Automatically handles done, draft, and cancelled states

#### 2. Operation Progress
- Tracks the completion of work center operations
- Calculates: `(actual_duration / expected_duration) × 100`
- Real-time tracking as work orders are logged

#### 3. Overall Progress
- Smart combination of component and operation progress
- Uses intelligent averaging based on what exists:
  - Both: Average of component % and operation %
  - Only components: Component progress
  - Only operations: Operation progress

#### 4. Child MO Aggregation
- Recursively finds all descendant manufacturing orders
- Calculates weighted progress across entire MO hierarchy
- Handles multi-level nested MOs (parent → child → grandchild)

#### 5. Total Progress
- Aggregates metrics across parent MO and ALL child MOs
- Weighted sum approach for accurate totals
- Separate calculations for components, operations, and overall

### Sales Order Integration (NEW!)

#### Progress Display
The module now displays manufacturing order progress directly in sales orders:

**Fields Added:**
- `mo_component_progress`: Average component progress of all MOs
- `mo_operation_progress`: Average operation progress of all MOs
- `mo_overall_progress`: Average overall progress of all MOs
- `has_manufacturing_orders`: Boolean indicator

**Where to View:**

1. **In Sale Order Form:**
   - Progress section before the notebook tabs (quick view)
   - Dedicated "Manufacturing Progress" tab showing:
     - Average progress bars
     - List of all manufacturing orders with individual progress

2. **In Sale Order List:**
   - Optional "MO Progress %" column
   - Shows overall manufacturing progress at a glance

#### Calculation Logic
- Uses the **total progress** from each MO (including all child MOs)
- Averages progress across all non-cancelled manufacturing orders
- Automatically updates when:
  - Materials are consumed
  - Work orders are completed
  - Child MOs progress changes
  - MO states change

## User Interface

### Manufacturing Order Form
```
┌─────────────── Progress ───────────────┐
│ This MO              │ Total (incl. Child MOs) │
│ ├─ Component %       │ ├─ Total Component %     │
│ ├─ Operation %       │ ├─ Total Operation %     │
│ └─ Overall %         │ └─ Total Overall %       │
└────────────────────────────────────────┘

MO Progress Tab:
- Lists all child manufacturing orders
- Shows progress for each child
- Color-coded by state (green=done, gray=cancelled)
```

### Sales Order Form (NEW!)
```
┌─────── Manufacturing Progress ─────────┐
│ Average MO Progress (incl. All Child MOs) │
│ ├─ MO Component Progress %                │
│ ├─ MO Operation Progress %                │
│ └─ MO Overall Progress %                  │
└───────────────────────────────────────────┘

Manufacturing Progress Tab:
- Average progress bars
- List of all manufacturing orders
- Individual progress for each MO
- State badges (done, in progress, cancelled)
```

## Use Cases

### Sales Team
- **Track order fulfillment** in real-time
- **Provide accurate updates** to customers on production status
- **Identify delays** early in the manufacturing process
- **Monitor multiple MOs** per sale order from a single view

### Production Manager
- **Monitor overall manufacturing progress** at a glance
- **Identify bottlenecks** in component availability or operations
- **Track multi-level BoM** production hierarchies
- **See impact on sales commitments**

### Shop Floor Supervisor
- **Real-time component consumption** tracking
- **Track operation completion rates**
- **Prioritize work** based on progress and sales urgency

### Customer Service
- **Instant visibility** into order manufacturing status
- **Accurate delivery estimates** based on current progress
- **Proactive communication** with customers
- **Single view** of all MO progress for a sale order

## Technical Details

### Dependencies
- `mrp` - Manufacturing module
- `sale_mrp` - Sale MRP integration

### New Models Extended

#### sale.order
**Computed Fields:**
- `mo_component_progress`: Float (0-100)
- `mo_operation_progress`: Float (0-100)
- `mo_overall_progress`: Float (0-100)
- `has_manufacturing_orders`: Boolean

**Dependencies:**
```python
@api.depends('mrp_production_ids',
             'mrp_production_ids.total_component_progress',
             'mrp_production_ids.total_operation_progress',
             'mrp_production_ids.total_overall_progress',
             'mrp_production_ids.state')
```

#### mrp.production
**Existing Fields:**
- `component_progress`: Progress for current MO
- `operation_progress`: Progress for current MO
- `overall_progress`: Progress for current MO
- `total_component_progress`: Aggregated with child MOs
- `total_operation_progress`: Aggregated with child MOs
- `total_overall_progress`: Aggregated with child MOs
- `child_mo_ids`: All descendant MOs

## Installation

1. Ensure `mrp` and `sale_mrp` modules are installed
2. Install or upgrade `mrp_production_progress` module:
   ```bash
   ./odoo-bin -u mrp_production_progress -d your_database_name
   ```

## Configuration

No configuration required. The module works automatically once installed.

## Workflow Example

```
Sale Order SO001
├─ Total Manufacturing Progress: 51.5%
│
├─ Main Product MO (Parent) - MO001
│  ├─ Overall: 45%
│  ├─ Components: 60%
│  └─ Operations: 30%
│
├─ Sub-assembly 1 (Child) - MO002
│  ├─ Overall: 80%
│  ├─ Components: 90%
│  └─ Operations: 70%
│
└─ Sub-assembly 2 (Child) - MO003
   ├─ Overall: 20%
   ├─ Components: 30%
   └─ Operations: 10%

Average Progress displayed in Sale Order:
- MO Component Progress: 60%
- MO Operation Progress: 36.7%
- MO Overall Progress: 48.3%
```

## Benefits

✅ **Sales Order Visibility** - Track manufacturing progress from sales orders
✅ **Real-time Updates** - Automatic recalculation as production progresses
✅ **Hierarchical Tracking** - Includes all child manufacturing orders
✅ **Customer Communication** - Accurate status for customer inquiries
✅ **Multi-MO Support** - Handles multiple MOs per sale order
✅ **Smart Averaging** - Intelligent progress calculation across different MO types
✅ **Visual Indicators** - Progress bars and color-coded states
✅ **No Manual Entry** - Completely automated based on actual production data

## Version History

### v16.0.1.1.0 (Current)
- Added sales order integration
- Display manufacturing progress in sale orders
- Average progress calculation across multiple MOs
- New "Manufacturing Progress" tab in sale order form
- Optional progress column in sale order tree view

### v16.0.1.0.0
- Initial release
- Component and operation progress tracking
- Child MO aggregation
- Total progress calculation
- MO Progress tab in manufacturing order form

## Support

For issues or questions, contact Centrics Business Solutions:
- Website: http://www.centrics.cloud/
- Module: mrp_production_progress

## License

LGPL-3
