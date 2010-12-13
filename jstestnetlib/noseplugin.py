
import logging
import os
import unittest

from nose.plugins import Plugin

from jstestnetlib.control import Connection

log = logging.getLogger('nose.plugins.jstests')

class JSTests(Plugin):
    """Run JavaScript tests using a JS TestNet server."""
    name = 'jstests'

    def options(self, parser, env=os.environ):
        super(JSTests, self).options(parser, env=env)
        parser.add_option('--jstests-server', action="store",
                          help='http://jstestnet-server/')
        parser.add_option('--jstests-suite', action="store",
                          help='Name of test suite to run')
        self.parser = parser

    def configure(self, options, conf):
        super(JSTests, self).configure(options, conf)
        if not self.enabled:
            return
        self.options = options
        if not self.options.jstests_server:
            self.parser.error("Missing --jstests-server")
        if not self.options.jstests_suite:
            self.parser.error("Missing --jstests-suite")
        self.started = False
        self.conn = Connection(self.options.jstests_server)

    def loadTestsFromDir(self, directory):
        if self.started:
            # hijacking loadTestsFromDir to run tests once
            # and only once.
            return
        self.started = True
        log.debug('Starting %r [%s]' % (self.options.jstests_suite,
                                        self.options.jstests_server))

        tests = self.conn.run_tests(self.options.jstests_suite)
        for result in tests['results']:
            for test in result['results']['tests']:
                yield JSTestCase(result['worker_id'], test)
                # TODO(Kumar) check stop_on_error for nosetests -x


class JSTestError(Exception):
    pass


class JSTestCase(unittest.TestCase):
    """A test case that represents a remote test known by the server."""
    __test__ = False # this is not a collectible test

    def __init__(self, worker_id, test):
        self.worker_id = worker_id
        self.test = test
        super(JSTestCase, self).__init__()

    def runTest(self):
        pass

    def run(self, result):
        result.startTest(self)
        try:
            passed = True
            # Since unittest does not log assertions,
            # iterate until the first failure (if there is one).
            for assertion in self.test['assertions']:
                if not assertion['result']:
                    passed = False
                    # log.debug(repr(self.test))
                    msg = assertion['message'] or '<unknown error>'
                    traceback = None # Python
                    e = (JSTestError, "%s %s" % (
                         msg, assertion['stacktrace'] or ''), traceback)
                    result.addError(self, e)
                    break
            if passed:
                result.addSuccess(self)
        finally:
            result.stopTest(self)

    def address(self):
        return (self.id(), None, None)

    def id(self):
        return repr(self)

    def shortDescription(self):
        return "%r %s: %s" % (self, self.test['module'], self.test['test'])

    def __repr__(self):
        return "JSTest [worker=%s]" % self.worker_id

    __str__ = __repr__