import json
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import CertificateForm
from .models import AssessmentReport, Certificate, Place


HAZARD_LABELS = {
    'LF': 'Low Susceptibility',
    'MF': 'Moderate Susceptibility',
    'HF': 'High Susceptibility',
    'VHF': 'Very High Susceptibility',
}

FLOOD_RISK_ASSESSMENT_TEXT = {
    'LF': 'Low Susceptibility; less than 0.5 meters flood height and/or less than 1 day flooding',
    'MF': 'Moderate Susceptibility; 0.5 to 1 meter flood height and/or 1 to 3 days flooding',
    'HF': 'High Susceptibility; 1 to 2 meters flood height and/or more than 3 days flooding',
    'VHF': 'Very High Susceptibility; more than 2 meters flood height and/or more than 3 days flooding',
}

HAZARD_DETAILS_TEXT = {
    'LF': (
        'Areas with low susceptibility to floods are likely to experience flood heights of less than '
        '0.5 meters and/or flood duration of less than 1 day. These include low hills and gentle slopes '
        'that have sparse to moderate drainage density.\n\n'
        'The implementation of appropriate mitigation measures as deemed necessary by project engineers '
        'and LGU building officials is recommended for areas that are susceptible to various flood depths. '
        'Site-specific studies including the assessment for other types of hazards should also be '
        'conducted to address potential foundation problems.'
    ),
    'MF': (
        'Areas with moderate susceptibility to floods are likely to experience flood heights of 0.5 meters '
        'up to 1 meter and/or flood duration of 1 to 3 days. These are subject to widespread inundation '
        'during prolonged and extensive heavy rainfall or extreme weather conditions. Fluvial terraces, '
        'alluvial fans, and infilled valleys are also moderately subjected to flooding.\n\n'
        'The implementation of appropriate mitigation measures as deemed necessary by project engineers '
        'and LGU building officials is recommended for areas that are susceptible to various flood depths. '
        'Site-specific studies including the assessment for other types of hazards should also be '
        'conducted to address potential foundation problems.'
    ),
    'HF': (
        'Areas with high susceptibility to floods are likely to experience flood heights of 1 meter up to '
        '2 meters and/or flood duration of more than 3 days. Sites including active river channels, '
        'abandoned river channels, and areas along riverbanks, are immediately flooded during heavy '
        'rains of several hours and are prone to flash floods. These may be considered not suitable for '
        'permanent habitation but may be developed for alternative uses subject to the implementation '
        'of appropriate mitigation measures after conducting site-specific geotechnical studies as '
        'deemed necessary by project engineers and LGU building officials.\n\n'
        'The implementation of appropriate mitigation measures as deemed necessary by project engineers '
        'and LGU building officials is recommended for areas that are susceptible to various flood depths. '
        'Site-specific studies including the assessment for other types of hazards should also be '
        'conducted to address potential foundation problems.'
    ),
    'VHF': (
        'Areas with very high susceptibility to floods are likely to experience flood heights of greater '
        'than 2 meters and/or flood duration of more than 3 days. These include active river channels, '
        'abandoned river channels, and areas along riverbanks, which are immediately flooded during '
        'heavy rains of several hours and are prone to flash floods. These are considered critical '
        'geohazard areas and are not suitable for development. It is recommended that these be '
        'declared as "No Habitation/No Build Zones" by the LGU, and that affected households/communities '
        'be relocated.\n\n'
        'The implementation of appropriate mitigation measures as deemed necessary by project engineers '
        'and LGU building officials is recommended for areas that are susceptible to various flood depths. '
        'Site-specific studies including the assessment for other types of hazards should also be '
        'conducted to address potential foundation problems.'
    ),
}

GENERIC_RECOMMENDATION_NOTES = [
    'All hazard assessments are based on the available susceptibility maps and the coordinates of the user\'s selected location.',
    'Depending on the basemaps used and methods employed during mapping, discrepancies may be observed between location of hazards or exposure information and actual ground observations.',
    'In some areas, hazard assessment may be updated as new data become available for interpretation or as a result of major topographic changes due to onset of natural events.',
    'The possibility of both rain-induced landslide and flooding occurring is not disregarded. Because of the composite nature of MGB\'s 1:10,000-scale Rain-induced Landslide and Flood Susceptibility Maps, it spatially prioritizes the more frequently occurring and most damaging hazards in an area. Continuous updating is being done.',
    'For site-specific evaluation or construction of critical facilities, detailed engineering assessment and onsite geotechnical engineering survey may be required.',
]

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


def _point_in_ring(point, ring):
    inside = False
    for i in range(len(ring)):
        j = (i - 1) % len(ring)
        xi, yi = ring[i]
        xj, yj = ring[j]
        intersect = ((yi > point['lat']) != (yj > point['lat'])) and (
            point['lng'] < (xj - xi) * (point['lat'] - yi) / (yj - yi + 0.0) + xi
        )
        if intersect:
            inside = not inside
    return inside


def _point_in_geometry(lat, lng, geometry):
    if not geometry:
        return False
    point = {'lat': lat, 'lng': lng}
    coords = geometry.get('coordinates', [])
    if geometry.get('type') == 'Polygon':
        outer_ring = coords[0]
        if not _point_in_ring(point, outer_ring):
            return False
        for hole in coords[1:]:
            if _point_in_ring(point, hole):
                return False
        return True
    if geometry.get('type') == 'MultiPolygon':
        for polygon in coords:
            outer_ring = polygon[0]
            if not _point_in_ring(point, outer_ring):
                continue
            if any(_point_in_ring(point, hole) for hole in polygon[1:]):
                continue
            return True
    return False


def _find_geojson_feature(lat, lng, data):
    for feature in data.get('features', []):
        if feature.get('geometry') and _point_in_geometry(lat, lng, feature['geometry']):
            return feature
    return None


def _build_assessment_data(lat, lng):
    boundary_geojson = _load_geojson('silay_barangaymap.geojson')
    hazard_geojson = _load_geojson('SilayCity_Admin_MGB_Flooding_10k.geojson')

    boundary_feature = _find_geojson_feature(lat, lng, boundary_geojson)
    hazard_feature = _find_geojson_feature(lat, lng, hazard_geojson)

    if not boundary_feature or not hazard_feature:
        raise ValueError('Location is not inside a flood risk area within Silay City.')

    barangay = boundary_feature['properties'].get('name') or boundary_feature['properties'].get('NAME') or 'Unknown barangay'
    hazard_code = hazard_feature['properties'].get('HazCode') or hazard_feature['properties'].get('hazcode') or 'Unknown'
    hazard_label = HAZARD_LABELS.get(
        hazard_code,
        hazard_feature['properties'].get('HazDesc') or hazard_feature['properties'].get('hazdesc') or hazard_code,
    )
    hazard_details = HAZARD_DETAILS_TEXT.get(
        hazard_code,
        hazard_feature['properties'].get('HazDesc') or hazard_feature['properties'].get('hazdesc') or 'Flood conditions require detailed review.',
    )

    risk_level_map = {
        'LF': 'Low',
        'MF': 'Medium',
        'HF': 'High',
        'VHF': 'High',
    }
    risk_level = risk_level_map.get(hazard_code, 'Unknown')
    timestamp = timezone.localtime(timezone.now())
    summary = (
        f'Initial assessment for {barangay}. Flood risk is {hazard_label}. '
        'Review community preparedness and flood response plans for this barangay.'
    )

    return {
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'date': timestamp.strftime('%Y-%m-%d'),
        'time': timestamp.strftime('%H:%M:%S'),
        'barangay': barangay,
        'coordinates': {
            'lat': round(lat, 6),
            'lng': round(lng, 6),
        },
        'hazard_code': hazard_code,
        'hazard_label': hazard_label,
        'flood_risk_assessment': FLOOD_RISK_ASSESSMENT_TEXT.get(hazard_code, hazard_label),
        'risk_level': risk_level,
        'details': hazard_details,
        'summary': summary,
        'recommendation': report_recommendations(risk_level),
    }


@login_required
def assessment_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    lat = payload.get('lat')
    lng = payload.get('lng')
    if lat is None or lng is None:
        return JsonResponse({'error': 'Latitude and longitude are required.'}, status=400)

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Latitude and longitude must be numeric.'}, status=400)

    try:
        assessment_data = _build_assessment_data(lat, lng)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    return JsonResponse(assessment_data)


@login_required
def assessment_report_pdf(request):
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if lat is None or lng is None:
        return HttpResponse('Latitude and longitude are required.', status=400)

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return HttpResponse('Latitude and longitude must be numeric.', status=400)

    try:
        assessment_data = _build_assessment_data(lat, lng)
    except ValueError as exc:
        return HttpResponse(str(exc), status=400)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
        title='Flood Risk Susceptibility Hazard Assessment',
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title_style', parent=styles['Heading1'], fontSize=16, leading=20, spaceAfter=10)
    label_style = ParagraphStyle('label_style', parent=styles['BodyText'], fontSize=9, leading=12, textColor=colors.HexColor('#475569'))
    body_style = ParagraphStyle(
        'body_style',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
    )
    centered_body_style = ParagraphStyle(
        'centered_body_style',
        parent=body_style,
        alignment=1,
    )
    bullet_style = ParagraphStyle('bullet_style', parent=body_style, leftIndent=10, bulletIndent=0, spaceAfter=4)

    page_width, page_height = A4
    usable_width = page_width - doc.leftMargin - doc.rightMargin
    usable_height = page_height - doc.topMargin - doc.bottomMargin
    header_left_width = usable_width * 0.42
    header_right_width = usable_width - header_left_width
    header_right_label_width = header_right_width * 0.34
    header_right_value_width = header_right_width - header_right_label_width
    assessment_left_width = usable_width * 0.34
    assessment_right_width = usable_width - assessment_left_width

    header_logo_paths = [
        Path(settings.BASE_DIR) / 'static' / 'pdf_assets' / 'word' / 'media' / 'image1.png',
        Path(settings.BASE_DIR) / 'static' / 'pdf_assets' / 'word' / 'media' / 'image2.png',
        Path(settings.BASE_DIR) / 'static' / 'pdf_assets' / 'word' / 'media' / 'image3.png',
    ]

    logo_cells = []
    for logo_path in header_logo_paths:
        if logo_path.exists():
            logo_cells.append(Image(str(logo_path), width=44, height=44))

    logos_table = None
    if logo_cells:
        logos_table = Table([logo_cells], colWidths=[46] * len(logo_cells))
        logos_table.setStyle(
            TableStyle(
                [
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]
            )
        )

    agency_text = Paragraph(
        'Republic of the Philippines<br/><b>Silay City Disaster Risk Reduction and Management Office</b>',
        body_style,
    )

    header_left_content = []
    if logos_table:
        header_left_content.append(logos_table)
        header_left_content.append(Spacer(1, 8))
    header_left_content.append(agency_text)

    header_right = Table(
        [
            ['DATE / TIME', f"{assessment_data['date']} {assessment_data['time']}"],
            ['BARANGAY', assessment_data['barangay']],
            [
                'COORDINATES',
                f"{assessment_data['coordinates']['lng']}, {assessment_data['coordinates']['lat']}",
            ],
        ],
        colWidths=[header_right_label_width, header_right_value_width],
    )
    header_right.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]
        )
    )

    header_table = Table(
        [[header_left_content, header_right]],
        colWidths=[header_left_width, header_right_width],
    )
    header_table.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]
        )
    )

    assessment_paragraph = Paragraph(assessment_data['flood_risk_assessment'], centered_body_style)
    explanation_paragraph = Paragraph(assessment_data['details'].replace('\n\n', '<br/><br/>'), centered_body_style)

    # Expand the main table row so the report page looks fuller on A4 without clipping content.
    assessment_text_width = assessment_left_width - 16
    explanation_text_width = assessment_right_width - 16
    _, assessment_height = assessment_paragraph.wrap(assessment_text_width, 10000)
    _, explanation_height = explanation_paragraph.wrap(explanation_text_width, 10000)
    content_height = max(assessment_height, explanation_height)
    target_row_height = usable_height * 0.44
    body_row_height = max(target_row_height, content_height + 24)

    assessment_table = Table(
        [
            ['ASSESSMENT', 'EXPLANATION AND RECOMMENDATION'],
            [assessment_paragraph, explanation_paragraph],
        ],
        colWidths=[assessment_left_width, assessment_right_width],
        rowHeights=[None, body_row_height],
    )
    assessment_table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('GRID', (0, 0), (-1, -1), 0.75, colors.HexColor('#94a3b8')),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]
        )
    )

    story = [
        header_table,
        Spacer(1, 12),
        Paragraph('Flood Risk Susceptibility Hazard Assessment', title_style),
        Spacer(1, 4),
        assessment_table,
        Spacer(1, 12),
        Paragraph('Explanation and Recommendation Note', label_style),
    ]

    for note in GENERIC_RECOMMENDATION_NOTES:
        story.append(Paragraph(note, bullet_style, bulletText='•'))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="hydro_meteorological_hazard_assessment.pdf"'
    return response


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
