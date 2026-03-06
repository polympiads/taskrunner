
import asyncio
from typing import List, Tuple

from ccs.feed.judgetype import JudgementTypesCCSJson
from ccs.feed.languages import LanguagesCCSJson
from ccs.feed.users import add_judge_account_events, add_team_account_events
from ccs.models.eventfeed import EventFeed
from ccs.models.contest import Contest, ContestAccount, ContestRole
from ccs.feed.contest import acreate_contest_event, acreate_contest_start_event

from django.db    import transaction
from django.utils import timezone

from asgiref.sync import async_to_sync, sync_to_async
from django.contrib.auth.models import User

class ContestManager:
    @staticmethod
    async def acreate_contest (**updates):
        contest = await Contest.objects.acreate(**updates)

        await acreate_contest_event(contest)

        return contest

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

    @staticmethod
    def add_accounts (contest_id: int, accounts: List[Tuple[User, ContestRole]]):
        with transaction.atomic():
            contest = Contest.objects.select_for_update().get(pk = contest_id)
            
            existing_accounts = ContestAccount.objects.filter(
                contest     = contest,
                user_id__in = [ user.pk for user, role in accounts ]
            )
            if len(existing_accounts) != 0:
                accounts_usernames = [ account.user.username for account in existing_accounts ]
                raise ValueError(f"Accounts {accounts_usernames} already have a role.")
            
            bulk = []
            for user, role in accounts:
                bulk.append(
                    ContestAccount(
                        user = user,
                        contest = contest,
                        role = role
                    )
                )

            ContestAccount.objects.bulk_create(bulk)

            async def create_events ():
                tasks = []
                for user, role in accounts:
                    match role:
                        case ContestRole.TEAM: 
                            tasks.append(add_team_account_events(contest, user))
                        case ContestRole.JUDGE: 
                            tasks.append(add_judge_account_events(contest, user))
            
                await asyncio.gather(*tasks)

            async_to_sync(create_events)()
