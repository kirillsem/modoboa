# coding: utf-8
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.translation import ugettext as _
from modoboa.lib import parameters, events
from modoboa.lib.decorators import needs_mailbox
from modoboa.lib.exceptions import ModoboaException
from modoboa.lib.webutils import (
    ajax_response, ajax_simple_response, _render_to_string
)
from modoboa.admin.models import Mailbox, Alias
from modoboa.auth.lib import encrypt
from forms import ForwardForm, BadDestination, ProfileForm


@login_required
def index(request, tplname="userprefs/index.html"):
    extrajs = events.raiseQueryEvent("ExtraUprefsJS", request.user)
    return render(request, tplname, {
        "selection": "user",
        "extrajs": "".join(extrajs)
    })


@login_required
@needs_mailbox()
def forward(request, tplname='userprefs/forward.html'):
    try:
        mb = request.user.mailbox_set.all()[0]
    except IndexError:
        raise ModoboaException(
            _("You need a mailbox in order to define a forward")
        )
    try:
        al = Alias.objects.get(address=mb.address,
                               domain__name=mb.domain.name)
    except Alias.DoesNotExist:
        al = None
    if request.method == "POST":
        form = ForwardForm(request.POST)
        error = None
        if form.is_valid():
            try:
                if al is None:
                    al = Alias()
                    al.address = mb.address
                    al.domain = mb.domain
                    al.enabled = mb.user.is_active
                intdests = []
                if form.cleaned_data["keepcopies"]:
                    intdests += [mb]
                form.parse_dest()
                al.save(intdests, form.dests)
                if request.user.group != "SimpleUsers":
                    al.post_create(request.user)
                return ajax_response(request, respmsg=_("Forward updated"))
            except BadDestination, e:
                error = str(e)

        return ajax_simple_response(dict(
            status="ko",
            errors=form.errors,
            respmsg=error
        ))

    form = ForwardForm()
    if al is not None:
        form.fields["dest"].initial = al.extmboxes
        try:
            selfmb = al.mboxes.get(pk=mb.id)
        except Mailbox.DoesNotExist:
            pass
        else:
            form.fields["keepcopies"].initial = True
    return ajax_simple_response({
        "status": "ok",
        "content": _render_to_string(request, tplname, {
            "form": form
        })
    })


@login_required
def profile(request, tplname='userprefs/profile.html'):
    update_password = True
    if True in events.raiseQueryEvent("PasswordChange", request.user):
        update_password = False

    if request.method == "POST":
        form = ProfileForm(
            update_password, request.POST, instance=request.user
        )
        if form.is_valid():
            form.save()
            if update_password and form.cleaned_data["confirmation"] != "":
                request.session["password"] = encrypt(form.cleaned_data["confirmation"])
            return ajax_simple_response(dict(
                status="ok", respmsg=_("Profile updated")
            ))
        return ajax_simple_response({
            "status": "ko",
            "errors": form.errors
        })

    form = ProfileForm(update_password, instance=request.user)
    return ajax_simple_response({
        "status": "ok",
        "content": _render_to_string(request, tplname, {
            "form": form
        })
    })


@login_required
def preferences(request):
    if request.method == "POST":
        for formdef in parameters.get_user_forms(request.user, request.POST)():
            form = formdef["form"]
            if form.is_valid():
                form.save()
                continue
            return ajax_simple_response({
                "status": "ko", "prefix": form.app, "errors": form.errors
            })

        return ajax_simple_response({
            "status": "ok", "respmsg": _("Preferences saved")
        })

    return ajax_simple_response({
        "status": "ok",
        "content": _render_to_string(request, "userprefs/preferences.html", {
            "forms": parameters.get_user_forms(request.user)
        })
    })
