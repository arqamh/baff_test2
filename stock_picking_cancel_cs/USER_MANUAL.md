# Stock Picking Cancel - User Manual

## Module Overview

**Module Name:** Cancel Stock Picking (Delivery Order) & Reset to Draft
**Version:** 16.0.1.0.0
**Author:** Craftsync Technologies

This module allows authorized users to cancel done/validated delivery orders and reset cancelled delivery orders back to draft state. This is particularly useful when you need to correct mistakes or reverse completed delivery operations.

---

## Key Features

1. **Cancel Done Delivery Orders** - Cancel delivery orders that are already in "Done" state
2. **Reset to Draft** - Reset cancelled delivery orders back to draft state for reprocessing
3. **Multiple Cancellation Options** - Cancel deliveries from:
   - Stock Picking form
   - Sale Order form
   - Purchase Order form
4. **Inventory Reversal** - Automatically reverses inventory movements when canceling
5. **Accounting Integration** - Reverses accounting entries created by the delivery
6. **Permission-Based Access** - Only authorized users can cancel done deliveries

---

## Installation

1. Copy the `stock_picking_cancel_cs` module to your Odoo addons directory
2. Update the Apps list in Odoo
3. Search for "Cancel Stock Picking" in Apps
4. Click **Install**

---

## Configuration

### Step 1: Enable the Feature

1. Go to **Settings → Inventory**
2. Scroll to the **Cancel Delivery Order** section
3. Check the **Cancel Done Delivery** checkbox
4. Click **Save**

### Step 2: Assign Permissions

1. Go to **Settings → Users & Companies → Users**
2. Select the user who needs cancellation rights
3. In the **Access Rights** tab, enable:
   - **Cancel Delivery Order** permission
4. Save the user settings

---

## How to Use

### Option 1: Cancel from Stock Picking (Delivery Order)

**When to use:** When you're viewing the delivery order directly

**Steps:**
1. Go to **Inventory → Operations → Transfers**
2. Open a delivery order in **Done** state
3. Click the **Cancel** button in the header
4. The delivery order will be cancelled and inventory will be reversed

**To Reset to Draft:**
1. Open a cancelled delivery order
2. Click the **Reset to Draft** button
3. The delivery order returns to draft state
4. Make necessary corrections
5. Validate again when ready

---

### Option 2: Cancel from Sale Order

**When to use:** When managing deliveries through sales orders

**Steps:**
1. Go to **Sales → Orders → Orders**
2. Open a sale order that has delivered products
3. Click the **Cancel Delivery** button in the header
4. **If ONE delivery:** The delivery is immediately cancelled
5. **If MULTIPLE deliveries:** A wizard appears:
   - Select the delivery orders you want to cancel
   - Click **Cancel Delivery Orders**
   - Click **Clear All** to deselect all deliveries

---

### Option 3: Cancel from Purchase Order

**When to use:** When managing receipts through purchase orders

**Steps:**
1. Go to **Purchase → Orders → Purchase Orders**
2. Open a purchase order that has received products
3. Click the **Cancel Delivery** button in the header
4. **If ONE receipt:** The receipt is immediately cancelled
5. **If MULTIPLE receipts:** A wizard appears:
   - Select the receipts you want to cancel
   - Click **Cancel Delivery Orders**
   - Click **Clear All** to deselect all receipts

---

## What Happens When You Cancel?

### Inventory Changes
- Product quantities are returned to their original locations
- Stock moves are reversed
- Inventory valuation is adjusted

### Accounting Changes
- Journal entries created by the delivery are reversed
- Stock valuation entries are removed
- Account reconciliations are undone

### Document Status
- Delivery order status changes to **Cancelled**
- Original sale/purchase order remains unchanged
- You can reset to draft to recreate the delivery

---

## Important Restrictions

### Cannot Cancel When:
1. **Landed Costs Applied** - If the delivery has landed costs, you must remove them first
2. **Insufficient Permissions** - User must have "Cancel Delivery Order" permission
3. **Already Cancelled** - Cannot cancel an already cancelled delivery

### Warning Messages:
- If landed costs exist: *"This Delivery is set in landed cost record [name] you need to delete it first then you can cancel this Delivery"*

---

## Permissions & Security

### Security Group
**Group Name:** Cancel Delivery Order
**Technical Name:** `stock_picking_cancel_cs.group_cancel_delivery_order`

### Who Should Have Access?
- Inventory Managers
- Warehouse Supervisors
- Operations Managers

### Who Should NOT Have Access?
- Regular warehouse users
- Sales representatives
- General staff members

---

## Practical Use Cases

### Use Case 1: Wrong Product Delivered
**Scenario:** Customer received wrong product
**Solution:**
1. Cancel the done delivery order
2. Product returns to stock
3. Reset to draft if needed
4. Pick correct product
5. Validate new delivery

### Use Case 2: Delivery to Wrong Location
**Scenario:** Products delivered to wrong customer
**Solution:**
1. Cancel the delivery from sale order
2. Products return to warehouse
3. Create new delivery for correct customer
4. Validate correct delivery

### Use Case 3: Incorrect Quantity
**Scenario:** Wrong quantity was delivered
**Solution:**
1. Cancel the done delivery
2. Reset to draft
3. Adjust quantities
4. Re-validate with correct quantities

### Use Case 4: Accounting Period Closed
**Scenario:** Need to correct delivery but period is closed
**Note:** Consult with accounting team before canceling deliveries in closed periods

---

## Troubleshooting

### Problem: Cancel button not visible
**Solution:**
- Check if user has "Cancel Delivery Order" permission
- Verify module is installed and configured
- Ensure "Cancel Done Delivery" setting is enabled

### Problem: Cannot cancel - Landed cost error
**Solution:**
- Go to **Inventory → Operations → Landed Costs**
- Find and delete the landed cost record
- Then cancel the delivery

### Problem: Reset to Draft button not appearing
**Solution:**
- Button only appears on cancelled deliveries
- Ensure delivery status is "Cancelled"

### Problem: Inventory not reversed correctly
**Solution:**
- Check product type (only storable products have inventory)
- Verify stock moves were in "Done" state
- Check for any custom inventory rules

---

## Technical Information

### Models Modified
- `stock.picking` - Delivery orders
- `sale.order` - Sales orders
- `purchase.order` - Purchase orders
- `res.config.settings` - Configuration settings
- `res.company` - Company settings

### Key Methods
- `action_cancel()` - Cancels delivery and reverses inventory
- `action_draft()` - Resets cancelled delivery to draft
- `check_cancel_done_picking()` - Checks user permissions
- `cancel_picking()` - Cancels deliveries from sale/purchase orders

---

## Support & Contact

**Developer:** Craftsync Technologies
**Email:** info@craftsync.com
**Website:** https://www.craftsync.com/

For technical support or customization requests, please contact the development team.

---

## Version History

**Version 16.0.1.0.0**
- Initial release for Odoo 16
- Cancel done delivery orders
- Reset cancelled orders to draft
- Support for sale and purchase orders
- Multi-delivery cancellation wizard
- Permission-based access control

---

*This manual is current as of the module version listed above. Features and functionality may vary in different versions.*
