from odoo import fields, models, api, tools, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError
import json
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re

# from odoo import amount_to_text


class CashVoucher(models.Model):
    _name = 'cash.voucher'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Finance Vouchers'
    _order = 'request_date desc'

    # def default_employee(self):
    #     return self.env.user.name

    def default_currency(self):
        return self.env.user.company_id.currency_id

    def invoice_tree_view(self):
        tree_view = {
            'name': _('Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'main',
            'domain': [('id', '=', self.x_bill_no.id)],
        }
        return tree_view

    def compute_permits(self):
        payment_count = self.env['account.move'].sudo().search_count([('id', '=', self.x_bill_no.id)])
        self.x_doc_count = payment_count

    @api.depends('amount', 'currency_id')
    def _onchange_amount(self):

        from ..models.money_to_text_ar import amount_to_text_arabic
        if self.amount:
            self.num2wo = amount_to_text_arabic(
                self.amount, self.currency_id.name)

    @api.depends('x_bill_no')
    @api.onchange('x_bill_no')
    def _get_bill(self):
        c = self.env["account.move"].search([('name', '=', self.x_bill_no.name)])
        if c.name:
            self.amount = float(c.amount_total)
            self.request_date = c.date
            self.currency_id = c.currency_id.id
        for i in self.x_bill_no:
            sale_order_line = self.env['cash.voucher.line'].create({
                'account_id': i.partner_id.property_account_payable_id.id,
                'partner_id': i.partner_id.id,
                'cash_request_id': self.id,
                'name':'سداد فاتورة',
                'amount': float(i.amount_total)
            })


    def default_company(self):
        return self.env.user.company_id

    def default_user_analytic(self):
        return self.env.user

    @api.returns('self')
    def _default_employee_get(self):
        return self.env.user

    # def manager_default(self):
    #     return self.env.user.manager_id

    name = fields.Char('Reference', readonly=True, default='New')
    description = fields.Char(string='الوصف')
    accounts_ids = fields.Char(string='حساب المصروف')

    user_name = fields.Many2one('res.users', string='User Name', readonly=True, default=_default_employee_get)
    # manager_id = fields.Many2one('res.users','Manager',default=manager_default)
    pay_type = fields.Boolean(string='Cheque Details',copy=False)
    x_bill_no = fields.Many2one('account.move',string='Bill No',domain="[('type','=','in_invoice')]")
    x_doc_count = fields.Integer(compute='compute_permits',
                               string="Bills")
    request_date = fields.Date('Date', required=True,copy=True, track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', string='Currency', default=default_currency, required=True)
    amount = fields.Monetary('Amount', track_visibility='onchange')
    sequence = fields.Integer(required=True, default=1, )
    state = fields.Selection([('draft', 'Draft'),
                              ('manager', 'Manager'),
                              ('audit', 'Auditor'),
                              ('done', 'Cash Approval'),
                              ('post', 'Posted'),


                              ('cancel', 'Cancel')], default='draft', track_visibility='onchange')

    company_id = fields.Many2one('res.company', string="Company", default=default_company)
    num2wo = fields.Char(string="Amount in word", compute='_onchange_amount', store=True)

    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)

    cash_journal_id = fields.Many2one('account.journal', string='Pay By')
    # employee_name = fields.Many2one('res.partner', string="Employee Name",domain="[('is_employee','=',True)]")
    account_id = fields.Many2one(related='cash_journal_id.default_account_id', string='Account', readonly=1)

    total_with_ex = fields.Float('Subtotal', compute='_total_with_ex')
    total = fields.Float(' Total Expenses', compute='_total_expense')

    count_je = fields.Integer(compute='_count_je_compute')
    count_diff = fields.Integer(compute='_count_diff_compute')

    @api.onchange('custody_line_ids')
    def _onchange_amount(self):
        # for rec in self:
        total =0
        for i in self.custody_line_ids:
            total += i.amount
        self.amount = total

    def _count_je_compute(self):
        for i in self:
            if i.move_id:
                i.count_je = 1
            else:
                i.count_je = 0

    def _count_diff_compute(self):
        for i in self:
            if i.move_id2:
                i.count_diff = 1
            else:
                i.count_diff = 0

    @api.depends('total_units', 'unit_500', 'unit_200', 'unit_100', 'unit_50', 'unit_20', 'unit_10', 'unit_other',
                 'total_other_value', 'unit_tl_10')
    # def _compute_units(self):
    #     for obj in self:
    #         total_500 = obj.unit_500 * 500
    #         total_200 = obj.unit_200 * 200
    #         total_100 = obj.unit_100 * 100
    #         total_50 = obj.unit_50 * 50
    #         total_20 = obj.unit_20 * 20
    #         total_10 = obj.unit_10 * 10
    #         total_other = obj.unit_other * obj.total_other_value
    #         obj.unit_tl_500 = total_500
    #         obj.unit_tl_200 = total_200
    #         obj.unit_tl_100 = total_100
    #         obj.unit_tl_50 = total_50
    #         obj.unit_tl_20 = total_20
    #         obj.unit_tl_10 = total_10
    #         obj.unit_tl_other = total_other
    #         obj.total_units = total_500 + total_200 + total_100 + total_50 + total_20 + total_10 + total_other

    def action_move(self):
        tree_view = self.env.ref('account.view_move_tree')
        form_view = self.env.ref('account.view_move_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'View Journal Entry',
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('id', '=', self.move_id.id)],

        }

    # @api.one
    @api.depends('custody_line_ids')
    def _total_with_ex(self):
        total_without = 0
        for i in self.custody_line_ids:
            total_without += i.amount
        self.total_with_ex = total_without

    @api.depends('custody_line_ids')
    def _compute_tax(self):
        total = 0
        for i in self.custody_line_ids:
            total += i.tax_amount
        self.total_tax = total

    @api.depends('custody_line_ids')
    def _total_expense(self):
        total_tax = 0
        total_am = 0
        for i in self.custody_line_ids:
            # total_tax +=i.tax_amount
            total_am += i.amount
        self.total = total_am

    @api.depends('user_name')
    def _compute_account(self):
        # setting_ob = self.env['res.config.settings'].search([], order='id desc', limit=1)
        #
        # if not setting_ob.petty_account_id:
        #     raise ValidationError('Please Insert Petty cash account In Setting')
        # if setting_ob.petty_account_id:
        #     self.account_id = setting_ob.petty_account_id
        if not self.company_id.petty_account_id:
            raise ValidationError('Please Insert Petty cash account In Company Configuration')
        else:
            self.account_id = self.company_id.petty_account_id

    user_id = fields.Many2one('res.users', default=default_user_analytic)
    # analytic_account = fields.Many2one(related='user_id.analytic_account_id', string='Analytic Account')

    # analytic_account = fields.Many2one('account.analytic.account',string='Analytic Account')
    # check_term = fields.Selection([('not_followup','Not Follow-up'),
    #                                ('followup','Follow-up')
    #                                ],
    #                               default='not_followup',invisible=True)
    # voucher_type = fields.Selection([('cash_vs', 'Cash'),
    #                                ('check_vs', 'Check')
    #                                ],
    #                               default='cash_vs', invisible=True)

    # clrarance Line Many2one
    custody_line_ids = fields.One2many('cash.voucher.line', 'cash_request_id', string='Expenses Line')

    @api.model
    def get_amount(self):
        for i in self.custody_line_ids:
            if self.amount > self.total:
                if i.currency_id != self.env.user.company_id.currency_id:
                    return i.amount * self.env.user.company_id.currency_id.rate
                if i.currency_id == self.env.user.company_id.currency_id:
                    return i.amount

            if self.amount < self.total:
                if i.currency_id != self.env.user.company_id.currency_id:
                    return i.amount * i.currency_id.rate
                if i.currency_id == self.env.user.company_id.currency_id:
                    return i.amount

            if self.amount == self.total:
                if i.currency_id != self.env.user.company_id.currency_id:
                    return i.amount / i.currency_id.rate
                if i.currency_id == self.env.user.company_id.currency_id:
                    return i.amount

    @api.model
    def get_amount_general(self):
        for i in self.custody_line_ids:
            if self.amount > self.total:
                if i.currency_id != self.env.user.company_id.currency_id:
                    return i.amount * i.currency_id.rate
                if i.currency_id == self.env.user.company_id.currency_id:
                    return i.amount

            if self.amount < self.total:
                if i.currency_id != self.env.user.company_id.currency_id:
                    return i.amount * i.currency_id.rate
                if i.currency_id == self.env.user.company_id.currency_id:
                    return i.amount

            if self.amount == self.total:
                if i.currency_id != self.env.user.company_id.currency_id:
                    return i.amount / i.currency_id.rate
                if i.currency_id == self.env.user.company_id.currency_id:
                    return i.amount

    @api.model
    def get_currency(self):
        for i in self.custody_line_ids:
            if i.currency_id != self.env.user.company_id.currency_id:
                return i.currency_id.id

    @api.model
    def amount_currency_debit(self):
        for i in self.custody_line_ids:
            if i.currency_id != self.env.user.company_id.currency_id:
                return i.amount

    @api.model
    def amount_currency_tax_debit(self):
        for i in self.custody_line_ids:
            if i.currency_id != self.env.user.company_id.currency_id:
                return i.tax_amount

    @api.model
    def amount_currency_credit(self):
        for i in self.custody_line_ids:
            if i.currency_id != self.env.user.company_id.currency_id:
                return i.amount * -1

    @api.model
    def amount_currency_credit_equal(self):
        for i in self.custody_line_ids:
            if i.currency_id != self.env.user.company_id.currency_id:
                return self.amount * -1

    @api.model
    def get_total_credit_amount_ex(self):
        for i in self.custody_line_ids:
            if i.currency_id != self.env.user.company_id.currency_id:
                return self.total_amount_ex * -1

    @api.model
    def get_totaporl_debit_amount_ex(self):
        for i in self.custody_line_ids:
            if i.currency_id != self.env.user.company_id.currency_id:
                return self.total_amount_ex


    def confirm_post(self):
        global total_desc, desc
        account_move_object = self.env['account.move']
        account_move_object2 = self.env['account.move']
        if not self.cash_journal_id and not self.account_id:
            raise ValidationError(_('Please insert Journal'))
        if self.amount != self.total:
            raise ValidationError(_('Please make total amount equal Voucher amount!!'))
        if self.amount == self.total:
            l = []
            list = []
            curr_amount = 0
            amount = 0
            currency_id = False
            total=self.total
            for i in self.custody_line_ids:
                description = i.name
                conc = str(i.name or '') + '/' + ' '
                list.append(conc)
                desc = ', '.join(list)
                self.description = desc
                partner_name = i.partner_id.id
                if i.currency_id != self.env.user.company_id.currency_id:
                    amount = i.amount * self.env.user.company_id.currency_id.rate
                    curr_amount = i.amount
                    currency_id = i.currency_id.id

                if i.currency_id == self.env.user.company_id.currency_id:
                    amount = i.amount
                    currency_id = i.currency_id.id
                    curr_amount = i.amount


                debit_val = {
                    'move_id': self.move_id.id,
                    'name': description,
                    'account_id': i.account_id.id,
                    'debit': amount,
                    # 'analytic_account_id': i.analytic_accont_id.id or False,
                    'currency_id': currency_id,
                    'partner_id': partner_name if self.custody_line_ids.partner_id else False,
                    'amount_currency': curr_amount or False,
                    # 'company_id': self.company_id.id or False,

                }
                l.append((0, 0, debit_val))
            credit_val={}
            if self.currency_id != self.env.user.company_id.currency_id:
                credit_amount = self.amount * self.env.user.company_id.currency_id.rate
                currency_id = self.currency_id.id
                credit_curr_amount = self.amount
                credit_val = {

                    'move_id': self.move_id.id,
                    'name': desc,
                    'account_id': self.account_id.id,
                    'credit': credit_amount,
                    'currency_id': currency_id,
                    'partner_id': False,
                    'amount_currency': credit_curr_amount * -1,
                }
            if self.currency_id == self.env.user.company_id.currency_id:
                credit_amount = self.amount
                currency_id = self.currency_id.id
                credit_curr_amount = self.amount
                credit_val = {

                        'move_id': self.move_id.id,
                        'name': desc,
                        'account_id': self.account_id.id,
                        'credit': credit_amount,
                        'currency_id': currency_id,
                        'partner_id': False,
                        'amount_currency': credit_curr_amount * -1,
                }
            l.append((0, 0, credit_val))
                # print("List", l).encode("utf-8")
            vals = {
                    'journal_id': self.cash_journal_id.id,
                    'date': self.request_date,
                    'ref': self.name,
                # 'is_contract': 'normal',
                    # 'company_id': ,
                'move_type': 'entry',
                    'line_ids': l,

            }
            move_id = account_move_object.sudo().create(vals)
            self.move_id = move_id.id
            self.move_id.action_post()
            self.state = 'done'

    @api.model
    def create(self, vals):
        code = 'cash.voucher.code'

        if vals.get('name', 'New') == 'New':
            message = 'Cash Out' + self.env['ir.sequence'].next_by_code(code)
            vals['name'] = message
            return super(CashVoucher, self).create(vals)
            # self.message_post(subject='Create CCR', body='This is New CCR Number' + str(message))

            # self.message_post(subject='Create CCR', body='This is New CCR Number' + str(message))

    # @api.multi
    def unlink(self):
        for i in self:
            if i.state == 'draft' or i.state == 'cancel':
                super(CashVoucher, self).unlink()
            else:
                raise ValidationError('Please be sure the document in Draft state!!')

    # def copy(self):
    #     raise ValidationError("Can not Duplicate a Record !!")

    def cancel_request(self):

        self.move_id.button_draft()
        self.move_id.button_cancel()
        # self.move_id.unlink()
        self.state = 'cancel'

    def reject(self):
        self.state = 'draft'

    def confirm_manager(self):
        global desc2, desc, accounts

        list = []
        list2 = []
        for i in self.custody_line_ids:
            accounts = i.account_id
            conc2 = str(i.account_id.name or '') + '/' + ' '
            list2.append(conc2)
            desc2 = ', '.join(list2)
            self.accounts_ids = desc2
            conc = str(i.name or '') + '/' + ' '
            list.append(conc)
            desc = ', '.join(list)
            self.description = desc
            partner_name = i.partner_id.id
        self.state = 'manager'
    def confirm_audit(self):
        global desc2, desc, accounts

        list = []
        list2 = []
        for i in self.custody_line_ids:
            accounts = i.name
            conc2 = str(i.account_id.name or '') + '/' + ' '
            list2.append(conc2)
            desc2 = ', '.join(list2)
            self.accounts_ids = desc2
            conc = str(i.name or '') + '/' + ' '
            list.append(conc)
            desc = ', '.join(list)
            self.description = desc
            partner_name = i.partner_id.id
        self.state = 'done'


    def confirm_cashier(self):
        global desc2, desc, accounts

        list = []
        list2=[]
        for i in self.custody_line_ids:
            accounts = i.name
            conc2 = str(i.account_id.name or '') + '/' + ' '
            list2.append(conc2)
            desc2 = ', '.join(list2)
            self.accounts_ids=desc2
            conc = str(i.name or '') + '/' + ' '
            list.append(conc)
            desc = ', '.join(list)
            self.description = desc
            partner_name = i.partner_id.id
            if self.amount != self.total:
                raise ValidationError(_('Total amount not equal Currency amount'))
            if self.amount == self.total:
                self.state = 'audit'


class CashVoucherLine(models.Model):
    _name = 'cash.voucher.line'

    def _default_user(self):
        return self.env.user.id

    name = fields.Char('Narration', required=True)
    doc_attachment_id = fields.Many2many('ir.attachment', 'doc_attach_rel4', 'doc_id', 'attach_id5', string="Attachment",
                                         help='You can attach the copy of your document', copy=False)
    analytic_accont_id = fields.Many2one('account.analytic.account',string='Analytic Account', track_visibility='onchange')
    amount = fields.Float('Amount', required=True)
    cash_request_id = fields.Many2one('cash.voucher', string='Cash request')
    account_id = fields.Many2one('account.account', string='Account')
    #############
    currency_id = fields.Many2one('res.currency', 'Currency', compute='_compute_currency')
    company_id = fields.Many2one('res.company', 'Company', compute='_compute_company')
    user_id = fields.Many2one('res.users', 'User', compute='_compute_user')
    date_clear = fields.Date(string='Clear Date', compute='_compute_date')
    # analytic_id = fields.Many2one('account.analytic.account',compute='_compute_analytic')
    #############
    state = fields.Selection(string="State", related='cash_request_id.state')
    user_name = fields.Many2one(string="User", related='cash_request_id.user_name')
    partner_id = fields.Many2one('res.partner', string='Partner')
    product_id = fields.Many2one('product.product',string='Expense Item',required=True)
    # user_id = fields.Many2one('res.users',default=_default_user)
    # tax_amount = fields.Float('الضريبة')

    @api.onchange('product_id')
    def _onchange_account(self):
        if self.product_id:
            self.account_id = self.product_id.property_account_expense_id.id


    @api.depends('cash_request_id.currency_id')
    def _compute_currency(self):
        self.currency_id = self.cash_request_id.currency_id

    @api.onchange('partner_id')
    def _get_partner(self):
        partner_account = self.partner_id.property_account_payable_id.id
        if self.partner_id:
            self.account_id = partner_account

    ######################3

    @api.depends('cash_request_id.company_id')
    def _compute_company(self):
        self.company_id = self.cash_request_id.company_id

    @api.depends('cash_request_id.user_name')
    def _compute_user(self):
        self.user_id = self.cash_request_id.user_name

    @api.depends('cash_request_id.request_date')
    def _compute_date(self):
        self.date_clear = self.cash_request_id.request_date
