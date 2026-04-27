from django import forms
from django.contrib.gis.geos import Point

from .models import AssessmentReport, Certificate, Place


class PlaceForm(forms.ModelForm):
    latitude = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'step': 'any'}))
    longitude = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'step': 'any'}))

    class Meta:
        model = Place
        fields = ['name', 'code', 'description', 'latitude', 'longitude']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.location:
            self.initial['latitude'] = self.instance.location.y
            self.initial['longitude'] = self.instance.location.x

    def save(self, commit=True):
        lat = self.cleaned_data.get('latitude')
        lng = self.cleaned_data.get('longitude')
        if lat is not None and lng is not None:
            self.instance.location = Point(lng, lat, srid=4326)
        else:
            self.instance.location = None
        return super().save(commit=commit)


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
