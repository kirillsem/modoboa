# coding: utf-8

from datetime import datetime
from django.utils.translation import ugettext as _, ugettext_lazy
from django.db.models import Q
from modoboa.lib import tables
from modoboa.lib.webutils import static_url
from modoboa.lib.email_listing import MBconnector, EmailListing
from modoboa.lib.emailutils import *
from modoboa.lib.dbutils import db_type
from models import *


class Qtable(tables.Table):
    tableid = "emails"
    styles = "table-condensed"
    idkey = "mailid"

    type = tables.Column(
        "type", align="center", width="30px",
    )
    rstatus = tables.ImgColumn("rstatus", width='25px')
    from_ = tables.Column("from", label=ugettext_lazy("From"), limit=30)
    subject = tables.Column("subject", label=ugettext_lazy("Subject"), limit=40)
    time = tables.Column("date", label=ugettext_lazy("Date"))
    to = tables.Column("to", label=ugettext_lazy("To"), sortable=False)

    cols_order = []

    def parse_date(self, value):
        return datetime.fromtimestamp(value)


class SQLconnector(MBconnector):
    orders = {
        "from": "mail__from_addr",
        "subject": "mail__subject",
        "date": "mail__time_num"
        }

    def __init__(self, mail_ids=None, filter=None):
        self.count = None
        self.mail_ids = mail_ids
        self.filter = filter

    def messages_count(self, **kwargs):
        if self.count is None:
            filter = Q(chunk_ind=1)
            if self.mail_ids is not None:
                filter &= Q(mail__in=self.mail_ids)
            if self.filter:
                filter &= self.filter
            self.messages = Quarantine.objects.filter(filter)
            if "order" in kwargs:
                totranslate = kwargs["order"][1:]
                sign = kwargs["order"][:1]
                if sign == " ":
                    sign = ""
                order = sign + self.orders[totranslate]
                self.messages = self.messages.order_by(order)
            self.count = self.messages.count()
        return self.count

    def fetch(self, start=None, stop=None, **kwargs):
        messages = self.messages[start - 1:stop]
        emails = []
        for qm in messages:
            for rcpt in qm.mail.msgrcpt_set.all():
                m = {"from": qm.mail.from_addr,
                     "to": rcpt.rid.email,
                     "subject": qm.mail.subject,
                     "mailid": qm.mail_id,
                     "date": qm.mail.time_num,
                     "type": rcpt.content}
                if rcpt.rs == '':
                    m["class"] = "unseen"
                elif rcpt.rs == 'R':
                    m["img_rstatus"] = static_url("pics/release.png")
                elif rcpt.rs == 'p':
                    m["class"] = "pending"
                emails.append(m)
        return emails


class SQLWrapper(object):
    """A simple SQL wrapper.

    This wrapper has been added just to answer the *Postgres bytea
    fields* issue :p

    The base class doesn't add anything special but defines the method
    (and so piece of SQL queries) that should be overloaded when
    Postgres is in use.

    See ``PgWrapper`` for the real mess...
    """

    def get_mails(self, request, rcptfilter=None):
        if request.GET.get("viewrequests", None) == "1":
            q = Q(rs='p')
        else:
            q = ~Q(rs='D')

        if request.user.group == 'SimpleUsers':
            q &= Q(rid__email=request.user.email)
        else:
            if not request.user.is_superuser:
                doms = request.user.get_domains()
                regexp = "(%s)" % '|'.join(map(lambda dom: dom.name, doms))
                doms_q = Q(rid__email__regex=regexp)
                q &= doms_q
            if rcptfilter is not None:
                q &= Q(rid__email__contains=rcptfilter)

        return Msgrcpt.objects.filter(q).values("mail_id")

    def get_recipient_message(self, address, mailid):
        return Msgrcpt.objects.get(mail=mailid, rid__email=address)

    def get_recipient_messages(self, address, mailids):
        return Msgrcpt.objects.filter(mail__in=mailids, rid__email=address)

    def get_domains_pending_requests(self, domains):
        regexp = "(%s)" % '|'.join(map(lambda dom: dom.name, domains))
        return Msgrcpt.objects.filter(rs='p', rid__email__regex=regexp)

    def get_pending_requests(self, user):
        """Return the number of current pending requests

        :param user: a ``User`` instance
        """
        rq = Q(rs='p')
        if not user.is_superuser:
            doms = user.get_domains()
            if not doms.count():
                return 0
            regexp = "(%s)" % '|'.join(map(lambda dom: dom.name, doms))
            doms_q = Q(rid__email__regex=regexp)
            rq &= doms_q
        return Msgrcpt.objects.filter(rq).count()

    def get_mail_content(self, mailid):
        return Quarantine.objects.filter(mail=mailid)


class PgWrapper(SQLWrapper):
    """The postgres wrapper

    Make use of ``QuerySet.extra`` and postgres ``convert_from``
    function to let the quarantine manager work as expected !
    """

    def get_mails(self, request, rcptfilter=None):
        if request.GET.get("viewrequests", None) == "1":
            q = Q(rs='p')
        else:
            q = ~Q(rs='D')
        where = ["U0.rid=maddr.id"]
        if request.user.group == 'SimpleUsers':
            where.append("convert_from(maddr.email, 'UTF8') = '%s'" % request.user.email)
            return Msgrcpt.objects.filter(q).extra(
                where=where, tables=['maddr']
                )

        if not request.user.is_superuser:
            doms = request.user.get_domains()
            regexp = "(%s)" % '|'.join(map(lambda dom: dom.name, doms))
            where.append("convert_from(maddr.email, 'UTF8') ~ '%s'" % regexp)
        if rcptfilter is not None:
            where.append("convert_from(maddr.email, 'UTF8') LIKE '%%%s%%'" % rcptfilter)
        return Msgrcpt.objects.filter(q).extra(where=where, tables=['maddr']).values("mail_id")

    def get_recipient_message(self, address, mailid):
        qset = Msgrcpt.objects.filter(mail=mailid).extra(
            where=["msgrcpt.rid=maddr.id", "convert_from(maddr.email, 'UTF8') = '%s'" % address],
            tables=['maddr']
            )
        return qset.all()[0]

    def get_recipient_messages(self, address, mailids):
        return Msgrcpt.objects.filter(mail__in=mailids).extra(
            where=["U0.rid=maddr.id", "convert_from(maddr.email, 'UTF8') = '%s'" % address],
            tables=['maddr']
            )

    def get_domains_pending_requests(self, domains):
        regexp = "(%s)" % '|'.join(map(lambda dom: dom.name, domains))
        return Msgrcpt.objects.filter(rs='p').extra(
            where=["msgrcpt.rid=maddr.id", "convert_from(maddr.email, 'UTF8') ~ '%s'" % regexp],
            tables=['maddr']
            )

    def get_pending_requests(self, user):
        rq = Q(rs='p')
        if not user.is_superuser:
            doms = user.get_domains()
            if not doms.count():
                return 0
            regexp = "(%s)" % '|'.join(map(lambda dom: dom.name, doms))
            return Msgrcpt.objects.filter(rq).extra(
                where=["msgrcpt.rid=maddr.id", "convert_from(maddr.email, 'UTF8') ~ '%s'" % (regexp,)],
                tables=['maddr']
                ).count()
        return len(Msgrcpt.objects.filter(rq))

    def get_mail_content(self, mailid):
        return Quarantine.objects.filter(mail=mailid).extra(
            select={'mail_text': "convert_from(mail_text, 'UTF8')"}
            )


def get_wrapper():
    """Return the appropriate *Wrapper class

    The result depends on the DB engine in use.
    """
    if db_type("amavis") == 'postgres':
        return PgWrapper()
    return SQLWrapper()


class SQLlisting(EmailListing):
    tpl = "amavis/index.html"
    tbltype = Qtable
    deflocation = "listing/"
    defcallback = "updatelisting"
    reset_wm_url = True

    def __init__(self, user, msgs, filter, **kwargs):
        if user.group == 'SimpleUsers':
            Qtable.cols_order = ['type', 'rstatus', 'from_', 'subject', 'time']
        else:
            Qtable.cols_order = ['type', 'rstatus', 'to', 'from_', 'subject', 'time']
        self.mbc = SQLconnector(msgs, filter)
        super(SQLlisting, self).__init__(**kwargs)
        self.show_listing_headers = True


class SQLemail(Email):
    def __init__(self, msg, *args, **kwargs):
        super(SQLemail, self).__init__(msg, *args, **kwargs)
        fields = ["From", "To", "Cc", "Date", "Subject"]
        for f in fields:
            label = f
            self.headers += [{"name": label, "value": self.get_header(msg, f)}]
            try:
                label = re.sub("-", "_", label)
                setattr(self, label, msg[f])
            except:
                pass
        qreason = self.get_header(msg, "X-Amavis-Alert")
        self.qtype = ""
        self.qreason = ""
        if qreason != "":
            if ',' in qreason:
                self.qtype, self.qreason = qreason.split(',', 1)
            elif qreason.startswith("BAD HEADER SECTION "):
                # Workaround for amavis <= 2.8.0 :p
                self.qtype = "BAD HEADER SECTION"
                self.qreason = qreason[19:]

    def get_header(self, msg, name):
        for k in [name, name.upper()]:
            if k in msg:
                return msg[k]
        return ""

    def render_headers(self, **kwargs):
        return render_to_string("amavis/mailheaders.html", {
                "qtype": self.qtype, "qreason": self.qreason,
                "headers": self.headers,
                })
