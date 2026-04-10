from django.contrib import admin

from .models import AssessmentReport, Certificate, Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'latitude', 'longitude', 'created_at')
    search_fields = ('name', 'code')


@admin.register(AssessmentReport)
class AssessmentReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'place', 'risk_level', 'created_at')
    list_filter = ('risk_level', 'created_at')
    search_fields = ('title', 'summary', 'place__name')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('place', 'business_name', 'issuer_name', 'issued_date', 'created_at')
    list_filter = ('issued_date',)
    search_fields = ('business_name', 'issuer_name', 'requestor_name', 'place__name')
