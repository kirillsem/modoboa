# coding: utf-8
"""
Postfix auto-replies plugin.

This module provides a way to integrate Modoboa auto-reply
functionality into Postfix.

"""
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _, ugettext_lazy
from modoboa.lib import events, parameters
from modoboa.extensions import ModoExtension, exts_pool
from models import *


class PostfixAutoreply(ModoExtension):
    name = "postfix_autoreply"
    label = "Postfix autoreply"
    version = "1.0"
    description = ugettext_lazy("Auto-reply (vacation) functionality using Postfix")

    def init(self):
        from modoboa.admin.models import Domain

        for dom in Domain.objects.all():
            try:
                trans = Transport.objects.get(domain="autoreply.%s" % dom.name)
            except Transport.DoesNotExist:
                onCreateDomain(None, dom)
            else:
                continue

            for mb in dom.mailbox_set.all():
                try:
                    alias = Alias.objects.get(full_address=mb.full_address)
                except Alias.DoesNotExist:
                    onCreateMailbox(None, mb)

    def load(self):
        from app_settings import ParametersForm
        parameters.register(ParametersForm, ugettext_lazy("Automatic replies"))

    def destroy(self):
        events.unregister("CreateDomain", onCreateDomain)
        events.unregister("DeleteDomain", onDeleteDomain)
        events.unregister("CreateMailbox", onCreateMailbox)
        events.unregister("DeleteMailbox", onDeleteMailbox)
        events.unregister("ModifyMailbox", onModifyMailbox)
        events.unregister("UserMenuDisplay", menu)
        parameters.unregister()

exts_pool.register_extension(PostfixAutoreply)


@events.observe("ExtraUprefsRoutes")
def extra_routes():
    return [(r'^autoreply/$', 'modoboa.extensions.postfix_autoreply.views.autoreply'),]


@events.observe("ExtraUprefsJS")
def extra_js(user):
    return ["""function autoreply_cb() {
    $('#id_untildate').datepicker({format: 'yyyy-mm-dd', language: '%s'});
}
""" % parameters.get_user(user, "LANG", app="general")
    ]


@events.observe("UserMenuDisplay")
def menu(target, user):
    if target != "uprefs_menu":
        return []
    if not user.has_mailbox:
        return []
    return [
        {"name": "autoreply",
         "class": "ajaxlink",
         "url": "autoreply/",
         "label": ugettext_lazy("Auto-reply message")}
    ]


@events.observe("CreateDomain")
def onCreateDomain(user, domain):
    transport = Transport()
    transport.domain = "autoreply.%s" % domain.name
    transport.method = "autoreply:"
    transport.save()


@events.observe("DeleteDomain")
def onDeleteDomain(domain):
    trans = Transport.objects.get(domain="autoreply.%s" % domain.name)
    trans.delete()


@events.observe("CreateMailbox")
def onCreateMailbox(user, mailbox):
    alias = Alias()
    alias.full_address = mailbox.full_address
    alias.autoreply_address = \
        "%s@autoreply.%s" % (mailbox.full_address, mailbox.domain.name)
    alias.save()


@events.observe("DeleteMailbox")
def onDeleteMailbox(mailboxes):
    from modoboa.admin.models import Mailbox

    if isinstance(mailboxes, Mailbox):
        mailboxes = [mailboxes]
    for mailbox in mailboxes:
        try:
            alias = Alias.objects.get(full_address=mailbox.full_address)
        except Alias.DoesNotExist:
            pass
        else:
            alias.delete()


@events.observe("ModifyMailbox")
def onModifyMailbox(mailbox, oldmailbox):
    if oldmailbox.full_address == mailbox.full_address:
        return
    alias = Alias.objects.get(full_address=oldmailbox.full_address)
    alias.full_address = mailbox.full_address
    alias.autoreply_address =  \
        "%s@autoreply.%s" % (mailbox.full_address, mailbox.domain.name)
    alias.save()
