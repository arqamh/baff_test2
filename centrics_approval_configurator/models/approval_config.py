from odoo import models, fields, api, _


class ApprovalConfig(models.Model):
    _name = 'approval.config'
    _description = 'Approval Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(readonly=True, tracking=True)
    model_id = fields.Many2one('ir.model',
                               string='Model',
                               tracking=True)
    approval_level = fields.Selection(
        selection=[('1', 'One Level'), ('2', 'Two Levels'), ('3', 'Three Levels')],
        string="Number of Approval Levels",
        required=True,
        tracking=True
    )
    user_ids_level1 = fields.Many2many('res.users', 'approval_config_users_rel1', string="Level 1 Approvers",
                                       tracking=True)
    user_ids_level2 = fields.Many2many('res.users', 'approval_config_users_rel2', string="Level 2 Approvers",
                                       tracking=True)
    user_ids_level3 = fields.Many2many('res.users', 'approval_config_users_rel3', string="Level 3 Approvers",
                                       tracking=True)

    @api.model
    def create(self, vals):
        """
            Create a new approval configuration record with a formatted name.

            The create method overrides the default behavior of the Odoo model's create
            method to generate a unique name for the approval configuration record based
            on the provided model_id field value.

            Args:
                vals (dict): A dictionary containing the fields and their values to
                initialize the new record.

            Returns:
                recordset: The newly created approval configuration record.
        """
        model_name = self.env['ir.model'].browse(vals.get('model_id')).name if vals.get('model_id') else 'Unknown Model'
        vals['name'] = f"{model_name} - Approval Configuration"
        return super(ApprovalConfig, self).create(vals)

    def write(self, vals):
        """
        Update many-to-many relational fields and log changes.

        This method overrides the default write behavior to handle specific many-to-
        many relational fields and log changes for these fields. It tracks added and
        removed values, constructs a summary of changes, and posts a message with the
        details for every record where the fields' values have been modified.

        Parameters:
            vals (dict): Dictionary containing field names as keys and new values to
            assign as the corresponding values.

        Returns:
            bool: Returns True if the write operation was successful, otherwise False.
        """
        many2many_fields = ['user_ids_level1', 'user_ids_level2', 'user_ids_level3']
        for record in self:
            old_values = {field: record[field] for field in many2many_fields if field in vals}
            result = super(ApprovalConfig, self).write(vals)
            for field in many2many_fields:
                if field in vals:
                    new_values = record[field]
                    if old_values[field] != new_values:
                        added = new_values - old_values[field]
                        removed = old_values[field] - new_values
                        message = ""
                        if added:
                            message += _("Added: %s") % ', '.join(added.mapped('name'))
                        if removed:
                            message += _(" Removed: %s") % ', '.join(removed.mapped('name'))
                        if message:
                            record.message_post(
                                body=_("%s changes: %s") % (self._fields[field].string, message))
            return result


