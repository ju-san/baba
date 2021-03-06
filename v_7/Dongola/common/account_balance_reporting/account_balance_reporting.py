# -*- coding: utf-8 -*-
##############################################################################
#
#    NCTR, Nile Center for Technology Research
#    Copyright (C) 2011-2012 NCTR (<http://www.nctr.sd>).
#
##############################################################################

from openerp.osv import fields, osv
import re
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import time
from openerp.tools.translate import _
import netsvc
from datetime import datetime, timedelta
from dateutil.relativedelta import *


#---------------------------------------------------
# CSS classes for the account line templates
#---------------------------------------------------

CSS_CLASSES = [('default','Default'),('l1', 'Level 1'), ('l2', 'Level 2'),
                ('l3', 'Level 3'), ('l4', 'Level 4'), ('l5', 'Level 5')]

#---------------------------------------------------
# Account balance report (document / header)
#---------------------------------------------------

class account_balance_reporting(osv.Model):
    """
    Account balance report.
    It stores the configuration/header fields of an account balance report,
    and the linked lines of detail with the values of the accounting concepts
    (values generated from the selected template lines of detail formulas).
    """

    _name = "account.balance.reporting"

    _columns = {
        'name': fields.char('Nameeee', size=64, required=True, readonly=True, states = {'draft': [('readonly', False)]}, select=True),
        'template_id': fields.many2one('account.balance.reporting.template', 'Template', ondelete='set null', required=True, select=True,
                                       readonly=True, states = {'draft': [('readonly', False)]}),
        'state': fields.selection([('draft','Draft'),('calc','Processing'),('calc_done','Processed'),('done','Done'),('canceled','Canceled')], 'State'),
        'company_id': fields.many2one('res.company', 'Company', ondelete='cascade', required=True, readonly=True, 
                                      states = {'draft': [('readonly', False)]}),
        'current_fiscalyear_id': fields.many2one('account.fiscalyear','Fiscal year 1', select=True,  
                                                 readonly=True, states = {'draft': [('readonly', False)]}), 
        'current_period_ids': fields.many2many('account.period', 'account_balance_reporting_account_period_current_rel', 'account_balance_reporting_id', 
                                               'period_id', 'Fiscal year 1 periods', readonly=True, states = {'draft': [('readonly', False)]}),
        'previous_fiscalyear_id': fields.many2one('account.fiscalyear','Fiscal year 2', select=True, readonly=True, 
                                                  states = {'draft': [('readonly', False)]}), 
        'previous_period_ids': fields.many2many('account.period', 'account_balance_reporting_account_period_previous_rel', 'account_balance_reporting_id', 
                                                'period_id', 'Fiscal year 2 periods',readonly=True, states = {'draft': [('readonly', False)]}),
        'chart_account_id': fields.many2one('account.account', 'Chart of account', help='Select Charts of Accounts', required=True, 
                                             domain = [('parent_id','=',False)], readonly=True, states = {'draft': [('readonly', False)]}),
        'detail': fields.selection([('none','Without Details'),('min','Without Regual Accounts'),('cons','With Regual Accounts')], 'Details', required=True, help="Print report with account details?"), 
         #'period_from': fields.many2one('account.period', 'Start period', readonly=True, states = {'draft': [('readonly', False)]}),
         #'period_to': fields.many2one('account.period', 'End period', readonly=True, states = {'draft': [('readonly', False)]}),
        'line_ids': fields.one2many('account.balance.reporting.line', 'report_id', 'Lines', states = {'done': [('readonly', True)]}),
        'target_move': fields.selection([('posted', 'All Posted Entries'), ('all', 'All Entries'), ], 'Target Moves', 
                                        readonly=True, states = {'draft': [('readonly', False)]}, required=True),
        'sign': fields.selection([('sign', 'With Sign'), ('bracket', 'With Brackets'), ('no_sign', 'Without Sign')], 'Sign', 
                                        readonly=False, required=True),  
        'round': fields.boolean('Round', help="Round the value "),
        'rml': fields.related('template_id', 'rml', type='char', string='RML'),
        'date_from': fields.date('Date From  '),
        'date_to': fields.date('Date To'),
        'openning_db':fields.float('openning debit ', digits=(16,2),readonly=True),
        'openning_cr':fields.float('openning credit', digits=(16,2),readonly=True),
        'debit':fields.float('Debit', digits=(16,2),readonly=True),
        'credit':fields.float('Credit', digits=(16,2),readonly=True),
        'balance_db':fields.float('Balance debit', digits=(16,2),readonly=True),
        'balance_cr':fields.float('Balance credit', digits=(16,2),readonly=True),
        'type_rep': fields.selection([('ministry', 'ministry'), ('locality', 'locality')], "Type"),
    }

    def _get_fiscalyear(self, cr, uid, context=None):
        """
        @return: int current fiscalyear id or False
        """
        fiscalyears = self.pool.get('account.fiscalyear').finds(cr, uid, dt=time.strftime('%Y-%m-%d'), exception=False, context=context)
        return fiscalyears and fiscalyears[0] or False

    def _get_account(self, cr, uid, context=None):
        """
        @return: int root account
        """
        accounts = self.pool.get('account.account').search(cr, uid, [('parent_id', '=', False)], limit=1)
        return accounts and accounts[0] or False

    _defaults = {
        'company_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id,
        'state': 'draft',
        'target_move': 'posted',
        'detail': 'none',
        'sign': 'no_sign',
        'round': True,
    }
#===============================================================================
# 
#    def _get_periods(self, cr, uid, period_from, period_to, company_id=[], context={}):
#        print "_get_periods(self, cr, uid, period_from, period_to, company_id=[], context={})", period_from, period_to, company_id, context
#        """
#        Get all periods between from & to period
#        @param period_from: selected start period,
#        @param period_to: selected end period,
#        @param company_id: printed report company,
#        @return: list of all periods between period_from & period_to
#        """
#        period_pool = self.pool.get('account.period')
#        period_from_obj = period_from and period_pool.browse(cr, uid, period_from, context=context) or False
#        period_to_obj = period_to and period_pool.browse(cr, uid, period_to, context=context) or False
#        filters = []
#        if company_id:
#            filters.append(('company_id', 'in', company_id))
#        if period_from_obj:
#            filters.append(('date_start', '>=', period_from_obj.date_start))
#        if period_to_obj and period_from_obj:
#            filters.append(('date_start', '<=', period_to_obj.date_start))
#        elif period_to_obj and not period_from_obj:
#            filters.append(('date_start', '<', period_to_obj.date_start))
#        else:
#            return []
#        return period_pool.search(cr, uid, filters, context=context)
#===============================================================================
    def onchange_template_id(self, cr, uid, ids, template_id, context=None):
        """
        Changing report rml by template rml & reset detail field
        
        @param template_id: int selected template
        @return: dictionary of field's values
        """
        template = self.pool.get('account.balance.reporting.template').browse(cr, uid, template_id, context=context)
        self.write(cr, uid, ids, {'detail':'none'},context=context)
        return {'value':{'detail': 'none', 'rml': template and template.rml}}
    
    def onchange_company_id(self, cr, uid, ids, current_fiscalyear, company_id, context=None):
        """
        Changing report company will change report account chart to the selected company chart
        and change fiscalyear to the current fiscalyear of the selected company
          
        @param current_fiscalyear: selected fiscalyear before changing report company,
        @param company_id: selected company,
        @return: dictionary conatins the new values of chart_account_id & current_fiscalyear_id
        """
        accounts = self.pool.get('account.account').search(cr, uid, [('parent_id', '=', False), ('company_id', '=', company_id)],
                                                           context=context, limit=1)
        fiscalyears = self.pool.get('account.fiscalyear').finds(cr, uid, dt=time.strftime('%Y-%m-%d'), exception=False, context=context)
        return {'value':{'chart_account_id': accounts and accounts[0]  or False ,
                        'current_fiscalyear_id': fiscalyears and fiscalyears[0] or current_fiscalyear,
                        'previous_fiscalyear_id': False
                }}

    def onchange_fiscalyear(self, cr, uid, ids, key, fiscalyear_id, context=None):
        """
        Changing fiscalyear will change some related fields values
        
        @param current_fiscalyear: new fiscalyear,
        @param company_id: report's company,
        @return: dictionary conatins the new values of 
                current_period_ids: all current fiscalyear periods
                previous_period_ids: all previous fiscalyear periods
        """
        return {'value':{key: fiscalyear_id and self.pool.get('account.period').search(cr, uid, [('fiscalyear_id', '=', fiscalyear_id)], 
                                                                                       order='date_start', context=context),
            }}
#===============================================================================
#    def onchange_periods(self, cr, uid, ids, fiscalyear, period_from, period_to, company_id=False, context={}):
#        """
#        Redife current_period_ids & previous_period_ids according to the selected period_from & period_to
#          
#        @param int fiscalyear: current fiscalyear,
#        @param int period_from: selected start period,
#        @param int period_to: selected end periods,
#        @param int company_id: report's company,
#        @return: dictionary conatins the new values of:
#                current_period_ids: periods between period_from & period_to
#                previous_period_ids: periods before period_from
#        """
#        res={'value':{}}
#        company_ids = self.pool.get('res.company')._get_company_children(cr, uid, company_id) or [company_id]
#        current_periods = self._get_periods(cr, uid, period_from, period_to, company_ids, context=context)
#        previous_periods = self._get_periods(cr, uid, False, period_from, company_ids, context=context) or []
#        res['value'].update({
#            'current_period_ids': period_from and current_periods or False, 
#            'previous_period_ids': period_from and previous_periods or False, 
#            'period_to': period_from and period_to or False
#        })
#        return res
#===============================================================================

    def action_calculate(self, cr, uid, ids, context=None):
        """
        Called when the user presses the Calculate button.
        It will use the report template to generate lines of detail for the
        report with calculated values.

        @return: boolean True
        """



        report_line_facade = self.pool.get('account.balance.reporting.line')
        # Set the state to 'calculating'
        self.write(cr, uid, ids, {'state': 'calc'}, context=context)
        # Replace the lines of detail of the report with new lines from its template
        reports = self.browse(cr, uid, ids, context=context)
        for report in reports:
            # Clear the report data (unlink the lines of detail)
            report_line_facade.unlink(cr, uid, [line.id for line in report.line_ids], context=context)
            # Fill the report with a 'copy' of the lines of its template (if it has one)
            if report.template_id:
                for template_line in report.template_id.line_ids:
                    report_line_facade.create(cr, uid, {
                            'code': template_line.code,
                            'name': template_line.name,
                            'report_id': report.id,
                            'template_line_id': template_line.id,
                            'parent_id': None,
                            'current_value': None,
                            'openning_balance':None,
                            'previous_value': None,
                            'sequence': template_line.sequence,
                            'css_class': template_line.css_class,
                        }, context=context)
        # Set the parents of the lines in the report
        # Note: We reload the reports objects to refresh the lines of detail.
        reports = self.browse(cr, uid, ids, context=context)
        for report in reports:
            if report.template_id:
                # Establecemos los padres de las líneas (ahora que ya están creados)
                for line in report.line_ids:
                    print "LINE ID ",line.current_value
                    line.openning_balance = 11


                    if line.template_line_id and line.template_line_id.parent_id:
                        parent_line_id = report_line_facade.search(cr, uid, [('report_id', '=', report.id), 
                                                                             ('code', '=', line.template_line_id.parent_id.code)], 
                                                                             context=context)
                        report_line_facade.write(cr, uid, line.id, {'parent_id': len(parent_line_id) and parent_line_id[0] or None,}, context=context)
        # Calculate the values of the lines
        # Note: We reload the reports objects to refresh the lines of detail.
        reports = self.browse(cr, uid, ids, context=context)
        for report in reports:
            if report.template_id:
                # Refresh the report's lines values
                print "BEFORE ", line.current_value
                for line in report.line_ids:
                    line.refresh_values()
                print "Final ", line.current_value
                # Set the report as calculated
                self.write(cr, uid, [report.id], {'state': 'calc_done'}, context=context)
            else:
                # Ouch! no template: Going back to draft state.
                self.write(cr, uid, [report.id], {'state': 'draft'}, context=context)
        
        for report in reports:
            total_debit=0.0
            total_credit=0.0
            total_openning_db=0.0
            total_openning_cr=0.0
            total_balance_db=0.0
            total_balance_cr=0.0
            for line in report.line_ids:
                total_debit+=abs(line.debit)
                total_credit+=abs(line.credit)
                if line.openning_balance>0:
                   total_openning_db+=abs(line.openning_balance)
                else:
                   total_openning_cr+=abs(line.openning_balance)
                if line.current_value>0:
                    total_balance_db+=abs(line.current_value)
                else:
                    total_balance_cr+=abs(line.current_value)

 
        return self.write(cr, uid, [report.id], {'credit':total_credit,'debit':total_debit ,'openning_db':total_openning_db,'balance_db':total_balance_db,'openning_cr':total_openning_cr,'balance_cr':total_balance_cr}, context=None)

    def action_cancel(self, cr, uid, ids, context=None):
        """
        Button action changing record state to 'canceled
        """
        return self.write(cr, uid, ids, {'state': 'canceled'}, context=context)

    def action_recover(self, cr, uid, ids, context=None):
        """
        Button action changing record state to 'draft'
        """
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

#---------------------------------------------------
# Account balance report line of detail (accounting concept)
#---------------------------------------------------
class account_balance_reporting_line(osv.Model):
    """
    Account balance report line / Accounting concept
    One line of detail of the balance report representing an accounting
    concept with its values.
    The accounting concepts follow a parent-children hierarchy.
    Its values (current and previous) are calculated based on the 'value'
    formula of the linked template line.
    """

    _name = "account.balance.reporting.line"

    _columns = {
        'report_id': fields.many2one('account.balance.reporting', 'Report', ondelete='cascade'),
        'code': fields.char('Code', size=64, required=True, select=True),
        'name': fields.char('Name', size=256, required=True, select=True),
        'notes': fields.text('Notes'),
        'current_value': fields.float('Fiscal year 1', digits=(16,2)),
        'debit': fields.float('debit', digits=(16,2)),
        'credit': fields.float('credit', digits=(16,2)),
        
        'previous_value': fields.float('Fiscal year 2', digits=(16,2)),
        'sequence': fields.char('Sequence', size=32, required=False),
        'css_class': fields.selection(CSS_CLASSES, 'CSS Class', required=False),
        'template_line_id': fields.many2one('account.balance.reporting.template.line', 'Line template', ondelete='set null'),
        'parent_id': fields.many2one('account.balance.reporting.line', 'Parent', ondelete='cascade'),
        'child_ids': fields.one2many('account.balance.reporting.line', 'parent_id', 'Children'),
        'disclosure_number': fields.integer('Disclosure Number'), 
        'account_id': fields.many2one('account.account', 'Disclosure Account'),
        'current_value_no_f_mounth': fields.float('Units', digits=(16, 2)),
        'openning_balance':fields.float('Openning Balance', digits=(16,2)),
    }

    _defaults = {
        'report_id': lambda self, cr, uid, context: context.get('report_id', None),
        'css_class': 'default', 
    }

    _order = "sequence, code"

    _sql_constraints = [('report_code_uniq', 'unique (report_id,code)', _("The code must be unique for this report!"))]

    def name_get(self, cr, uid, ids, context=None):
        """
        Line name show as "[code] name"
        """
        return ids and [(item.id, "[%s] %s" % (item.code, item.name)) for item in self.browse(cr, uid, ids, context=context)] or []

    def name_search(self, cr, uid, name, args=[], operator='ilike', context={}, limit=80):
        """
        Allow searching by line name or code
        """
        ids = name and self.search(cr, uid, [('code','ilike',name)]+ args, context=context, limit=limit) or []
        if not ids:
            ids = self.search(cr, uid, [('name',operator,name)]+ args, context=context, limit=limit)
        return self.name_get(cr, uid, ids, context=context)

    def refresh_values(self, cr, uid, ids, context=None):
        """
        Recalculates the values of this report line using the
        linked line template values formulas:

        Depending on this formula the final value is calculated as follows:
        - Empy template value: sum of (this concept) children values.
        - Number with decimal point ("10.2"): that value (constant).
        - Account numbers separated by commas ("430,431,(437)"): Sum of the account balances.
            (The sign of the balance depends on the balance mode)
        - Concept codes separated by "+" ("11000+12000"): Sum of those concepts values.
        """
 

        for line in self.browse(cr, uid, ids, context=context):
            current_value = 0.0
            previous_value = 0.0
            # We use the same code to calculate both fiscal year values,
            # just iterating over them.
            for fyear in ('current', 'previous','openning_balance'):
                value = 0
                template_value = (fyear == 'current' and line.template_line_id.current_value) or \
                                 (fyear == 'previous' and line.template_line_id.previous_value) or \
                                 (fyear == 'openning_balance' and line.template_line_id.openning_balance) or  0
                # Remove characters after a ";" (we use ; for comments)
                template_value = template_value and len(template_value) and template_value.split(';')[0] or template_value
                if (fyear == 'current' and not line.report_id.current_fiscalyear_id) or \
                       (fyear == 'previous' and not line.report_id.previous_fiscalyear_id):
                    value = 0
                else:
                    # Calculate the value
                    if not template_value or not len(template_value):
                        # Empy template value => sum of the children, of this concept, values.
                        for child in line.child_ids:
                            # Tell the child to refresh its values
                            child.refresh_values()
                            # Reload the child datacurrent_period_ids
                            child = self.browse(cr, uid, [child.id], context=context)[0]
                            value += (fyear == 'current' and float(child.current_value)) or \
                                     (fyear == 'previous' and float(child.previous_value)) or \
                                     (fyear == 'openning_balance' and float(child.openning_balance)) or 0
                    elif re.match(r'^\-?[0-9]*\.[0-9]*$', template_value):
                        # Number with decimal points => that number value (constant).
                        value = float(template_value)
                    elif re.match(r'^[0-9a-zA-Z,\(\)\*_]*$', template_value):
                        # Account numbers separated by commas => sum of the account balances.
                        # We will use the context to filter the accounts by fiscalyear
                        # and periods.
                        #ctx = {'periods': fyear == 'current' and [p.id for p in line.report_id.current_period_ids] or \
                                      #  fyear == 'previous' and [p.id for p in line.report_id.previous_period_ids] or []}
                        # Get the mode of balance calculation from the template
                        balance_mode = line.template_line_id.report_id.balance_mode
                        # Get the balance
                        if ctx.get('periods'):
                            value = line._get_account_balance(template_value, balance_mode, context=ctx)
                    elif re.match(r'^[\+\-0-9a-zA-Z_\*]*$', template_value):
                        # Account concept codes separated by "+" => sum of the concept (report lines) values.
                        for line_code in re.findall(r'(-?\(?[0-9a-zA-Z_]*\)?)', template_value):
                            # Check the sign of the code (substraction)
                            if line_code.startswith('-') or line_code.startswith('('):
                                sign = -1.0
                            else:
                                sign = 1.0
                            line_code = line_code.strip('-()*')
                            # Check if the code is valid (findall might return empty strings)
                            if len(line_code) > 0:
                                # Search for the line (perfect match)
                                line_ids = self.search(cr, uid, [('report_id','=', line.report_id.id),
                                                                 ('code', '=', line_code)], context=context)
                                for child in self.browse(cr, uid, line_ids, context=context):
                                    # Tell the child to refresh its values
                                    child.refresh_values()
                                    # Reload the child data
                                    child = self.browse(cr, uid, [child.id], context=context)[0]
                                    if fyear == 'current':
                                        value += float(child.current_value) * sign
                                    elif fyear == 'previous':
                                        value += float(child.previous_value) * sign
                # Negate the value if needed
                value = line.template_line_id.negate and -value or value

                if fyear == 'current':
                    current_value =  value
                   #openning_balance = value

                elif fyear == 'previous':
                    previous_value = value
                    #openning_balance = value

            # Write the values
            self.write(cr, uid, [line.id], {
                    'current_value': current_value,
                    'previous_value': previous_value,
                    'openning_balance':openning_balance
                }, context=context)
        return True

    def _get_account_balance(self, cr, uid, ids, code, balance_mode=0, context=None):
        """
        It returns the (debit, credit, balance*) tuple for a account with the
        given code, or the sum of those values for a set of accounts
        when the code is in the form "400,300,(323)"
        Depending on the balance_mode, the balance is calculated as follows:
          Mode 0: debit-credit for all accounts (default);
          Mode 1: debit-credit, credit-debit for accounts in brackets;
          Mode 2: credit-debit for all accounts;
          Mode 3: credit-debit, debit-credit for accounts in brackets.
        Also the user may specify to use only the debit or credit of the account
        instead of the balance writing "debit(551)" or "credit(551)".
        """

        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalperiod_obj = self.pool.get('account.period')
        acc_facade = self.pool.get('account.account')
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        company_obj = self.pool.get('res.company')
        res = 0.0
        line = self.browse(cr, uid, ids)[0]
        assert balance_mode in ('0', '1', '2', '3'), "balance_mode should be in [0..3]"
        #if line.report_id.target_move == 'posted':
            #context.update({'state':'posted'})
        context['state'] = ('draft','compeleted','posted')
        if line.report_id.date_from:
            context.update({'date_from':line.report_id.date_from})

        if line.report_id.date_to:
            context.update({'date_to':line.report_id.date_to})
        
           
        context.update({'type':'statement'})
        context.update({'unit_type':line.report_id.type_rep})

        # get fisacl years of all childs companies with same code
        company_id= fiscalyear_obj.browse(cr, uid, context['fiscalyear'], context=context).company_id.id
        company_ids=company_obj.search(cr, uid, [ ('id', 'child_of', line.report_id.company_id.id)], context=context)
        year_code=fiscalyear_obj.browse(cr, uid, context['fiscalyear'], context=context).code

        if company_ids:
            fiscalyear_ids= fiscalyear_obj.search(cr, uid, [('code', '=',year_code), ('company_id', 'in', company_ids)], context=context)
        if not company_ids:
            fiscalyear_ids= fiscalyear_obj.search(cr, uid, [('code', '=',year_code), ('company_id', '=', line.report_id.company_id.id)], context=context)
        init_period = fiscalperiod_obj.search(cr, uid, [('special', '=', True), ('fiscalyear_id', 'in', fiscalyear_ids)])
        date_start = fiscalperiod_obj.browse(cr, uid, init_period[0], context=context).date_start
        if not line.report_id.date_from:
            context.update({'date_from':date_start})
        if fiscalyear_ids:
            context.update({'fiscalyear':fiscalyear_ids})
        date_from1=context['date_from']

        if context['date_from']==date_start:
            date_from1 = datetime.strptime(date_from1, DEFAULT_SERVER_DATE_FORMAT)
            date_from1= date_from1+timedelta(days=1)
            context.update({'date_from':date_from1})
        # We iterate over the accounts listed in "code", so code can be
        # a string like "430+431+432-438"; accounts split by "+" will be added,
        # accounts split by "-" will be substracted.
        # We also take in consideration the balance_mode:
        #   Mode 0: credit-debit for all accounts
        #   Mode 1: debit-credit, credit-debit for accounts in brackets
        #   Mode 2: credit-debit, debit-credit for accounts in brackets
        #   Mode 3: credit-debit, debit-credit for accounts in brackets.
        # And let the user get just the credit or debit if he specifies so.
        for account_code in re.findall('(-?\w*\(?[0-9a-zA-Z_]*\)?)', code):
            # Check if the code is valid (findall might return empty strings)
            if len(account_code) > 0:
                # Check the sign of the code (substraction)
                if account_code.startswith('-'):
                    sign = -1.0
                    account_code = account_code[1:] # Strip the sign
                else:
                    sign = 1.0
                if re.match(r'^debit\(.*\)$', account_code):
                    # Use debit instead of balance
                    mode = 'debit'
                    account_code = account_code[6:-1] # Strip debit()
                elif re.match(r'^credit\(.*\)$', account_code):
                    # Use credit instead of balance
                    mode = 'credit'
                    account_code = account_code[7:-1] # Strip credit()
                else:
                    mode = 'balance'
                    # Calculate the balance, as given by the balance mode
                    if balance_mode == '1' and account_code.startswith('(') and account_code.endswith(')'):
                        # We use debit-credit as default balance,
                        # but for accounts in brackets we use credit-debit
                        sign = -1.0 * sign
                    elif balance_mode == '2':
                        # We use credit-debit as the balance,
                        sign = -1.0 * sign
                    elif balance_mode == '3' and not account_code.startswith('(') and account_code.endswith(')'):
                        # We use credit-debit as default balance,
                        # but for accounts in brackets we use debit-credit
                        sign = -1.0 * sign
                    # Strip the brackets (if there are brackets)
                    if account_code.startswith('(') and account_code.endswith(')'):
                        account_code = account_code[1:-1]
                # Search for the account (perfect match)context
                account_ids = acc_facade.search(cr, uid, [('code', '=', account_code), 
                                                          ('company_id', '=', line.report_id.company_id.id)], context=context)
                if not account_ids:
                    # We didn't find the account, search for a subaccount ending with '0'
                    account_ids = acc_facade.search(cr, uid, [('code', '=like', '%s%%0' % account_code), 
                                                              ('company_id', '=', line.report_id.company_id.id)], context=context)
                if len(account_ids) > 0:
                    if mode == 'debit':
                        res += acc_facade.read(cr, uid, account_ids, ['debit'], context)[0]['debit'] or 0.0

                    elif mode == 'credit':
                        res += acc_facade.read(cr, uid, account_ids, ['credit'], context)[0]['credit'] or 0.0
                    else:
                        # MODIFY HERE 
                        res += acc_facade.read(cr, uid, account_ids, ['balance'], context)[0]['balance'] * sign or 0.0

                else:
                    netsvc.Logger().notifyChannel('account_balance_reporting', netsvc.LOG_WARNING, "Account with code '%s' not found!" % account_code)
 
        return res



    def _get_account_balance_custom2(self, cr, uid, ids, code, balance_mode=0, context=None):
        """
        It returns the (debit, credit, balance*) tuple for a account with the
        given code, or the sum of those values for a set of accounts
        when the code is in the form "400,300,(323)"
        Depending on the balance_mode, the balance is calculated as follows:
          Mode 0: debit-credit for all accounts (default);
          Mode 1: debit-credit, credit-debit for accounts in brackets;
          Mode 2: credit-debit for all accounts;
          Mode 3: credit-debit, debit-credit for accounts in brackets.
        Also the user may specify to use only the debit or credit of the account
        instead of the balance writing "debit(551)" or "credit(551)".
        """

        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalperiod_obj = self.pool.get('account.period')
        acc_facade = self.pool.get('account.account')
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        company_obj = self.pool.get('res.company')
        res = 0.0
        line = self.browse(cr, uid, ids)[0]
        assert balance_mode in ('0', '1', '2', '3'), "balance_mode should be in [0..3]"
        #if line.report_id.target_move == 'posted':
            #context.update({'state':'posted'})
        context['state'] = ('draft','compeleted','posted')
        if line.report_id.date_from:
            context.update({'date_from':line.report_id.date_from})

        if line.report_id.date_to:
            context.update({'date_to':line.report_id.date_to})
        
        context.update({'unit_type':line.report_id.type_rep})  
        context.update({'type':'statement'})
        context.update({'initial_bal':True})

        # get fisacl years of all childs companies with same code
        company_id= fiscalyear_obj.browse(cr, uid, context['fiscalyear'], context=context).company_id.id
        company_ids=company_obj.search(cr, uid, [ ('id', 'child_of', line.report_id.company_id.id)], context=context)
        year_code=fiscalyear_obj.browse(cr, uid, context['fiscalyear'], context=context).code

        if company_ids:
            fiscalyear_ids= fiscalyear_obj.search(cr, uid, [('code', '=',year_code), ('company_id', 'in', company_ids)], context=context)
        if not company_ids:
            fiscalyear_ids= fiscalyear_obj.search(cr, uid, [('code', '=',year_code), ('company_id', '=', line.report_id.company_id.id)], context=context)
        init_period = fiscalperiod_obj.search(cr, uid, [('special', '=', True), ('fiscalyear_id', 'in', fiscalyear_ids)])
        date_start = fiscalperiod_obj.browse(cr, uid, init_period[0], context=context).date_start
        if not line.report_id.date_from:
            context.update({'date_from':date_start})
        if fiscalyear_ids:
            context.update({'fiscalyear':fiscalyear_ids})
        date_from1=context['date_from']
        if context['date_from']==date_start:
            date_from1 = datetime.strptime(date_from1, DEFAULT_SERVER_DATE_FORMAT)
            date_from1= date_from1+timedelta(days=1)
            context.update({'date_from':date_from1})
        # We iterate over the accounts listed in "code", so code can be
        # a string like "430+431+432-438"; accounts split by "+" will be added,
        # accounts split by "-" will be substracted.
        # We also take in consideration the balance_mode:
        #   Mode 0: credit-debit for all accounts
        #   Mode 1: debit-credit, credit-debit for accounts in brackets
        #   Mode 2: credit-debit, debit-credit for accounts in brackets
        #   Mode 3: credit-debit, debit-credit for accounts in brackets.
        # And let the user get just the credit or debit if he specifies so.
        for account_code in re.findall('(-?\w*\(?[0-9a-zA-Z_]*\)?)', code):
            # Check if the code is valid (findall might return empty strings)
            if len(account_code) > 0:
                # Check the sign of the code (substraction)
                if account_code.startswith('-'):
                    sign = -1.0
                    account_code = account_code[1:] # Strip the sign
                else:
                    sign = 1.0
                if re.match(r'^debit\(.*\)$', account_code):
                    # Use debit instead of balance
                    mode = 'debit'
                    account_code = account_code[6:-1] # Strip debit()
                elif re.match(r'^credit\(.*\)$', account_code):
                    # Use credit instead of balance
                    mode = 'credit'
                    account_code = account_code[7:-1] # Strip credit()
                else:
                    mode = 'balance'
                    # Calculate the balance, as given by the balance mode
                    if balance_mode == '1' and account_code.startswith('(') and account_code.endswith(')'):
                        # We use debit-credit as default balance,
                        # but for accounts in brackets we use credit-debit
                        sign = -1.0 * sign
                    elif balance_mode == '2':
                        # We use credit-debit as the balance,
                        sign = -1.0 * sign
                    elif balance_mode == '3' and not account_code.startswith('(') and account_code.endswith(')'):
                        # We use credit-debit as default balance,
                        # but for accounts in brackets we use debit-credit
                        sign = -1.0 * sign
                    # Strip the brackets (if there are brackets)
                    if account_code.startswith('(') and account_code.endswith(')'):
                        account_code = account_code[1:-1]
                # Search for the account (perfect match)context
                account_ids = acc_facade.search(cr, uid, [('code', '=', account_code), 
                                                          ('company_id', '=', line.report_id.company_id.id)], context=context)
                if not account_ids:
                    # We didn't find the account, search for a subaccount ending with '0'
                    account_ids = acc_facade.search(cr, uid, [('code', '=like', '%s%%0' % account_code), 
                                                              ('company_id', '=', line.report_id.company_id.id)], context=context)
                if len(account_ids) > 0:
                    if mode == 'debit':
                        res += acc_facade.read(cr, uid, account_ids, ['debit'], context)[0]['debit'] or 0.0

                    elif mode == 'credit':
                        res += acc_facade.read(cr, uid, account_ids, ['credit'], context)[0]['credit'] or 0.0
                    else:
                        # MODIFY HERE 
                        res += acc_facade.read(cr, uid, account_ids, ['balance'], context)[0]['balance'] * sign or 0.0

                else:
                    netsvc.Logger().notifyChannel('account_balance_reporting', netsvc.LOG_WARNING, "Account with code '%s' not found!" % account_code)
 
        return res

    def _get_account_balance_custom(self, cr, uid, ids, code, balance_mode=0, context=None):
        """
        It returns the (debit, credit, balance*) tuple for a account with the
        given code, or the sum of those values for a set of accounts
        when the code is in the form "400,300,(323)"
        Depending on the balance_mode, the balance is calculated as follows:
          Mode 0: debit-credit for all accounts (default);
          Mode 1: debit-credit, credit-debit for accounts in brackets;
          Mode 2: credit-debit for all accounts;
          Mode 3: credit-debit, debit-credit for accounts in brackets.
        Also the user may specify to use only the debit or credit of the account
        instead of the balance writing "debit(551)" or "credit(551)".
        """

        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalperiod_obj = self.pool.get('account.period')
        acc_facade = self.pool.get('account.account')
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        company_obj = self.pool.get('res.company')
        res = 0.0
        line = self.browse(cr, uid, ids)[0]
        assert balance_mode in ('0', '1', '2', '3'), "balance_mode should be in [0..3]"
        #if line.report_id.target_move == 'posted':
            #context.update({'state': 'posted'})

        context['state'] = ('draft','compeleted','posted')
        if line.report_id.date_from:
            context.update({'date_from': line.report_id.date_from})

        if line.report_id.date_to:
            context.update({'date_to': line.report_id.date_to})

        context.update({'type': 'statement'})

        # get fisacl years of all childs companies with same code
        company_id = fiscalyear_obj.browse(cr, uid, context['fiscalyear'], context=context).company_id.id
        company_ids = company_obj.search(cr, uid, [('id', 'child_of', line.report_id.company_id.id)], context=context)
        year_code = fiscalyear_obj.browse(cr, uid, context['fiscalyear'], context=context).code

        if company_ids:
            fiscalyear_ids = fiscalyear_obj.search(cr, uid,
                                                   [('code', '=', year_code), ('company_id', 'in', company_ids)],
                                                   context=context)
        if not company_ids:
            fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('code', '=', year_code),
                                                             ('company_id', '=', line.report_id.company_id.id)],
                                                   context=context)
        init_period = fiscalperiod_obj.search(cr, uid,
                                              [('special', '=', True), ('fiscalyear_id', 'in', fiscalyear_ids)])


        date_start = fiscalperiod_obj.browse(cr, uid, init_period[0], context=context).date_start
        # convert string date object and add 1 day to it  #Mudathir
        date_start = datetime.strptime(date_start, '%Y-%m-%d')
        #date_start = date_start + relativedelta(days=1)

        if not line.report_id.date_from:
            context.update({'date_from':date_start})
        if fiscalyear_ids:
            context.update({'fiscalyear': fiscalyear_ids})
 

        # We iterate over the accounts listed in "code", so code can be
        # a string like "430+431+432-438"; accounts split by "+" will be added,
        # accounts split by "-" will be substracted.
        # We also take in consideration the balance_mode:
        #   Mode 0: credit-debit for all accounts
        #   Mode 1: debit-credit, credit-debit for accounts in brackets
        #   Mode 2: credit-debit, debit-credit for accounts in brackets
        #   Mode 3: credit-debit, debit-credit for accounts in brackets.
        # And let the user get just the credit or debit if he specifies so.
        for account_code in re.findall('(-?\w*\(?[0-9a-zA-Z_]*\)?)', code):
            # Check if the code is valid (findall might return empty strings)
            if len(account_code) > 0:
                # Check the sign of the code (substraction)
                if account_code.startswith('-'):
                    sign = -1.0
                    account_code = account_code[1:]  # Strip the sign
                else:
                    sign = 1.0
                if re.match(r'^debit\(.*\)$', account_code):
                    # Use debit instead of balance
                    mode = 'debit'
                    account_code = account_code[6:-1]  # Strip debit()
                elif re.match(r'^credit\(.*\)$', account_code):
                    # Use credit instead of balance
                    mode = 'credit'
                    account_code = account_code[7:-1]  # Strip credit()
                else:
                    mode = 'balance'
                    # Calculate the balance, as given by the balance mode
                    if balance_mode == '1' and account_code.startswith('(') and account_code.endswith(')'):
                        # We use debit-credit as default balance,
                        # but for accounts in brackets we use credit-debit
                        sign = -1.0 * sign

                    elif balance_mode == '2':
                        # We use credit-debit as the balance,
                        sign = -1.0 * sign
                    elif balance_mode == '3' and not account_code.startswith('(') and account_code.endswith(')'):
                        # We use credit-debit as default balance,
                        # but for accounts in brackets we use debit-credit
                        sign = -1.0 * sign
                    # Strip the brackets (if there are brackets)
                    if account_code.startswith('(') and account_code.endswith(')'):
                        account_code = account_code[1:-1]
                # Search for the account (perfect match)context
                account_ids = acc_facade.search(cr, uid, [('code', '=', account_code),
                                                          ('company_id', '=', line.report_id.company_id.id)],
                                                context=context)
                if not account_ids:
                    # We didn't find the account, search for a subaccount ending with '0'
                    account_ids = acc_facade.search(cr, uid, [('code', '=like', '%s%%0' % account_code),
                                                              ('company_id', '=', line.report_id.company_id.id)],
                                                    context=context)
                if len(account_ids) > 0:
                    if mode == 'debit':
                        res += acc_facade.read(cr, uid, account_ids, ['debit'], context)[0]['debit'] or 0.0

                    elif mode == 'credit':
                        res += acc_facade.read(cr, uid, account_ids, ['credit'], context)[0]['credit'] or 0.0
                    else:
                        # MODIFY HERE
                        res += acc_facade.read(cr, uid, account_ids, ['balance'], context)[0]['balance'] * sign or 0.0


                else:
                    netsvc.Logger().notifyChannel('account_balance_reporting', netsvc.LOG_WARNING,
                                                  "Account with code '%s' not found!" % account_code)

        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
