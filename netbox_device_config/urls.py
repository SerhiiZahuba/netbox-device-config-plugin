from django.urls import path
from . import views

app_name = 'netbox_device_config'

urlpatterns = [
    path('credentials/', views.DeviceCredentialListView.as_view(), name='devicecredential_list'),
    path('credentials/add/', views.DeviceCredentialCreateView.as_view(), name='devicecredential_add'),
    path('credentials/<int:pk>/edit/', views.DeviceCredentialEditView.as_view(), name='devicecredential_edit'),
    path('credentials/<int:pk>/test/', views.DeviceCredentialTestView.as_view(), name='devicecredential_test'),
    path('credentials/<int:pk>/backup/', views.DeviceCredentialBackupView.as_view(), name='devicecredential_backup'),
    path('history/', views.DeviceConfigHistoryListView.as_view(), name='deviceconfighistory_list'),
    path('backup/<int:device_id>/', views.backup_device, name='backup_device'),

    path("config/<int:config_id>/", views.view_config, name="view_config"),
    path("config/<int:config_id>/diff/", views.compare_config, name="compare_config"),
    path("config/<int:config_id>/download/", views.download_config, name="download_config"),

    #path('config/<int:config_id>/', views.view_config, name='view_config'),
   # path("config/<int:config_id>/download/", views.download_config, name="download_config"),
    path('compare/<int:config_id>/', views.compare_config, name='compare_config'),
    path("statistics/", views.BackupStatisticsView.as_view(), name="backup_statistics"),
    path("view/<int:config_id>/", views.view_config, name="view_config"),
    path("compare/<int:config_id>/", views.compare_config, name="compare_config"),
    path("download/<int:config_id>/", views.download_config, name="download_config"),

    path("templates/", views.BackupTemplatesListView.as_view(), name="backup_templates_list"),
    path("templates/add/", views.BackupTemplatesCreateView.as_view(), name="backup_templates_add"),
    path("templates/<int:pk>/edit/", views.BackupTemplatesEditView.as_view(), name="backup_templates_edit"),
    path("templates/<int:pk>/delete/", views.BackupTemplatesDeleteView.as_view(), name="backup_templates_delete"),

    #path("settings/", views.BackupSettingsListView.as_view(), name="backup_settings_list"),
   # path("settings/add/", views.BackupSettingsCreateView.as_view(), name="backup_settings_add"),
    #path("settings/<int:pk>/edit/", views.BackupSettingsEditView.as_view(), name="backup_settings_edit"),
    #path("settings/<int:pk>/delete/", views.BackupSettingsDeleteView.as_view(), name="backup_settings_delete"),

]
