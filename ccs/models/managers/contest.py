
from ccs.feed.judgetype import JudgementTypesCCSJson
from ccs.feed.languages import LanguagesCCSJson
from ccs.models.eventfeed import EventFeed
from ccs.models.contest import Contest
from ccs.feed.contest import acreate_contest_event, acreate_contest_start_event

from django.db    import transaction
from django.utils import timezone

from asgiref.sync import async_to_sync, sync_to_async

class ContestManager:
    @staticmethod
    async def acreate_contest (**updates):
        contest = await Contest.objects.acreate(**updates)

        await acreate_contest_event(contest)

        return contest
    @staticmethod
    def create_contest (**updates):
        return async_to_sync(ContestManager.acreate_contest)(**updates)

    @staticmethod
    def start_contest (contest_id: int):
        with transaction.atomic():
            contest = Contest.objects.select_for_update().get(pk = contest_id)
            if contest.started is not None:
                raise ValueError("Can't start contest that has started.")
            
            contest.started = timezone.now()
            contest.save()
        
            async def send_events ():
                await acreate_contest_start_event(contest)
                
                await LanguagesCCSJson.acreate_languages_events(contest)
                await JudgementTypesCCSJson.acreate_judgement_types(contest)
            
            async_to_sync(send_events)()

    astart_contest = sync_to_async(start_contest)
