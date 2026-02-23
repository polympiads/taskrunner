
from django_enumfield import enum
from django.contrib.auth.models import User

import rules

class Visibility (enum.Enum):
    PUBLIC  = 0
    PRIVATE = 1

def parse_visibility (x: "str | None"):
    if x is None:
        return None, "Field '{field}' should exist"

    match x:
        case "public"  : return Visibility.PUBLIC,  None
        case "private" : return Visibility.PRIVATE, None
    
    return None, "Field '{field}' should be either \"public\" or \"private\""

@rules.predicate
def is_public (user: User, visibility: Visibility):
    return visibility == Visibility.PUBLIC
