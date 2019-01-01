# -*- coding: utf-8 -*-
# Copyright 2014 Agile Business Group (<http://www.agilebg.com>)
# Copyright 2015 Grupo ESOC <www.grupoesoc.es>
# Copyright 2015 Antiun Ingenieria S.L. - Antonio Espinosa
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from openerp import api, fields, models
from . import exceptions


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Adds last name and first name; name becomes a stored function field."""

    _inherit = 'res.partner'

    firstname = fields.Char("First name")
    lastname = fields.Char("Last name")

    @api.model
    def create(self, vals):
        """Add inverted names at creation if unavailable."""
        context = dict(self.env.context)
        name = vals.get("name", context.get("default_name"))

        if name is not None:
            # Calculate the splitted fields
            inverted = self._get_inverse_name(
                self._get_whitespace_cleaned_name(name),
                vals.get("is_company",
                         self.default_get(["is_company"])["is_company"]))

            for key, value in inverted.iteritems():
                if not vals.get(key) or context.get("copy"):
                    vals[key] = value

        return super(ResPartner, self.with_context(context)).create(vals)

    @api.multi
    def copy(self, default=None):
        """Ensure partners are copied right.

        Odoo adds ``(copy)`` to the end of :attr:`~.name`, but that would get
        ignored in :meth:`~.create` because it also copies explicitly firstname
        and lastname fields.
        """
        return super(ResPartner, self.with_context(copy=True)).copy(default)

    @api.model
    def default_get(self, fields_list):
        """Invert name when getting default values."""
        result = super(ResPartner, self).default_get(fields_list)

        inverted = self._get_inverse_name(
            self._get_whitespace_cleaned_name(result.get("name", "")),
            result.get("is_company", False))

        for field in inverted.keys():
            if field in fields_list:
                result[field] = inverted.get(field)

        return result

    @api.model
    def _names_order_default(self):
        return 'last_first'

    @api.model
    def _get_names_order(self):
        """Get names order configuration from system parameters.

        You can override this method to read configuration from language,
        country, company or other
        """
        return self.env['ir.config_parameter'].get_param(
            'partner_names_order', self._names_order_default())

    @api.one
    def _inverse_name_after_cleaning_whitespace(self):
        """Clean whitespace in :attr:`~.name` and split it.

        The splitting logic is stored separately in :meth:`~._inverse_name`, so
        submodules can extend that method and get whitespace cleaning for free.
        """
        # Remove unneeded whitespace
        clean = self._get_whitespace_cleaned_name(self.name)

        # Clean name avoiding infinite recursion
        if self.name != clean:
            self.name = clean

        # Save name in the real fields
        else:
            self._inverse_name()

    @api.model
    def _get_whitespace_cleaned_name(self, name, comma=False):
        """Remove redundant whitespace from :param:`name`.

        Removes leading, trailing and duplicated whitespace.
        """
        if name:
            name = u" ".join(name.split(None))
            if comma:
                name = name.replace(" ,", ",")
                name = name.replace(", ", ",")
        return name

    @api.model
    def _get_inverse_name(self, name, is_company=False):
        """Compute the inverted name.

        - If the partner is a company, save it in the lastname.
        - Otherwise, make a guess.

        This method can be easily overriden by other submodules.
        You can also override this method to change the order of name's
        attributes

        When this method is called, :attr:`~.name` already has unified and
        trimmed whitespace.
        """
        # Company name goes to the lastname
        if is_company or not name:
            parts = [name or False, False]
        # Guess name splitting
        else:
            order = self._get_names_order()
            # Remove redundant spaces
            name = self._get_whitespace_cleaned_name(
                name, comma=(order == 'last_first_comma'))
            parts = name.split("," if order == 'last_first_comma' else " ", 1)
            if len(parts) > 1:
                if order == 'first_last':
                    parts = [u" ".join(parts[1:]), parts[0]]
                else:
                    parts = [parts[0], u" ".join(parts[1:])]
            else:
                while len(parts) < 2:
                    parts.append(False)
        return {"name": name, "lastname": parts[0], "firstname": parts[1]}

    @api.one
    def _inverse_name(self):
        """Try to revert the effect of :meth:`._compute_name`."""
        parts = self._get_inverse_name(self.name, self.is_company)
        if parts["lastname"] != self.lastname:
            self.lastname = parts["lastname"]
        if parts["firstname"] != self.firstname:
            self.firstname = parts["firstname"]

    @api.model
    def _install_partner_firstname(self):
        """Save names correctly in the database.

        Before installing the module, field ``name`` contains all full names.
        When installing it, this method parses those names and saves them
        correctly into the database. This can be called later too if needed.
        """
        # Find records with empty firstname and lastname
        records = self.search([("firstname", "=", False),
                               ("lastname", "=", False)])

        # Force calculations there
        records._inverse_name()
        _logger.info("%d partners updated installing module.", len(records))

