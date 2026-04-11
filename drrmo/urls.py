from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='drrmo/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.map_view, name='map_view'),
    path('geojson/boundary/', views.geojson_boundary, name='geojson_boundary'),
    path('geojson/hazard/', views.geojson_hazard, name='geojson_hazard'),
    path('assessment/', views.assessment_api, name='assessment_api'),
    path('reports/full/pdf/', views.assessment_report_pdf, name='assessment_report_pdf'),
    path('reports/generate/<int:place_id>/', views.report_generate, name='report_generate'),
    path('reports/<int:pk>/print/', views.report_print, name='report_print'),
    path('certificates/new/<int:place_id>/', views.certificate_create, name='certificate_create'),
    path('certificates/<int:pk>/print/', views.certificate_print, name='certificate_print'),
]
