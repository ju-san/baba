# -*- coding: utf-8 -*-
##############################################################################
#
#    NCTR, Nile Center for Technology Research
#    Copyright (C) 2011-2012 NCTR (<http://www.nctr.sd>).
#
##############################################################################
import time
from report import report_sxw

class sea_insurance_notification(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(sea_insurance_notification, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })


report_sxw.report_sxw('report.sea_insurance_notification','sea.insurance','addons/extra_insurance/report/sea_insurance_notfi.rml',parser=sea_insurance_notification, header=False)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
