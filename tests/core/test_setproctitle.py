import unittest

from cryptodogelight.util.setproctitle import setproctitle


class TestSetProcTitle(unittest.TestCase):
    def test_does_not_crash(self):
        setproctitle("cryptodogelight test title")
