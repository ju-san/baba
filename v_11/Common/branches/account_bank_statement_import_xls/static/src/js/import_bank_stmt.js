odoo.define('bank_stmt_import_xls.import', function (require) {
"use strict";

var core = require('web.core');
var BaseImport = require('base_import.import')

var QWeb = core.qweb;
var _t = core._t;
var _lt = core._lt;

var DataImportStmt = BaseImport.DataImport.extend({
    init: function (parent, action) {
        this._super.apply(this, arguments);
        action.display_name = _t('Import Bank Statement');
        this.filename = action.params.filename || {};
        this.first_load = true;
    },
    start: function () {
        var self = this;
        return this._super().then(function (res) {
            self.id = self.parent_context.wizard_id;
            self.$('input[name=import_id]').val(self.id);
            self['loaded_file']();
        });
    },
    create_model: function() {
        return new $.Deferred().resolve();
    },
    import_options: function () {
        var options = this._super();
        options['bank_stmt_import'] = true;
        return options;
    },
    onfile_loaded: function () {
        var self = this;
        if (this.first_load) {
            this.$('.oe_import_file_show').val(this.filename);
            this.$('.oe_import_file_reload').hide();
            this.first_load = false;
            self['settings_changed']();
        }
        else {
            this.$('.oe_import_file_reload').show();
            this._super();
        }
    },
    
});
core.action_registry.add('import_bank_stmt', DataImportStmt);

});
