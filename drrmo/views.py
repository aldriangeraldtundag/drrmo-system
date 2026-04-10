import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import CertificateForm
from .models import AssessmentReport, Certificate, Place


def compute_risk_level(place):
    if place.latitude is None or place.longitude is None:
        return 'Unknown'

    score = int(abs(place.latitude * 10 + place.longitude * 10))
    return ['Low', 'Medium', 'High'][score % 3]


def report_recommendations(risk_level):
    if risk_level == 'High':
        return (
            'The location is at elevated flood risk. Review evacuation plans, secure electrical systems, and avoid permanent structures in low-lying zones.'
        )
    if risk_level == 'Medium':
        return (
            'The location requires continued monitoring. Improve drainage, raise critical assets, and make sure nearby communities are aware of flood alerts.'
        )
    return (
        'Current risk is low. Maintain regular inspection of waterways and keep an up-to-date flood preparedness checklist.'
    )


def _load_geojson(filename):
    path = Path(settings.BASE_DIR) / 'data' / 'geojson' / filename
    if not path.exists():
        raise Http404(f'GeoJSON file not found: {filename}')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


@login_required
def geojson_boundary(request):
    return JsonResponse(_load_geojson('silay_barangaymap.geojson'))


@login_required
def geojson_hazard(request):
    return JsonResponse(_load_geojson('SilayCity_Admin_MGB_Flooding_10k.geojson'))


@login_required
def map_view(request):
    places = Place.objects.filter(latitude__isnull=False, longitude__isnull=False).all()
    return render(request, 'drrmo/map.html', {
        'places': places,
    })


@login_required
def report_generate(request, place_id):
    place = get_object_or_404(Place, pk=place_id)
    risk_level = compute_risk_level(place)
    summary = (
        f'Initial flood risk assessment for {place.name}. The calculated flood risk level is {risk_level}. '
        'This assessment was generated from the CDRA map workflow.'
    )
    report = AssessmentReport.objects.create(
        place=place,
        title=f'Flood Assessment Report — {place.name}',
        risk_level=risk_level,
        summary=summary,
        recommendations=report_recommendations(risk_level),
    )
    return redirect(reverse('report_print', args=[report.pk]))


@login_required
def report_print(request, pk):
    report = get_object_or_404(AssessmentReport, pk=pk)
    return render(request, 'drrmo/report_print.html', {
        'report': report,
    })


@login_required
def certificate_create(request, place_id):
    place = get_object_or_404(Place, pk=place_id)
    if request.method == 'POST':
        form = CertificateForm(request.POST)
        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.place = place
            certificate.save()
            return redirect(reverse('certificate_print', args=[certificate.pk]))
    else:
        form = CertificateForm()
    return render(request, 'drrmo/certificate_form.html', {
        'form': form,
        'place': place,
    })


@login_required
def certificate_print(request, pk):
    certificate = get_object_or_404(Certificate, pk=pk)
    return render(request, 'drrmo/certificate_print.html', {
        'certificate': certificate,
    })
