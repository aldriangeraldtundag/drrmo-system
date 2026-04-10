from django import forms

from .models import AssessmentReport, Certificate, Place


class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ['name', 'code', 'description', 'latitude', 'longitude']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class AssessmentReportForm(forms.ModelForm):
    class Meta:
        model = AssessmentReport
        fields = ['place', 'title', 'summary', 'recommendations']
        widgets = {
            'summary': forms.Textarea(attrs={'rows': 6}),
            'recommendations': forms.Textarea(attrs={'rows': 6}),
        }


class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['issuer_name', 'requestor_name', 'business_name', 'project_name', 'issued_date', 'remarks']
        widgets = {
            'issued_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.Textarea(attrs={'rows': 5}),
        }
