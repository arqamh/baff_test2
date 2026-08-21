import logging
from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    def action_process_draft_assets(self):
        """
        Process selected draft account assets by computing depreciation
        and validating them.
        """
        active_ids = self.env.context.get('active_ids', [])
        records = self.env['account.asset'].browse(active_ids)

        if not records:
            raise UserError("Please select at least one asset.")

        draft_records = records.filtered(lambda r: r.state == 'draft')

        if not draft_records:
            raise UserError("No selected assets are in draft state.")

        success_count = 0
        for record in draft_records:
            try:
                record.compute_depreciation_board()
                record.validate()
                success_count += 1
            except Exception as e:
                _logger.error("Error processing %s: %s", record.name, str(e))

        _logger.info("Successfully processed %d out of %d records",success_count,len(draft_records))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Asset Processing',
                'message': f'Successfully processed {success_count} out of {len(draft_records)} records',
                'type': 'success',
                'sticky': False,
            }
        }