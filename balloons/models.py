
from typing import Literal

from django.db import models

from django.contrib.auth.models import User
from django_enumfield import enum
from balloons.ccs import create_ccs_for_balloons
from ccs.models.contest import Contest, ContestAccount, ContestProblem, ContestRole
from problems.models import Problem

class BalloonStatus (enum.Enum):
    PENDING = 0
    TAKEN   = 1
    DROPPED = 2

def balloon_status_to_string (status: BalloonStatus):
    match status:
        case BalloonStatus.PENDING: return "pending"
        case BalloonStatus.TAKEN:   return "taken"
        case BalloonStatus.DROPPED: return "dropped"

    raise NotImplementedError(f"Could not recognize balloon status '{status}'")

def balloon_status_from_string (status: "Literal['pending', 'taken', 'dropped']"):
    match status:
        case "pending" : return BalloonStatus.PENDING
        case "taken"   : return BalloonStatus.TAKEN 
        case "dropped" : return BalloonStatus.DROPPED
    
    return None

class Balloon (models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.PROTECT)
    team    = models.ForeignKey(User,    on_delete=models.PROTECT)
    problem = models.ForeignKey(Problem, on_delete=models.PROTECT)

    status = enum.EnumField(BalloonStatus, default = BalloonStatus.PENDING)

    def set_status (self, status: BalloonStatus):
        if status == self.status:
            return
        
        self.status = status
        self.save()
        self.send_ccs()
    def send_ccs(self):
        create_ccs_for_balloons(self)

    @staticmethod
    def create_balloon (contest: Contest, team: User, problem: Problem):
        if not ContestAccount.objects.filter(contest = contest, user = team, role = ContestRole.TEAM).exists():
            return

        if Balloon.objects.filter(contest = contest, team = team, problem = problem).exists():
            return
        
        balloon = Balloon.objects.create(contest = contest, team = team, problem = problem)
        balloon.send_ccs()
        return balloon
