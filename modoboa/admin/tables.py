# coding: utf-8
from django.utils.translation import ugettext as _, ugettext_lazy
from modoboa.lib import tables
from templatetags.admin_extras import *

class DomainsTable(tables.Table):
    tableid = "objects_table"
    idkey = "id"
    styles = "table"

    name = tables.LinkColumn(
        "name", label=ugettext_lazy("Name"), 
        urlpattern="modoboa.admin.views.editdomain",
        title=_("Edit domain"), modal=True, modalcb="admin.domainform_cb",
        sortable=True, sort_order="name"
    )
    domaliases = tables.Column(
        "domainalias_set", label=ugettext_lazy("Alias(es)"), safe=True,
        sortable=True, sort_order="domainalias__name"
    )
    actions = tables.ActionColumn("actions", label=ugettext_lazy("Actions"), 
                                  defvalue=domain_actions)

    cols_order = ["name", "domaliases", "actions"]

    def __init__(self, request, doms):
        super(DomainsTable, self).__init__(request)
        self.populate(self._rows_from_model(doms))


    def parse_domainalias_set(self, aliases):
        if not len(aliases.all()):
            return "---"
        res = ""
        for da in aliases.all():
            res += "%s<br/>" % da.name
        return res

    def row_class(self, request, domain):
        if not domain.enabled:
            return "muted"
        return ""

class ExtensionsTable(tables.Table):
    idkey = "id"
    selection = tables.SelectionColumn("selection", width="4%", header=False)
    label = tables.Column("label", label=ugettext_lazy("Name"), width="15%")
    version = tables.Column("version", label=ugettext_lazy("Version"), width="6%")
    descr = tables.Column("description", label=ugettext_lazy("Description"))
    
    cols_order = ["selection", "label", "version", "descr"]
