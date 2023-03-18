from odoo import models,fields,api,_

class CashVoucherReport(models.AbstractModel):
    _name = 'cash.voucher.report'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('finance_vouchers.report_cash')
        docargs = {
            'doc_ids': docids,
            'doc_model': report.cash,
            'docs': self,
        }
        return report_obj.render('finance_vouchers.report_cash', docargs)