# -*- coding: utf-8 -*-
##############################################################################
#
#    NCTR, Nile Center for Technology Research
#    Copyright (C) 2018-2019 NCTR (<http://www.nctr.sd>).
#
##############################################################################

from odoo import api, fields, models, _
from odoo.osv import expression
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.config import config
import operator
from dateutil.relativedelta import relativedelta


class AccountFiscalyear(models.Model):
    _name = "account.fiscalyear"
    _inherit = ['mail.thread']
    _description = "Fiscal Year"
    _order = "date_start desc"

    name = fields.Char('Fiscal Year', size=64, required=True, track_visibility='onchange')
    code = fields.Char('Code', size=6, required=True, track_visibility='onchange')
    interval = fields.Integer('Period Interval', required="1")
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self.env.user.company_id, track_visibility='onchange')
    date_start = fields.Date('Start Date', required=True, track_visibility='onchange')
    date_stop = fields.Date('End Date', required=True, track_visibility='onchange')
    period_ids = fields.One2many('account.period', 'fiscalyear_id', 'Periods', track_visibility='onchange')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('open', 'Open'),
         ('done', 'Closed'),
         ('cancel', 'Cancel')],
        'Status', readonly=True, default='draft', track_visibility='onchange')
    
    comments = fields.Text('Comments')

    # _sql_constraints = [('fiscal_name_uniq', 'unique(name,company_id,state)', _(
    #     'The Fiscal Year name must be unique per company and state!')), ]

    @api.multi
    @api.constrains('interval')
    def _check_interval(self):
        for year in self:
            if year.interval < 1:
                raise ValidationError(_('The interval must be greater than or equals to one'))

    @api.multi
    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        for year in self:
            if year.date_stop < year.date_start:
                raise ValidationError(_('The start date of a fiscal year must precede its end date.'))
            if self.search([('id', '!=', year.id),
                            ('state', '!=', 'cancel'),
                            ('date_start', '>=', year.date_start),
                            ('date_start', '<=', year.date_stop)]) or \
                self.search(
                [('id', '!=', year.id),
                 ('state', '!=', 'cancel'),
                 ('date_start', '<=', year.date_start),
                 ('date_stop', '>=', year.date_start)]):
                raise ValidationError(_('The fiscal year period must be unique'))

    @api.one
    def create_periods(self):
        return self.create_period(interval=self.interval)

    @api.multi
    def open(self):
        periods_ids = self.env['account.period'].search([('fiscalyear_id', 'in', [x.id for x in self])])
        periods_ids.write({'state': 'open'})
        return self.write({'state': 'open'})

    @api.multi
    def done(self):
        periods_ids_all = self.env['account.period'].search([('fiscalyear_id', 'in', [x.id for x in self])])
        periods_ids_done = self.env['account.period'].search(
            [('fiscalyear_id', 'in', [x.id for x in self]), ('state', '=', 'done')])
        if len(periods_ids_all) != len(periods_ids_done):
            raise ValidationError(_('All periods must be closed'))

        return self.write({'state': 'done'})

    @api.multi
    def cancel(self):
        periods_ids = self.env['account.period'].search([('fiscalyear_id', 'in', [x.id for x in self])])
        periods_ids.write({'state': 'cancel'})
        return self.write({'state': 'cancel'})

    @api.multi
    def create_period3(self):
        return self.create_period(interval=3)

    @api.multi
    def create_period1(self):
        return self.create_period(interval=1)

    @api.multi
    def create_period(self, interval=1):
        period_obj = self.env['account.period']
        for fy in self:
            fy.period_ids.unlink()
            ds = datetime.strptime(fy.date_start, '%Y-%m-%d').date()
            date_stop = datetime.strptime(fy.date_stop, '%Y-%m-%d').date()
            # stop creating the opening period
            # current_year= "%s %s" % (_('Opening Period'), ds.strftime('%Y'))
            # check_period_name=period_obj.search([('name', 'like',current_year)])
            # if(check_period_name):
            #     current_year= "%s %s" % (_('Opening Period 2'), ds.strftime('%Y'))
            # period_obj.create({
            #         'name': current_year,
            #         'code': ds.strftime('00/%Y'),
            #         'date_start': ds,
            #         'date_stop': ds,
            #         'special': True,
            #         'fiscalyear_id': fy.id,
            #     })

            #no_monthes = self.no_monthes(ds, date_stop, fy.calender_type)

            #interval_length = no_monthes / interval
            # for period in self.get_periods(ds, date_stop, fy.calender_type)
            index = 1
            while ds < date_stop:
                de = ds + date_log.relativedelta(months=interval, days=-1)

                if de > date_stop:
                    de = date_stop

                period_obj.create({
                    'name': '%02d/' % int(index) + ds.strftime('%Y'),
                    'code': '%02d/' % int(index) + ds.strftime('%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                })
                ds = ds + relativedelta(months=interval)
                index += 1
        return True

    @api.multi
    def find(self, dt=None, exception=True):
        res = self.finds(dt, exception)
        return res and res[0] or False

    @api.multi
    def finds(self, dt=None, exception=True):
        if not dt:
            dt = fields.Date.context_today(self)
        args = [('date_start', '<=', dt), ('date_stop', '>=', dt)]
        if self._context.get('company_id', False):
            company_id = self._context['company_id']
        else:
            company_id = self.env.user.company_id.id
        args.append(('company_id', '=', company_id))
        ids = self.search(args)
        if not ids:
            if exception:
                raise ValidationError(
                    _('There is no fiscal year defined for this date.\nPlease create one from the configuration of the accounting menu.'))
            else:
                return []
        return ids

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        args = args or []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        ids = self.search(expression.AND([domain, args]), limit=limit)
        return ids.name_get()


class AccountPeriod(models.Model):
    _name = "account.period"
    _description = "Account period"
    _inherit = ['mail.thread']
    _order = "date_start desc"

    name = fields.Char('Period Name', size=64, required=True, track_visibility='onchange')
    code = fields.Char('Code', size=12, track_visibility='onchange')
    special = fields.Boolean('Opening/Closing Period', size=12,
                             help="These periods can overlap.", track_visibility='onchange')
    date_start = fields.Date('Start of Period', required=True, states={
                             'done': [('readonly', True)]}, track_visibility='onchange')
    date_stop = fields.Date('End of Period', required=True, states={
                            'done': [('readonly', True)]}, track_visibility='onchange')
    fiscalyear_id = fields.Many2one('account.fiscalyear', 'Fiscal Year', required=True, states={
                                    'done': [('readonly', True)]}, select=True, track_visibility='onchange')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('open', 'Open'),
         ('done', 'Closed'),
         ('cancel', 'Cancel')],
        'Status', readonly=True, default='draft',
        help='When monthly periods are created. The status is \'Draft\'. At the end of monthly period it is in \'Done\' status.',
        track_visibility='onchange')
    company_id = fields.Many2one(related='fiscalyear_id.company_id', string='Company', store=True, readonly=True)


    # _sql_constraints = [
    #     ('name_company_uniq', 'unique(name, company_id)', 'The name of the period must be unique per company!'),
    #     ('date_start_uniq', 'unique(date_start)', _('fiscalyear date start and stop must be unique.')),
    #     ('date_stop_uniq', 'unique(date_stop)', _('fiscalyear date start and stop must be unique.')),
    # ]

    @api.multi
    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        for year in self:
            if year.date_stop < year.date_start:
                raise ValidationError(_('The start date of a fiscal year period must precede its end date.'))
            if self.search([('id', '!=', year.id),
                            ('state', '!=', 'cancel'),
                            ('date_start', '>=', year.date_start),
                            ('date_start', '<=', year.date_stop)]) or \
                self.search(
                [('id', '!=', year.id),
                 ('state', '!=', 'cancel'),
                 ('date_start', '<=', year.date_start),
                 ('date_stop', '>=', year.date_start)]):
                raise ValidationError(_('The fiscal year period must be unique'))

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_('%s (copy)') % self.name)
        raise ValidationError(_("You can't duplicate Period"))
        return super(AccountPeriod, self).copy(default)

    @api.multi
    @api.constrains('date_stop')
    def _check_duration(self):
        for obj_period in self:
            if obj_period.date_stop < obj_period.date_start:
                raise ValidationError(_('The duration of the Period(s) is/are invalid.'))

    @api.multi
    @api.constrains('date_stop')
    def _check_year_limit(self):
        for obj_period in self:
            if obj_period.special:
                continue

            if obj_period.fiscalyear_id.date_stop < obj_period.date_stop or \
               obj_period.fiscalyear_id.date_stop < obj_period.date_start or \
               obj_period.fiscalyear_id.date_start > obj_period.date_start or \
               obj_period.date_start > obj_period.date_stop or \
               obj_period.fiscalyear_id.date_start > obj_period.date_stop:
                raise ValidationError(
                    _('The period is invalid. Either some periods are overlapping or the period\'s dates are not matching the scope of the fiscal year.'))

            pids = self.search(
                [('date_stop', '>=', obj_period.date_start),
                 ('date_start', '<=', obj_period.date_stop),
                 ('special', '=', False),
                 ('id', '!=', obj_period.id)])
            for period in pids:
                if period.fiscalyear_id.company_id.id == obj_period.fiscalyear_id.company_id.id:
                    raise ValidationError(
                        _('The period is invalid. Either some periods are overlapping or the period\'s dates are not matching the scope of the fiscal year.'))

    @api.multi
    def next(self, period, step):
        ids = self.search([('date_start', '>', period.date_start)])
        if len(ids) >= step:
            return ids[step-1]
        return False

    @api.multi
    def find(self, dt=None):
        if not dt:
            dt = fields.Date.context_today(self)
        args = [('date_start', '<=', dt), ('date_stop', '>=', dt)]
        if self._context.get('company_id', False):
            args.append(('company_id', '=', self._context['company_id']))
        else:
            company_id = self.env.user.company_id.id
            args.append(('company_id', '=', company_id))
        result = []
        # WARNING: in next version the default value for account_periof_prefer_normal will be True
        if self._context.get('account_period_prefer_normal'):
            # look for non-special periods first, and fallback to all if no result is found
            result = self.search(args + [('special', '=', False)])
        if not result:
            result = self.search(args)
        if not result:
            raise ValidationError(_('There is no period defined for this date: %s.\nPlease create one.') % dt)
        return result

    @api.multi
    def action_draft(self):
        for period in self:
            if period.fiscalyear_id.state == 'done':
                raise ValidationError(_('You can not re-open a period which belongs to closed fiscal year'))
            period.write({'state': 'open'})
        return True

    @api.multi
    def action_current(self):
        for period in self:
            period.write({'state': 'current'})

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        ids = self.search(expression.AND([domain, args]), limit=limit)
        return ids.name_get()

    @api.multi
    def write(self, vals):
        if 'company_id' in vals:
            move_lines = self.env['account.move.line'].search(cr, uid, [('period_id', 'in', self.ids)])
            if move_lines:
                raise ValidationError(
                    _('This journal already contains items for this period, therefore you cannot modify its company field.'))
        return super(AccountPeriod, self).write(vals)

    @api.multi
    def build_ctx_periods(self, period_from_id, period_to_id):
        if period_from_id == period_to_id:
            return [period_from_id]
        period_from = self.browse(period_from_id)
        period_date_start = period_from.date_start
        company1_id = period_from.company_id.id
        period_to = self.browse(period_to_id)
        period_date_stop = period_to.date_stop
        company2_id = period_to.company_id.id
        if company1_id != company2_id:
            raise ValidationError(_('You should choose the periods that belong to the same company.'))
        if period_date_start > period_date_stop:
            raise ValidationError(_('Start period should precede then end period.'))

        # /!\ We do not include a criterion on the company_id field below, to allow producing consolidated reports
        # on multiple companies. It will only work when start/end periods are selected and no fiscal year is chosen.

        # for period from = january, we want to exclude the opening period (but it has same date_from, so we have to check if period_from is special or not to include that clause or not in the search).
        if period_from.special:
            return self.search([('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop)])
        return self.search(
            [('date_start', '>=', period_date_start),
             ('date_stop', '<=', period_date_stop),
             ('special', '=', False)])
