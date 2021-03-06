# -*- coding: utf-8 -*-
##############################################################################
#
# NCTR, Nile Center for Technology Research
# Copyright (C) 2011-2012 NCTR (<http://www.nctr.sd>).
#
##############################################################################

from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
from openerp.osv import fields, osv,orm
from openerp.tools.translate import _
import tools
import netsvc

#----------------------------------------------------------
# packaging
#----------------------------------------------------------
class stock_pakage(osv.osv):
    _name = "stock.pakage"
    _description = "Pakageing"
    def create(self, cr, user, vals, context=None):
        """
        Override to add constrain of sequance
        @param vals: Dictionary of values
        @return: super of exchange_order
        """
        if ('code' not in vals) or (vals.get('code') == '/'):
            seq = self.pool.get('ir.sequence').get(cr, user, 'stock.pakage')
            vals['code'] = seq and seq or '/'
            if not seq:
                raise  osv.except_osv(_('Warning'), _('No sequence defined!\nPleas contact administartor to configue sequence with code \'stock.pakage\'') )
        new_id = super(stock_pakage, self).create(cr, user, vals, context)
        return new_id
    _columns = {
        'name': fields.char('Name', size=64, required=True, help="name of the packaged"),
        'code': fields.char('Reference', size=64, required=True, readonly=True, select=True),
        'package_line':fields.one2many('stock.package.line','pakage_id', 'package Line'),
    }
    _defaults = {
        'code':'/',
    }
    _sql_constraints = [
                   ('name_uniq', 'unique(name)', 'package name must be unique !'),
                   ('code_uniq', 'unique(code)', 'package Code must be unique !'),

    ]

stock_pakage()
#----------------------------------------------------------
# packaging lines
#----------------------------------------------------------

class stock_package_line(osv.osv):
    _name = "stock.package.line"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, domain="[('type','=','product')]" ),
        'product_qty': fields.float('Quantity', required=True),
        'pakage_id': fields.many2one('stock.pakage','pakage', readonly=True),
    }
    _sql_constraints = [
                   ('product_uniq', 'unique(product_id,pakage_id)', 'product must be unique !'),

    ]
    def _check_positive_qty(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if line.product_qty < 0:
                return False
        return True
    _constraints = [      
        (_check_positive_qty, 'Error! The product quantity can not be less than zero', ['product_qty'])]


stock_package_line()
