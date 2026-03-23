

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

from printing.views.admin import REV_PRINT_DONE, PrintDoneView
from printing.views.download import REV_PRINT_DOWNLOAD, PrintDownloadView
from printing.views.print import REV_PRINT_CREATE, CreatePrintView

urlpatterns = [
    path('contests/<int:pk>/prints/', CreatePrintView.as_view(), name = REV_PRINT_CREATE),
    path('contests/<int:pk>/prints/<int:prpk>/download/<str:kind>/', PrintDownloadView.as_view(), name = REV_PRINT_DOWNLOAD), 
    path('contests/<int:pk>/prints/<int:prpk>/done/', PrintDoneView.as_view(), name = REV_PRINT_DONE)
]
