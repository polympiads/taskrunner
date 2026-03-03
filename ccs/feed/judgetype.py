
import enum
from typing import TypedDict

from ccs.models.contest import Contest
from ccs.models.managers.eventfeed import EventFeedKind, EventFeedManager
from submit.models.verdict import SubmissionVerdict


class JudgementType (enum.Enum):
    RE  = "RE"
    TLE = "TLE"
    MLE = "MLE"
    WA  = "WA"
    CE  = "CE"
    AC  = "AC"
    JE  = "JE"

    @staticmethod
    def from_verdict (verdict: SubmissionVerdict) -> "JudgementType":
        match verdict:
            case SubmissionVerdict.ACCEPTED: return JudgementType.AC
            case SubmissionVerdict.COMPILER_ERROR: return JudgementType.CE
            case SubmissionVerdict.JUDGE_ERROR: return JudgementType.JE
            case SubmissionVerdict.WRONG_ANSWER: return JudgementType.WA
            case SubmissionVerdict.RUNTIME_ERROR: return JudgementType.RE
            case SubmissionVerdict.MEM_LIMIT: return JudgementType.MLE
            case SubmissionVerdict.TIME_LIMIT: return JudgementType.TLE
            
        raise NotImplementedError(f"There is no judgement type for verdict {verdict}")

class JudgementTypesCCSJson(TypedDict):
    id   : str
    name : str

    penalty : bool
    solved  : bool

    @staticmethod
    async def acreate_judgement_types (contest: "Contest"):
        async def send_judgement (judgement: JudgementType, data: "JudgementTypesCCSJson"):
            data["id"] = judgement.value
            await EventFeedManager.acreate_event(
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
