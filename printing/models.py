
from django.db import models
from django.db import transaction

from django.contrib.auth.models import User
from django_enumfield import enum
from ccs.models.contest import Contest
from printing.ccs import create_ccs_for_print
from printing.tasks.prepare import prepare_pdf_print

class PrintStatus (enum.Enum):
    PENDING   = 0
    COMPILING = 1
    FAILURE   = 2
    ERROR     = 3
    READY     = 4
    DONE      = 5

class ContestPrintManager (models.Manager):
    @staticmethod
    def create_print (contest: Contest, owner: User, code_location: str):
        with transaction.atomic():
            print = ContestPrint.objects.create(
                contest = contest,
                owner = owner,
                status = PrintStatus.PENDING,
                code_location = code_location
            )
            print.send_ccs()

            prepare_pdf_print.delay_on_commit(print.pk)

            return print

class ContestPrint (models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.PROTECT)

    owner  = models.ForeignKey(User, on_delete=models.PROTECT)
    status = enum.EnumField(PrintStatus, default = PrintStatus.PENDING)

    code_location = models.TextField()

    simple_error = models.TextField(null = True, default = None)
    pdf_location = models.TextField(null = True, default = None)
    err_location = models.TextField(null = True, default = None)

    objects : "models.Manager[ContestPrint] | ContestPrintManager" = ContestPrintManager()

    def send_ccs (self):
        create_ccs_for_print(self)

    def on_compiling (self):
        self.status = PrintStatus.COMPILING
        self.save()
        
        self.send_ccs()
    def on_done (self):
        self.status = PrintStatus.DONE
        self.save()
        
        self.send_ccs()
    def on_ready (self, pdf_location: str):
        self.pdf_location = pdf_location
        self.status = PrintStatus.READY
        self.save()

        self.send_ccs()
    def on_task_error (self, error: str):
        self.simple_error = error
        self.status = PrintStatus.ERROR
        self.save()

        self.send_ccs()
    def on_compile_error (self, err_location: str):
        self.err_location = err_location
        self.status = PrintStatus.FAILURE
        self.save()

        self.send_ccs()
