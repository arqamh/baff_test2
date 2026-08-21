# Product Category Change Restriction

[![Version](https://img.shields.io/badge/version-16.0.1.0.0-blue.svg)](http://www.centrics.cloud/)
[![License](https://img.shields.io/badge/license-OPL--1-lightgrey.svg)](https://www.odoo.com/documentation/user/16.0/legal/licenses/licenses.html#odoo-apps)

## Overview

This module allows administrators to control who can change product categories in Odoo. When enabled, only users with the "Change Product Category" permission can modify the product category field on product forms.

**Key Features:**
- Company-specific configuration
- Toggle restriction on/off from Inventory settings
- Dedicated security group for authorized users
- UI-level field protection (readonly)
- API-level validation (prevents programmatic changes)
- Multi-company support

---

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Usage](#usage)
4. [Technical Details](#technical-details)
5. [Use Cases](#use-cases)
6. [Testing](#testing)
7. [FAQ](#faq)
8. [Troubleshooting](#troubleshooting)

---

## Installation

1. Copy the module to your Odoo addons directory
2. Update the apps list: Settings → Apps → Update Apps List
3. Search for "Product Category Change Restriction"
4. Click **Install**

**Dependencies:**
- `stock` (Inventory/Stock Management)
- `product` (Product Management)

---

## Configuration

### Step 1: Enable the Restriction

1. Go to **Settings → Inventory**
2. Scroll down to the **Products** section
3. Find the **Restrict Product Category Change** checkbox
4. Check the box to enable the restriction
5. Click **Save**

![Configuration Setting](static/description/config_screenshot.png)

> **Note:** This is a company-specific setting. Each company can have its own configuration in multi-company environments.

### Step 2: Assign Permissions

1. Go to **Settings → Users & Companies → Users**
2. Select the user who needs permission to change product categories
3. Click **Edit**
4. In the user form, scroll to the **Access Rights** section
5. Find and enable the **Change Product Category** permission
6. Click **Save**

**Recommended Users:**
- Product Managers
- Inventory Managers
- Master Data Administrators
- Category Management Team

---

## Usage

### When Restriction is ENABLED

#### For Regular Users (without permission):
- The **Product Category** field appears **read-only** on product forms
- Users cannot select or change the category via the UI
- Attempting to change via API/code triggers an error:
  ```
  You do not have permission to change product category.
  Please contact your administrator.
  ```

#### For Authorized Users (with permission):
- The **Product Category** field remains **fully editable**
- Users can freely change product categories
- No restrictions apply

### When Restriction is DISABLED

- **All users** can change the product category
- No restrictions apply regardless of user permissions
- Standard Odoo behavior

---

## Technical Details

### Module Structure

```
centrics_product_category_restriction/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── res_company.py          # Company configuration field
│   ├── res_config_settings.py  # Settings UI field
│   └── product_template.py     # Permission logic
├── views/
│   ├── res_config_settings_views.xml  # Settings view
│   └── product_template_views.xml     # Product form view
├── security/
│   └── security.xml            # Security group definition
└── static/
    └── description/
        └── icon.png
```

### Models

#### 1. res.company (res_company.py)

Adds company-specific configuration field:

```python
restrict_product_category_change = fields.Boolean(
    string='Restrict Product Category Change',
    help='Only authorized users can change product category'
)
```

#### 2. res.config.settings (res_config_settings.py)

Uses Odoo's standard `related` field pattern for configuration:

```python
restrict_product_category_change = fields.Boolean(
    related='company_id.restrict_product_category_change',
    readonly=False,
    string='Restrict Product Category Change',
    help='Only authorized users can change product category'
)
```

**Why this pattern?**
- Follows Odoo best practices
- Automatically handles get/set values
- No manual `get_values()` or `set_values()` needed
- Cleaner code

#### 3. product.template (product_template.py)

Implements permission logic with two mechanisms:

**A. Computed Field for UI Protection**

```python
can_change_category = fields.Boolean(
    string='Can Change Category',
    compute='_compute_can_change_category'
)

@api.depends_context('uid', 'company')
def _compute_can_change_category(self):
    """Compute if user can change product category based on company settings."""
    company = self.env.company
    for product in self:
        # If restriction is disabled, everyone can change
        if not company.restrict_product_category_change:
            product.can_change_category = True
        # If restriction is enabled, only users with the group can change
        elif self.user_has_groups(
            'centrics_product_category_restriction.group_change_product_category'
        ):
            product.can_change_category = True
        else:
            product.can_change_category = False
```

**Key Points:**
- Checks if restriction is enabled first
- If disabled, all users get edit access
- If enabled, only authorized users get access
- Depends on both user (`uid`) and company context

**B. Write Method Validation**

```python
def write(self, vals):
    """Override write to check permission for category change."""
    if 'categ_id' in vals:
        company = self.env.user.company_id
        if company.restrict_product_category_change:
            if not self.user_has_groups(
                'centrics_product_category_restriction.group_change_product_category'
            ):
                raise UserError(
                    'You do not have permission to change product '
                    'category. Please contact your administrator.'
                )
    return super(ProductTemplate, self).write(vals)
```

**Purpose:**
- Prevents programmatic changes via XML-RPC, API, or direct ORM calls
- Server-side validation (cannot be bypassed)
- Only runs when restriction is enabled

### Views

#### 1. Settings View (res_config_settings_views.xml)

Uses standard Odoo setting box structure:

```xml
<xpath expr="//div[@id='manage_product_packaging']" position="after">
    <div class="col-12 col-lg-6 o_setting_box" id="restrict_product_category_change_setting">
        <div class="o_setting_left_pane">
            <field name="restrict_product_category_change"/>
        </div>
        <div class="o_setting_right_pane">
            <label for="restrict_product_category_change"/>
            <span class="fa fa-lg fa-building-o"
                  title="Values set here are company-specific."
                  groups="base.group_multi_company"/>
            <div class="text-muted">
                Only authorized users can change product category
            </div>
        </div>
    </div>
</xpath>
```

**Benefits:**
- Consistent with Odoo UI/UX
- Responsive layout (Bootstrap grid)
- Shows company-specific indicator
- Properly placed in Products section

#### 2. Product Form View (product_template_views.xml)

Makes category field conditional:

```xml
<field name="categ_id" position="before">
    <field name="can_change_category" invisible="1"/>
</field>
<field name="categ_id" position="attributes">
    <attribute name="attrs">{'readonly': [('can_change_category', '=', False)]}</attribute>
</field>
```

### Security

#### Security Group (security/security.xml)

```xml
<record id="group_change_product_category" model="res.groups">
    <field name="name">Change Product Category</field>
</record>
```

**Technical Name:** `centrics_product_category_restriction.group_change_product_category`

---

## Use Cases

### Use Case 1: Prevent Accidental Category Changes

**Problem:** Users accidentally change product categories during data entry, causing reporting issues and inventory misclassification.

**Solution:**
1. Enable "Restrict Product Category Change"
2. Only assign permission to product managers
3. Regular users can still create products but cannot recategorize them

**Result:** Reduced data errors and improved category consistency.

### Use Case 2: Category Standardization

**Problem:** Different departments categorizing products differently, leading to inconsistent reporting.

**Solution:**
1. Enable restriction across all companies
2. Create a dedicated "Category Management" team
3. All category changes go through this team

**Result:** Standardized product categorization company-wide.

### Use Case 3: Audit and Compliance

**Problem:** Need to track and control who can reclassify products for audit purposes.

**Solution:**
1. Enable restriction
2. Assign permission to specific roles
3. Use Odoo's chatter/log to track changes

**Result:** Clear audit trail of category changes by authorized personnel only.

### Use Case 4: Multi-Company Operations

**Problem:** Subsidiary companies need different category management rules.

**Solution:**
1. Company A: Enable restriction (strict control)
2. Company B: Disable restriction (flexible management)
3. Each company operates independently

**Result:** Flexible per-company configuration.

---

## Testing

### Manual Testing Checklist

#### Test 1: Configuration Toggle
- [ ] Navigate to Settings → Inventory
- [ ] Find "Restrict Product Category Change" in Products section
- [ ] Toggle ON → Save → Verify setting persists
- [ ] Toggle OFF → Save → Verify setting persists

#### Test 2: Permission Assignment
- [ ] Go to Settings → Users & Companies → Users
- [ ] Select test user
- [ ] Enable "Change Product Category" permission
- [ ] Save and verify permission is saved

#### Test 3: Restriction Enabled - Authorized User
- [ ] Enable restriction in settings
- [ ] Assign permission to test user
- [ ] Log in as test user
- [ ] Open any product
- [ ] Verify category field is EDITABLE
- [ ] Change category and save
- [ ] Verify change is saved successfully

#### Test 4: Restriction Enabled - Unauthorized User
- [ ] Keep restriction enabled
- [ ] Create user WITHOUT permission
- [ ] Log in as that user
- [ ] Open any product
- [ ] Verify category field is READ-ONLY
- [ ] Field should appear grayed out/disabled

#### Test 5: Restriction Disabled
- [ ] Disable restriction in settings
- [ ] Log in as any user (with or without permission)
- [ ] Open any product
- [ ] Verify category field is EDITABLE for all users

#### Test 6: API Validation
- [ ] Enable restriction
- [ ] Use XML-RPC or Python code to change category
- [ ] Without permission: Should raise UserError
- [ ] With permission: Should succeed

### Automated Testing

```python
# Test case example
def test_category_restriction_enabled(self):
    """Test category restriction when enabled"""
    self.env.user.company_id.restrict_product_category_change = True

    # User without permission should get error
    with self.assertRaises(UserError):
        self.product.categ_id = self.other_category

    # User with permission should succeed
    self.env.user.groups_id += self.env.ref(
        'centrics_product_category_restriction.group_change_product_category'
    )
    self.product.categ_id = self.other_category
    self.assertEqual(self.product.categ_id, self.other_category)

def test_category_restriction_disabled(self):
    """Test category restriction when disabled"""
    self.env.user.company_id.restrict_product_category_change = False

    # All users should be able to change
    self.product.categ_id = self.other_category
    self.assertEqual(self.product.categ_id, self.other_category)
```

---

## FAQ

**Q: Does this affect product variants?**
A: Yes, the restriction applies to both product templates and their variants since product.product inherits from product.template.

**Q: Can users still create new products with a category?**
A: Yes, users can create products with an initial category. The restriction only applies when CHANGING an existing product's category.

**Q: What happens to existing products when I enable this?**
A: Nothing changes to existing data. The restriction only applies to future attempts to change categories.

**Q: Can users with Stock Manager access change categories automatically?**
A: No. The "Change Product Category" permission is independent. You must explicitly assign it even to Stock Managers.

**Q: Is this setting per-company?**
A: Yes, each company in a multi-company environment can have its own restriction setting.

**Q: Does this work with product imports?**
A: Yes. If a user without permission tries to import products with changed categories while restriction is enabled, the import will fail for those records.

**Q: Can I disable the restriction temporarily?**
A: Yes, simply uncheck the setting in Inventory configuration. Changes take effect immediately.

**Q: What if I need to bulk change categories?**
A: Either:
1. Temporarily disable the restriction, or
2. Temporarily assign permission to the user performing bulk changes

**Q: Does this affect the product category tree/hierarchy?**
A: No. This only restricts changing which category a product belongs to. Managing the category tree itself (product.category model) is not affected.

---

## Troubleshooting

### Problem: Category field not read-only despite restriction enabled

**Possible Causes:**
- User has the "Change Product Category" permission
- Restriction is disabled for the current company
- Browser cache issue

**Solutions:**
1. Verify the user does NOT have "Change Product Category" in Access Rights
2. Check Settings → Inventory → confirm restriction checkbox is enabled
3. Hard refresh the browser (Ctrl+Shift+R or Cmd+Shift+R)
4. Clear browser cache and reload
5. Check if you're logged into the correct company

### Problem: Getting permission error when I should have access

**Possible Causes:**
- User doesn't actually have the permission assigned
- User is accessing from a different company
- Cache/session issue

**Solutions:**
1. Go to user record → Access Rights tab
2. Verify "Change Product Category" checkbox is enabled
3. Save the user record
4. Log out and log back in
5. If multi-company, verify you're in the correct company context

### Problem: Restriction not applying to XML-RPC/API calls

**Possible Causes:**
- Calling as a user with permission
- Restriction is disabled
- Using sudo() to bypass (intentional behavior)

**Solutions:**
1. Verify restriction is enabled: `company.restrict_product_category_change == True`
2. Check the user making API calls doesn't have permission
3. Remove `.sudo()` from your code if present

### Problem: Want to allow category changes during product creation only

**Current Limitation:**
This module doesn't distinguish between creating and updating. The restriction applies to both.

**Workaround:**
1. Disable restriction
2. Create products with categories
3. Enable restriction to prevent future changes

**Alternative:**
Customize the module to add create vs update logic.

### Problem: Need different restrictions per product type

**Current Limitation:**
The restriction is global (per company) and applies to all products equally.

**Workaround:**
Would require custom development to add product type-specific rules.

---

## Upgrade Notes

### Upgrading from Previous Versions

After updating the module code, run:

```bash
odoo-bin -u centrics_product_category_restriction -d your_database
```

Or from Odoo UI:
1. Go to Apps
2. Remove the "Apps" filter
3. Search for "Product Category Change Restriction"
4. Click "Upgrade"

**Version 16.0.1.0.0 Changes:**
- Refactored to use standard Odoo `related` field pattern
- Updated settings view to use proper `o_setting_box` structure
- Fixed computed field to check configuration enable/disable status
- Improved code documentation
- Removed manual get_values/set_values methods

---

## Best Practices

### Implementation Recommendations

1. **Start with restriction disabled**
   - Allow teams to adjust to the new workflow
   - Identify key users who need permission
   - Enable after proper user training

2. **Document your category structure**
   - Create clear guidelines on category usage
   - Train authorized users on proper categorization
   - Maintain category documentation

3. **Regular permission audits**
   - Periodically review who has permission
   - Remove permission from users who no longer need it
   - Follow principle of least privilege

4. **Use with change tracking**
   - Enable Odoo's audit log for product.template
   - Track who makes category changes
   - Review changes during audits

5. **Multi-company considerations**
   - Decide if all companies need same restriction
   - Document per-company policies
   - Communicate differences to users

---

## Support

**Module Author:** Centrics Business Solutions (Pvt) Ltd
**Website:** http://www.centrics.cloud/
**Version:** 16.0.1.0.0
**License:** OPL-1 (Odoo Proprietary License)

For bugs, feature requests, or questions:
1. Check this documentation first
2. Review the Troubleshooting section
3. Contact Centrics Business Solutions support

---

## Credits

**Contributors:**
- Centrics Business Solutions (Pvt) Ltd Development Team

**Maintainer:**
- Centrics Business Solutions (Pvt) Ltd

---

*This module follows Odoo development best practices and coding standards.*
