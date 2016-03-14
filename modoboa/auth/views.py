# coding: utf-8
import logging
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from modoboa.lib import events, parameters
from modoboa.lib.webutils import _render_to_string
from forms import LoginForm
from modoboa.auth.lib import encrypt


def dologin(request):
    error = None
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            logger = logging.getLogger('modoboa.auth')
            user = authenticate(username=form.cleaned_data["username"],
                                password=form.cleaned_data["password"])
            if user and user.is_active:
                login(request, user)
                if not form.cleaned_data["rememberme"]:
                    request.session.set_expiry(0)
                if request.user.has_mailbox:
                    request.session["password"] = encrypt(form.cleaned_data["password"])

                request.session["django_language"] = \
                    parameters.get_user(request.user, "LANG", app="general")

                logger.info(_("User '%s' successfully logged in" % user.username))
                events.raiseEvent("UserLogin", request,
                                  form.cleaned_data["username"],
                                  form.cleaned_data["password"])

                nextlocation = request.POST.get("next", None)
                if nextlocation is None or nextlocation == "None":
                    if user.group != "SimpleUsers":
                        nextlocation = reverse("modoboa.lib.webutils.topredirection")
                    else:
                        nextlocation = reverse("domains")
                return HttpResponseRedirect(nextlocation)
            error = _("Your username and password didn't match. Please try again.")
            logger.warning("Failed connection attempt from '%(addr)s' as user '%(user)s'" \
                               % {"addr": request.META["REMOTE_ADDR"],
                                  "user": form.cleaned_data["username"]})

        nextlocation = request.POST.get("next", None)
        httpcode = 401
    else:
        form = LoginForm()
        nextlocation = request.GET.get("next", None)
        httpcode = 200

    return HttpResponse(_render_to_string(request, "registration/login.html", {
        "form": form, "error": error, "next": nextlocation,
        "annoucements": events.raiseQueryEvent("GetAnnouncement", "loginpage")
    }), status=httpcode)

dologin = never_cache(dologin)


def dologout(request):
    events.raiseEvent("UserLogout", request)
    logger = logging.getLogger("modoboa.auth")
    logger.info(_("User '%s' logged out" % request.user.username))
    logout(request)
    return HttpResponseRedirect(reverse(dologin))
