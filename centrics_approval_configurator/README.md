# Approval Configurator

This Odoo 16 module allows system administrators or top-level users to dynamically define multi-level approval workflows for any model in the system.

## Features

- Configure approvals for any model (e.g., `sale.order`, `purchase.order`, etc.)
- Supports up to 3 levels of approval
- Each level can have multiple approvers (users)
- Easily extendable for integration into custom model workflows

## Usage

1. Go to **Approval Config > Configurations**
2. Create a new configuration record:
   - Select the target model
   - Choose the number of approval levels (1, 2, or 3)
   - Assign users to each approval level
3. Use the configuration logic in your custom models to fetch the approvers and validate actions

## Menu Access

- Approval Config > Configurations

## Technical

Refer to the `TECHNICAL.md` file for a complete explanation of the module structure and how to integrate it into other models.

## License

This module is released under the Odoo Proprietary License.
