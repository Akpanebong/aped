from django.urls import path
from . import views
urlpatterns=[
 path('forms/',views.form_catalog,name='form_catalog'),
 path('forms/manage/',views.form_definition_list,name='form_definition_list'),
 path('forms/new/',views.form_definition_create,name='form_definition_create'),
 path('forms/<int:pk>/edit/',views.form_definition_update,name='form_definition_update'),
 path('forms/<int:pk>/delete/',views.form_definition_delete,name='form_definition_delete'),
 path('forms/<int:form_id>/',views.form_records,name='form_records'),
 path('records/',views.record_list,name='record_list'),
 path('records/new/',views.record_create,name='record_create'),
 path('records/<int:pk>/',views.record_detail,name='record_detail'),
 path('records/<int:pk>/edit/',views.record_update,name='record_update'),
 path('records/<int:pk>/sections/<int:section_index>/',views.record_section_update,name='record_section_update'),
 path('records/<int:pk>/delete/',views.record_delete,name='record_delete'),
 path('followups/<int:pk>/edit/',views.followup_update,name='followup_update'),
 path('followups/<int:pk>/delete/',views.followup_delete,name='followup_delete'),
 path('exports/excel/',views.export_excel,name='export_excel'),
 path('exports/pdf/',views.export_pdf,name='export_pdf'),
]
