
from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict

from django.urls import reverse

from ccs.models.eventfeed import EventFeed
from ccs.models.managers.eventfeed import EventFeedKind, EventFeedManager
from ccs.models.visible import Visibility

from asgiref.sync import async_to_sync

if TYPE_CHECKING:
    from .models import ContestPrint, PrintStatus

class PrintCCSJson(TypedDict):
    id: str

    owner_id : str
    status   : Literal['pending', 'compiling', 'failure', 'error', 'ready', 'done']

    code_href: str

    simple_error: NotRequired[str]

    pdf_href: NotRequired[str]
    err_href: NotRequired[str]

def print_status_to_string (print_status: "PrintStatus"):
    from printing.models import PrintStatus

    match print_status:
        case PrintStatus.PENDING:   return "pending"
        case PrintStatus.COMPILING: return "compiling"
        case PrintStatus.FAILURE:   return "failure"
        case PrintStatus.ERROR:     return "error"
        case PrintStatus.READY:     return "ready"
        case PrintStatus.DONE:      return "done"
    
    raise NotImplementedError(f"Couldn't recognize status '{print_status}'.")

def ccs_json_from_print (print: "ContestPrint") -> PrintCCSJson:
    from printing.views.download import REV_PRINT_DOWNLOAD

    ccs: PrintCCSJson = {
        "id" : str(print.pk),

        "owner_id" : str(print.owner.pk),
        "status"   : print_status_to_string(print.status),

        "code_href" : reverse(
            REV_PRINT_DOWNLOAD,
            kwargs = { "pk": print.contest.pk, "prpk": print.pk, "kind": "code" },
            urlconf = "ccs.urls")
    }

    if print.pdf_location is not None:
        ccs["pdf_href"] = reverse(
            REV_PRINT_DOWNLOAD,
            kwargs = { "pk": print.contest.pk, "prpk": print.pk, "kind": "pdf" })
    if print.err_location is not None:
        ccs["err_href"] = reverse(
            REV_PRINT_DOWNLOAD,
            kwargs = { "pk": print.contest.pk, "prpk": print.pk, "kind": "err" })
    if print.simple_error is not None:
        ccs["simple_error"] = print.simple_error

    return ccs

def create_ccs_for_print (print: "ContestPrint") -> EventFeed:
    return async_to_sync(EventFeedManager.acreate_event)(
        print.contest,
        str(print.pk),
        EventFeedKind.PRINT,
        ccs_json_from_print(print),
        Visibility.PRIVATE,
        print.owner
    )
