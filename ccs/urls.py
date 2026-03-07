

"""
URL configuration for taskrunner project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from ccs.auth.login import REV_API_LOGIN, api_login
from ccs.auth.whoami import REV_WHO_AM_I, WhoAmIView
from ccs.views.contest import REV_CONTEST_ITEM, REV_CONTEST_LIST, ContestView, ContestsView
from ccs.views.problem import REV_STATEMENT, StatementView

urlpatterns = [
    path('whoami/', WhoAmIView.as_view(), name = REV_WHO_AM_I),
    path('login/', api_login, name = REV_API_LOGIN),

    path('contests/',          ContestsView.as_view(), name=REV_CONTEST_LIST),
    path('contests/<int:pk>/', ContestView.as_view(),  name=REV_CONTEST_ITEM),

    path('contests/<int:pk>/problems/<int:pbpk>/statement/', StatementView.as_view(), name = REV_STATEMENT)
]
