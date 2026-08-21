from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrContractAdvanceLimitLine(models.Model):
    _name = 'hr.contract.advance.limit.line'
    _description = 'Contract Advance Limit Line'

    contract_id = fields.Many2one('hr.contract', string="Contract",
                                  help="The contract linked to this advance limit line.")
    advance_type_id = fields.Many2one('advance.type', string="Advance Type",
                                      help="The type of advance linked to this limit line.")
    maximum_amount = fields.Float(string="Maximum Amount",
                                  help="The maximum amount that can be advanced for this type within this contract.")

    def create(self, values):
        """
        Creates new records for the advance limit lines based on provided values. This method ensures data
        integrity by validating that duplicate limit lines for the same contract and advance type are not
        created. Upon successful creation of a new record, a system message is posted to the related
        contract.

        Parameters
        ----------
        values : list of dict
            A list of dictionaries where each dictionary contains the data for creating a new advance limit
            line. Each dictionary should typically include keys such as 'contract_id' and
            'advance_type_id'.

        Returns
        -------
        record : HrContractAdvanceLimitLine
            The created instance of the advance limit line.

        Raises
        ------
        ValidationError
            Raised if there already exists a limit line for the same contract and advance type in the
            system.
        """
        for rec in values:
            if self.search_count([
                ('contract_id', '=', rec.get('contract_id')),
                ('advance_type_id', '=', rec.get('advance_type_id'))
            ]):
                raise ValidationError(
                    _("Another limit line with this advance type already exists for the same contract."))
        record = super(HrContractAdvanceLimitLine, self).create(values)
        message = _(
            "A new advance limit line has been created for advance type '%s' with a maximum amount of %.2f."
        ) % (record.advance_type_id.name or _('Unknown'), record.maximum_amount)
        record.contract_id.message_post(body=message)
        return record

    def write(self, values):
        """
        Updates the record and logs a message if the maximum amount is changed.
        Prevents updating the record in such a way that it duplicates an existing advance type within the same contract.
        """
        if 'advance_type_id' in values:
            for record in self:
                if self.search_count([
                    ('contract_id', '=', record.contract_id.id),
                    ('advance_type_id', '=', values.get('advance_type_id')),
                    ('id', '!=', record.id)
                ]):
                    raise ValidationError(
                        _("Another limit line with this advance type already exists for the same contract."))

        if 'maximum_amount' in values:
            for record in self:
                message = _(
                    "The maximum amount for advance type '%s' has been updated from %.2f to %.2f."
                ) % (record.advance_type_id.name or _('Unknown'), record.maximum_amount, values['maximum_amount'])
                record.contract_id.message_post(body=message)
        return super(HrContractAdvanceLimitLine, self).write(values)
