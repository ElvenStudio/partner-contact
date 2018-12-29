# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _


class ResPartnerSplitNameWizard(models.TransientModel):
    _name = 'res.partner.split_name_wizard'
    _description = _('Split Name Wizard')

    partner_ids = fields.Many2many(
        comodel_name='res.partner',
        default=lambda self: self._get_partner_ids(),
        readonly=True
    )

    split_mode = fields.Selection(
        string=_('Format'),
        selection=[
            ('LF', _('Last/First')),
            ('FL', _('First/Last')),
            ('LFM', _('Last/First Middle')),
            ('L2F', _('Last last/First')),
            ('L2FM', _('Last last/First Middle')),
            ('FML', _('First middle/Last')),
            ('FL2', _('First/Last last')),
            ('FML2', _('First Middle/Last last'))
        ],
        default='LF'
    )

    @api.model
    def _get_partner_ids(self):
        partner_cls = self.env['res.partner']
        partner_ids = self.env.context.get('active_ids', [])
        return partner_cls.browse(partner_ids)

    @api.multi
    def _split_last_first_name(self, partner):
        self.ensure_one()
        if not partner.name:
            return '', ''

        f = partner.name.split(' ')
        if len(f) == 1:
            if self.split_mode[0] == 'F':
                return '', f[0]
            elif self.split_mode[0] == 'L':
                return f[0], ''
        elif len(f) == 2:
            if self.split_mode[0] == 'F':
                return f[1], f[0]
            elif self.split_mode[0] == 'L':
                return f[0], f[1]
        elif len(f) == 3:
            if self.split_mode in ('LFM', 'LF', 'L2FM'):
                return f[2], '%s %s' % (f[0], f[1])
            elif self.split_mode in ('FML', 'FL', 'FML2'):
                return '%s %s' % (f[0], f[1]), f[2]
            elif self.split_mode == 'L2F':
                return '%s %s' % (f[0], f[1]), f[2]
            elif self.split_mode == 'FL2':
                return '%s %s' % (f[1], f[2]), f[0]
        else:
            if self.split_mode[0] == 'F':
                return '%s %s' % (f[2], f[3]), '%s %s' % (f[0], f[1])
            elif self.split_mode[0] == 'L':
                return '%s %s' % (f[0], f[1]), '%s %s' % (f[2], f[3])

        return '', ''

    @api.multi
    def action_split_name(self):
        self.ensure_one()
        for record in self.partner_ids:
            firstname, lastname = self._split_last_first_name(record)
            record.firstname = firstname
            record.lastname = lastname

        return True
