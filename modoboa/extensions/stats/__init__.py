# coding: utf-8

"""
Graphical statistics about emails traffic using RRDtool

This module provides support to retrieve statistics from postfix log :
sent, received, bounced, rejected

"""
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _, ugettext_lazy
from modoboa.lib import events, parameters
from modoboa.extensions import ModoExtension, exts_pool


class Stats(ModoExtension):
    name = "stats"
    label = "Statistics"
    version = "1.0"
    description = ugettext_lazy("Graphical statistics about emails traffic using RRDtool")
    needs_media = True

    def load(self):
        from app_settings import ParametersForm
        events.registerEvent("GetGraphSets")
        parameters.register(ParametersForm, ugettext_lazy("Graphical statistics"))

    def destroy(self):
        events.unregister("AdminMenuDisplay", menu)

exts_pool.register_extension(Stats)


@events.observe("UserMenuDisplay")
def menu(target, user):
    if target != "top_menu" or user.group == "SimpleUsers":
        return []
    return [
        {"name": "stats",
         "label": _("Statistics"),
         "url": reverse('fullindex')}
    ]


@events.observe("GetGraphSets")
def get_default_graph_sets():
    from graph_templates import MailTraffic

    gset = MailTraffic()
    return {gset.html_id: gset}
