# Sri Lanka: Work Entry Holiday Type Mapping (Odoo 16)

Map local public holiday types (Public, Mercantile, Poya…) to Payroll › Work Entry Types.

## Features
- Selection field **`holiday_mapping`** on `hr.work.entry.type` to classify local holiday categories:
  - **— Not a Holiday —** (`none`)
  - **Public Holiday** (`public`)
  - **Mercantile Holiday** (`mercantile`)
  - **Poya Day** (`poya`)
  - **Religious Holiday (Other)** (`religious`)
  - **Company Holiday** (`company`)
- Visible on **Form** and **List** views of Work Entry Types.
- Field is **trackable** to log changes in chatter.
- Module category: **Localization**.

## Menu Path
**Payroll → Configuration → Work Entries → Work Entry Types**

## Installation
1. Copy this folder into your Odoo addons path.
2. Activate developer mode, update the Apps list.
3. Install **Sri Lanka: Work Entry Holiday Type Mapping**. (Depends on: hr_work_entry_holidays_enterprise)

## Usage
1. Open a Work Entry Type (e.g., Attendance, Public Holiday).
2. Set **Holiday Mapping** to the correct local category.
3. Use this mapping in salary rules, overtime computation, and reports. Example:
   ```python
   public_types = self.env["hr.work.entry.type"].search([("holiday_mapping", "=", "public")])
   ```

## Conventions Followed
- One class per file (CamelCase), with the **Python file name equal to the class name**.
- Module folder name remains **snake_case**.
- Fields are trackable (where applicable).
- README.md and TECHNICAL.md included.

## License & Credits
- **License**: OPL-1  
- **Author**: Centrics Business Solutions (Pvt) Ltd  
- **Website**: http://www.centrics.cloud/
