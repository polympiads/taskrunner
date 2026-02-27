
from typing import TYPE_CHECKING, List, TypedDict, NotRequired

if TYPE_CHECKING:
    from ccs.models.contest import Contest
from ccs.models.eventfeed import EventFeed, EventFeedKind
from judge.languages import LanguageKind, get_language

class LanguagesCCSJson (TypedDict):
    id   : str
    name : str

    extensions : List[str]

    @staticmethod
    async def acreate_languages_events (contest: "Contest"):
        for uuid, lang in LanguageKind.choices():
            ccs_info = get_language(lang).ccs_language_information
            
            await EventFeed.objects.acreate_event(
                contest,
                ccs_info['id'],
                EventFeedKind.LANGUAGES,
                ccs_info
            )
