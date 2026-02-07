from django.urls import path
from . import views
from .views import (
    BackupTaskListView,
    BackupTaskDetailView,
)

app_name = 'netbox_device_config'

urlpatterns = [
    path('credentials/', views.DeviceCredentialListView.as_view(), name='devicecredential_list'),
    path('credentials/add/', views.DeviceCredentialCreateView.as_view(), name='devicecredential_add'),
    path('credentials/<int:pk>/edit/', views.DeviceCredentialEditView.as_view(), name='devicecredential_edit'),
    path('credentials/<int:pk>/test/', views.DeviceCredentialTestView.as_view(), name='devicecredential_test'),
    path('credentials/<int:pk>/backup/', views.DeviceCredentialBackupView.as_view(), name='devicecredential_backup'),
    path('backup/<int:device_id>/', views.backup_device, name='backup_device'),
    path("config/<int:config_id>/", views.view_config, name="view_config"),
    path("config/<int:config_id>/diff/", views.compare_config, name="compare_config"),
    path("config/<int:config_id>/download/", views.download_config, name="download_config"),
    path('compare/<int:config_id>/', views.compare_config, name='compare_config'),
    path("statistics/", views.BackupStatisticsView.as_view(), name="backup_statistics"),
    path("view/<int:config_id>/", views.view_config, name="view_config"),
    path("templates/", views.BackupTemplatesListView.as_view(), name="backup_templates_list"),
    path("templates/add/", views.BackupTemplatesCreateView.as_view(), name="backup_templates_add"),
    path("templates/<int:pk>/edit/", views.BackupTemplatesEditView.as_view(), name="backup_templates_edit"),
    path("templates/<int:pk>/delete/", views.BackupTemplatesDeleteView.as_view(), name="backup_templates_delete"),
    path("tasks/", BackupTaskListView.as_view(), name="task_history"),
    path("tasks/<int:pk>/", BackupTaskDetailView.as_view(), name="task_detail"),
    #search menu
    path("search/", views.ConfigSearchView.as_view(), name="config_search"),
    # git
    path("settings/git/", views.GitSettingsView.as_view(), name="git_settings"),
    path("device/<int:device_id>/diff/", views.DeviceGitDiffView.as_view(), name="device_git_diff"),
    path("device/<int:device_id>/show/", views.DeviceGitShowView.as_view()),
    path("device/<int:device_id>/diff/", views.DeviceGitDiffView.as_view()),
    # task
    path("scheduler/", views.BackupScheduleListView.as_view(), name="schedule_list"),
    path("scheduler/add/", views.BackupScheduleCreateView.as_view(), name="schedule_add"),

]
