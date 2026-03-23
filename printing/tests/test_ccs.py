
from django.test import TransactionTestCase

from printing.ccs import print_status_to_string
from printing.models import PrintStatus


class TestPrintingCCS (TransactionTestCase):
    def test_status_to_string (self):
        with self.assertRaises(NotImplementedError):
            print_status_to_string(None)

        self.assertEqual(print_status_to_string(PrintStatus.COMPILING), "compiling")
        self.assertEqual(print_status_to_string(PrintStatus.DONE), "done")
        self.assertEqual(print_status_to_string(PrintStatus.ERROR), "error")
        self.assertEqual(print_status_to_string(PrintStatus.FAILURE), "failure")
        self.assertEqual(print_status_to_string(PrintStatus.PENDING), "pending")
        self.assertEqual(print_status_to_string(PrintStatus.READY), "ready")
