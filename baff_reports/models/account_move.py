from odoo import fields, api, models
import re
import html


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    bank_1_details = fields.Text(string="Bank 1 Details", default="BankName :NationalDevelopment BankPLC \n"
                                                                  "1A Abeysekara Building | Wakwella Road | Galle | Sri Lanka \n"
                                                                  "USD Account: 115650006412 \n"
                                                                  "EURAccount: 115650006404 \n"
                                                                  "Swift:NDBSLKLX")
    bank_2_details = fields.Text(string="Bank 2 Details", default="BankName :Commercial Bank ofCeylon PLC \n"
                                                                  "Matara Road | Koggala | Sri Lanka \n"
                                                                  "USD Account: 8104011584 \n"
                                                                  "EURAccount: 8104011585 \n"
                                                                  "Swift: CCEYLKLX")
    term_invoice = fields.Char(string="Term")
    shipment_by = fields.Char(string="Shipment By")
    net_weight = fields.Char(string="Net Weight")
    gross_weight = fields.Char(string="Gross Weight")
    total_cmb = fields.Char(string="Total CBM")
    no_of_packages = fields.Char(string="No Of Packages")
    tracking_no = fields.Char(string="Tracking No")
    rex_hs_code = fields.Char(string="REX HS CODE")

    footer_note = fields.Text(string="Bank 2 Details", default="The exporter LKREX114667560DC0445 of the products covered by this document declares that, except where otherwise clearly \n"
"indicated, these products are of Sri Lanka preferential origin according to the rules of origin of the Generalized System of \n"
"preferences of the European Union and that the origin criterion met is W, HS CODE 8903, 7326")

    po_reference = fields.Char(string="PO Reference")
    terms_conditions = fields.Text(string='Terms and Conditions', store=True)


    @staticmethod
    def remove_html_tags(text):
        """ Remove html tags from a string """
        text = html.unescape(text)
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)


    @api.model
    def default_get(self, fields):
        """ Override default get to set default terms and conditions """
        result = super(InheritAccountMove, self).default_get(fields)
        company_terms = self.env.company.invoice_terms
        if company_terms:
            result['terms_conditions'] = self.remove_html_tags(company_terms)
        return result