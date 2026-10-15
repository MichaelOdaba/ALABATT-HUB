from django.urls import path

from .views import OverviewReportView

urlpatterns = [
    path('reports/overview/', OverviewReportView.as_view(), name='overview-report'),
]
