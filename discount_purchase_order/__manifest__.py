# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
  "name"                 :  "Discount On Purchase Order",
  "summary"              :  """The module allows you to set discount in fixed/percent basis for purchase orders and order lines separately. The total discount in an order is sum of global discount and order line discount.""",
  "category"             :  "Purchases",
'version'                :  '16.0.0.1',
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/Odoo-Discount-On-Purchase-Order.html",
  "description"          :  """odoo discount sale
odoo discount purchase
discount purchase order
discount invoice
discount order line
order global discount
sale global discount
sale percentage discount
sale fixed discount
order percentage discount
order fixed discount
customer order discount
purchase discount
discount reporting
order discount reporting
invoice discount management
advance sale discount
automatic sale discount
automatic invoice discount sync
automatic purchase discount""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=discount_purchase_order",
  "depends"              :  [
                             'purchase',
                             'discount_account_invoice',
                            ],
  "data"                 :  [
                             'views/purchase_views.xml',
                             'report/purchase_order_templates.xml',
                            ],
  "demo"                 :  ['data/discount_demo.xml'],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  99,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}
