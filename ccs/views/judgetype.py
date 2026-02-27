
import enum
from typing import TYPE_CHECKING, TypedDict

from ccs.models.eventfeed import EventFeed, EventFeedKind

if TYPE_CHECKING:
    from ccs.models.contest import Contest

class JudgementType (enum.Enum):
    RE  = "RE"
    TLE = "TLE"
    MLE = "MLE"
    WA  = "WA"
    CE  = "CE"
    AC  = "AC"
    JE  = "JE"

class JudgementTypesCCSJson(TypedDict):
    id   : str
    name : str

    penalty : bool
    solved  : bool

    @staticmethod
    async def acreate_judgement_types (contest: "Contest"):
        async def send_judgement (judgement: JudgementType, data: "JudgementTypesCCSJson"):
            data["id"] = judgement.value
            await EventFeed.objects.acreate_event(
                contest,
                judgement.value,
                EventFeedKind.JUDGEMENT_TYPES,
                data)
        
        await send_judgement(JudgementType.RE,  { "name": "Runtime Error", "penalty": True, "solved": False })
        await send_judgement(JudgementType.TLE, { "name": "Time Limit Exceeded", "penalty": True, "solved": False })
        await send_judgement(JudgementType.MLE, { "name": "Memory Limit Exceeded", "penalty": True, "solved": False })
        await send_judgement(JudgementType.WA,  { "name": "Wrong Answer", "penalty": True, "solved": False })
        await send_judgement(JudgementType.CE,  { "name": "Compilation Error", "penalty": False, "solved": False })
        await send_judgement(JudgementType.AC,  { "name": "Accepted", "penalty": False, "solved": True })
        await send_judgement(JudgementType.JE,  { "name": "Judge Error", "penalty": False, "solved": False })
