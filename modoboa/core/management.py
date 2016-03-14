# coding: utf-8

from django.conf import settings
from django.template import Context, Template
import argparse
import os
import sys

class Command(object):
    """Base command class

    A valid administrative command must inherit from this class.
    """
    help = "No help available."

    def __init__(self, commands, verbose=False, **kwargs):
        self._commands = commands
        self._parser = argparse.ArgumentParser()
        self._verbose = verbose
        if not settings.configured:
            settings.configure()
        self._templates_dir = "%s/templates" % os.path.dirname(__file__)

    def _render_template(self, tplfile, env):
        fp = open(tplfile)
        t = Template(fp.read())
        fp.close()
        return t.render(Context(env))

    def run(self, cmdline):
        args = self._parser.parse_args(cmdline)
        self.handle(args)

    def handle(self, parsed_args):
        """A command must overload this method to be called

        :param parsed_args:
        """
        raise NotImplemented

def scan_for_commands(dirname="commands"):
    """Build a dictionnary containing all commands

    :param dirname: the directory where commands are located
    :return: a dict of commands (name : class)
    """
    path = os.path.join(os.path.dirname(__file__), dirname)
    result = {}
    for f in os.listdir(path):
        if f in ['.', '..', '__init__.py']:
            continue
        if not f.endswith('.py'):
            continue
        if os.path.isfile(f):
            continue
        cmdname = f.replace('.py', '')
        cmdmod = __import__("modoboa.core.commands", globals(), locals(),
                            [cmdname])
        cmdmod = getattr(cmdmod, cmdname)
        if '_' in cmdname:
            cmdclassname = ''.join(map(lambda s: s.capitalize(), cmdname.split('_')))
        else:
            cmdclassname = cmdname.capitalize()
        try:
            cmdclass = getattr(cmdmod, "%sCommand" % cmdclassname)
        except AttributeError:
            continue
        result[cmdname] = cmdclass
    return result

def handle_command_line():
    commands = scan_for_commands()
    parser = argparse.ArgumentParser(
        description="A set of utilities to ease the installation of Modoboa.",
        epilog="""Available commands:
%s
""" % "\n".join(map(lambda c: "\t" + c, sorted(commands))))
    parser.add_argument('--verbose', action='store_true',
                        help='Activate verbose output')
    parser.add_argument('command', type=str,
                        help='A valid command name')
    (args, remaining) = parser.parse_known_args()

    if not args.command in commands:
        print >>sys.stderr, "Unknown command '%s'" % args.command
        sys.exit(1)

    commands[args.command](commands, verbose=args.verbose).run(remaining)
