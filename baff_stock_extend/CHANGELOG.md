# Changelog

All notable changes to this module will be documented here.

---

## [16.0.1.0.0] - 2026-03-30

### Added
- Initial release of `baff_stock_extend`.
- Added `mail.thread` and `mail.activity.mixin` to `product.category` to enable chatter and activity features.
- Inherited `product.product_category_form_view` to inject the chatter widget (`mail_followers`, `mail_activity`, `mail_thread`).
- Custom `write()` override to track changes to the following `company_dependent` and M2M fields and post internal log notes:
  - Costing Method
  - Inventory Valuation
  - Stock Valuation Account
  - Stock Journal
  - Stock Input Account
  - Stock Output Account
  - Income Account
  - Expense Account
  - Routes (shows Added / Removed items)
