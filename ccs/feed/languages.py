
from typing import List, TypedDict

from ccs.models.contest import Contest
from ccs.models.managers.eventfeed import EventFeedKind, EventFeedManager
from judge.languages import LanguageKind, get_language


class LanguagesCCSJson (TypedDict):
    id   : str
    name : str

    extensions : List[str]

    @staticmethod
    async def acreate_languages_events (contest: "Contest"):
        for uuid, lang in LanguageKind.choices():
            ccs_info = get_language(lang).ccs_language_information
            
            await EventFeedManager.acreate_event(
                contest,
                ccs_info['id'],
                EventFeedKind.LANGUAGES,
                ccs_info
            )
