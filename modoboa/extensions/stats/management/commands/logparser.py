#!/usr/bin/env python
# coding: utf-8
"""
Postfix log parser.

This scripts parses a log file produced by postfix (or using the same
format). It looks for predefined events and build statistics about
their occurence rate.

At the, somes default graphics are generated using the grapher module.
(see grapher.py)

Predefined events are:
 * Per domain sent/received messages,
 * Per domain received bad messages (bounced, reject for now),
 * Per domain sent/received traffics size,
 * Global consolidation of all previous events.

"""
import time
import sys
import os
import re
import rrdtool
import string
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from modoboa.lib import parameters
from modoboa.admin.models import Domain
from modoboa.extensions.stats import Stats
from modoboa.extensions.stats.grapher import *
from modoboa.extensions.stats.graph_templates import MailTraffic

rrdstep = 60
xpoints = 540
points_per_sample = 3
variables = ["sent", "recv", "bounced", "reject", "spam", "virus",
             "size_sent", "size_recv"]

class LogParser(object):
    def __init__(self, options, workdir, year=None):
        self.logfile = options["logfile"]
        try:
            self.f = open(self.logfile)
        except IOError, errno:
            if options["debug"]:
                print "%s" % errno
            sys.exit(1)
        self.workdir = workdir
        self.__year = year
        self.debug = options["debug"]
        self.verbose = options["verbose"]
        self.cfs = ['AVERAGE', 'MAX']

        curtime = time.localtime()
        if not self.__year:
            self.__year = curtime.tm_year
        self.curmonth = curtime.tm_mon

        self.data = {}
        domains = Domain.objects.all()
        self.domains = []
        for dom in domains:
            self.domains += [str(dom.name)]
            self.data[str(dom.name)] = {}
        self.data["global"] = {}

        self.workdict = {}
        self.lupdates = {}
        self.line_expr = re.compile("(\w+)\s+(\d+)\s+(\d+):(\d+):(\d+)\s+([-\w]+)\s+(\w+)/?\w*[[](\d+)[]]:\s+(.*)")

    def init_rrd(self, fname, m):
        """init_rrd

        Set-up Data Sources (DS)
        Set-up Round Robin Archives (RRA):
        - day,week,month and year archives
        - 2 types : AVERAGE and MAX

        parameter : start time
        return    : last epoch recorded
        """
        ds_type = 'ABSOLUTE'
        rows = xpoints / points_per_sample
        realrows = int(rows * 1.1)    # ensure that the full range is covered
        day_steps = int(3600 * 24 / (rrdstep * rows))
        week_steps = day_steps * 7
        month_steps = week_steps * 5
        year_steps = month_steps * 12

        # Set up data sources for our RRD
        params = []
        for v in variables:
            params += ['DS:%s:%s:%s:0:U' % (v, ds_type, rrdstep * 2)]

        # Set up RRD to archive data
        rras = []
        for cf in ['AVERAGE', 'MAX']:
            for step in [day_steps, week_steps, month_steps, year_steps]:
                params += ['RRA:%s:0.5:%s:%s' % (cf, step, realrows)]

        # With those setup, we can now created the RRD
        rrdtool.create(str(fname),
                       '--start', str(m),
                       '--step', str(rrdstep),
                       *params)
        return m

    def update_rrd(self, dom, t):
        """update_rrd

        Update RRD with records at t time.

        True  : if data are up-to-date for current minute
        False : syslog may have probably been already recorded
        or something wrong
        """
        fname = "%s/%s.rrd" % (self.workdir, dom)
        m = t - (t % rrdstep)
        if not os.path.exists(fname):
            self.lupdates[fname] = self.init_rrd(fname, m)
            if self.debug:
                print "[rrd] create new RRD file %s" %fname
        else:
            if not self.lupdates.has_key(fname):
                self.lupdates[fname] = rrdtool.last(str(fname))

        if m <= self.lupdates[fname]:
            if self.verbose:
                print "[rrd] VERBOSE events at %s already recorded in RRD" %m
            return False

        tpl = ""
        for v in variables:
            if tpl != "":
                tpl += ":"
            tpl += v
        # Missing some RRD steps
        # Est ce vraiment nécessaire... ?
        if m > self.lupdates[fname] + rrdstep:
            values = ""
            for v in variables:
                if values != "": values += ":"
                values += "0"
            for p in range(self.lupdates[fname] + rrdstep, m, rrdstep):
                if self.verbose:
                    print "[rrd] VERBOSE update -t %s %s:%s (SKIP)" \
                        % (tpl, p, values)
                rrdtool.update(str(fname), "-t", tpl, "%s:%s" % (p, values))

        values = "%s" % m
        tpl = ""
        for v in variables:
            values += ":"
            values += str(self.data[dom][m][v])
            if tpl != "":
                tpl += ":"
            tpl += v
        if self.verbose:
            print "[rrd] VERBOSE update -t %s %s" % (tpl, values)

        rrdtool.update(str(fname), "-t", tpl, values)
        self.lupdates[fname] = m
        return True

    def initcounters(self, dom, cur_t):
        init = {}
        for v in variables: init[v] = 0
        self.data[dom][cur_t] = init

    def inc_counter(self, dom, cur_t, counter, val=1):
        if dom is not None and dom in self.domains:
            if not self.data[dom].has_key(cur_t):
                self.initcounters(dom, cur_t)
            self.data[dom][cur_t][counter] += val

        if not self.data["global"].has_key(cur_t):
            self.initcounters("global", cur_t)
        self.data["global"][cur_t][counter] += val

    def year(self, month):
        """Return the appropriate year

        Date used in log files don't always embark the year so we need
        to guess it :p

        This method tries to deal with year changes in a simply
        (ugly?) way: if we currently are in january and the given
        month is different, return the current year -1. Otherwise,
        return the current year.

        Obviously, this method only works for year to year + 1
        changes.

        :param month: the month of the current record beeing parsed
        :return: an integer
        """
        month = time.strptime(month, "%b").tm_mon if not month.isdigit() \
            else int(month)
        if self.curmonth == 1 and month != self.curmonth:
            return self.__year - 1
        return self.__year

    def process(self):
        id_expr = re.compile("([0-9A-F]+): (.*)")
        prev_se = -1
        prev_mi = -1
        prev_ho = -1
        for line in self.f.readlines():
            m = self.line_expr.match(line)
            if not m:
                continue
            (mo, da, ho, mi, se, host, prog, pid, log) = m.groups()
            se = int(int(se) / rrdstep)            # rrd step is one-minute => se = 0

            if prev_se != se or prev_mi != mi or prev_ho != ho:
                cur_t = str2Time(self.year(mo), mo, da, ho, mi, se)
                cur_t = cur_t - cur_t % rrdstep
                prev_mi = mi
                prev_ho = ho
                prev_se = se
            m = id_expr.match(log)
            if m:
                (line_id, line_log) = m.groups()

                m = re.search("message-id=<([^>]*)>", line_log)
                if m:
                    self.workdict[line_id] = {'from' : m.group(1), 'size' : 0}
                    continue

                m = re.search("from=<([^>]*)>, size=(\d+)", line_log)
                if m:
                    self.workdict[line_id] = {'from' : m.group(1),
                                             'size' : string.atoi(m.group(2))}
                    continue

                m = re.search("to=<([^>]*)>.*status=(\S+)", line_log)
                if m:
                    if not self.workdict.has_key(line_id):
                        if self.debug:
                            print "Inconsistent mail (%s: %s), skipping" % (line_id, m.group(1))
                        continue
                    if not m.group(2) in variables:
                        if self.debug:
                            print "Unsupported status %s, skipping" % m.group(2)
                        continue

                    addrfrom = re.match("([^@]+)@(.+)", self.workdict[line_id]['from'])
                    if addrfrom is not None and addrfrom.group(2) in self.domains:
                        self.inc_counter(addrfrom.group(2), cur_t, 'sent')
                        self.inc_counter(addrfrom.group(2), cur_t, 'size_sent',
                                         self.workdict[line_id]['size'])
                    addrto = re.match("([^@]+)@(.+)", m.group(1))
                    domname = addrto.group(2) if addrto is not None else None
                    if m.group(2) == "sent":
                        self.inc_counter(addrto.group(2), cur_t, 'recv')
                        self.inc_counter(addrto.group(2), cur_t, 'size_recv',
                                         self.workdict[line_id]['size'])
                    else:
                        self.inc_counter(domname, cur_t, m.group(2))
                    continue

                if self.debug:
                    print "Unknown line format: %s" % line_log
            else:
                m = re.match("NOQUEUE: reject: .*from=<(.*)> to=<([^>]*)>", log)
                if m:
                    addrto = re.match("([^@]+)@(.+)", m.group(2))
                    if addrto and addrto.group(2) in self.domains:
                        self.inc_counter(addrto.group(2), cur_t, 'reject')
                    continue
                if self.debug:
                    print "Unknown line format: %s" % log

        # Sort everything by time
        G = Grapher()
        for dom, data in self.data.iteritems():
            if self.debug:
                print "[rrd] dealing with domain %s" %dom
            for t in sorted(data.keys()):
                self.update_rrd(dom, t)

            for graph_tpl in MailTraffic().get_graphs():
                G.make_defaults(dom, graph_tpl)

class Command(BaseCommand):
    help = 'Log file parser'

    option_list = BaseCommand.option_list + (
        make_option("--logfile", default=None,
                    help="postfix log in syslog format", metavar="FILE"),
        make_option("--verbose", default=False, action="store_true",
                    dest="verbose", help="Set verbose mode"),
        make_option("--debug", default=False, action="store_true",
                    help="Set debug mode")
        )

    def handle(self, *args, **options):
        Stats().load()
        if options["logfile"] is None:
            options["logfile"] = parameters.get_admin("LOGFILE", app="stats")
        p = LogParser(options, parameters.get_admin("RRD_ROOTDIR", app="stats"))
        p.process()
