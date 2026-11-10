from django.urls import path
from . import views
urlpatterns=[
 path('',views.dashboard,name='dashboard'),
 path('projects/',views.project_list,name='project_list'),
 path('projects/new/',views.project_create,name='project_create'),
 path('activities/',views.activity_list,name='activity_list'),
 path('activities/new/',views.activity_create,name='activity_create'),
 path('attendance/',views.attendance_list,name='attendance_list'),
 path('attendance/new/',views.attendance_create,name='attendance_create'),
 path('attendance/<int:pk>/edit/',views.attendance_update,name='attendance_update'),
 path('attendance/<int:pk>/',views.attendance_detail,name='attendance_detail'),
 path('attendance/<int:pk>/delete/',views.attendance_delete,name='attendance_delete'),
 path('attendance/<int:pk>/approve/',views.attendance_approve,name='attendance_approve'),
 path('attendance/<int:pk>/reject/',views.attendance_reject,name='attendance_reject'),
 path('attendance/export/excel/',views.attendance_export_excel,name='attendance_export_excel'),
 path('attendance/export/pdf/',views.attendance_export_pdf,name='attendance_export_pdf'),
]
