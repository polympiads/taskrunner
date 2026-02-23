
from django.contrib.auth.models import User
import rules

@rules.predicate
def is_superuser (user: User):
    return user.is_superuser
@rules.predicate
def is_staff (user: User):
    return user.is_staff
