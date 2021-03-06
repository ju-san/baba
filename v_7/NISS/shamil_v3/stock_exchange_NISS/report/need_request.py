#coding: utf-8 
##############################################################################
#
#    NCTR, Nile Center for Technology Research
#    Copyright (C) 2011-2012 NCTR (<http://www.nctr.sd>).
#
##############################################################################

import re
import pooler
from osv import fields, osv
import time
from report import report_sxw
from tools.translate import _


class need_request(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(need_request, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
        })
        self.context = context

    '''def set_context(self, objects, data, ids, report_type=None):
        for obj in self.pool.get('asset.custody').browse(self.cr, self.uid, ids, self.context):
            if obj.asset !='0.0':
		            raise osv.except_osv(_('Error!'), _('You can not print this notification, This request already been printed or not product quantity!'))
        return super(return_custody, self).set_context(objects, data, ids, report_type=report_type)'''


report_sxw.report_sxw('report.need_request', 'exchange.order', 'addons/stock_exchange_NISS/report/need_request.rml' ,parser=need_request , header=True)
