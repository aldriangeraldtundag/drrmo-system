from datetime import date

from django.db import models


class Place(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class AssessmentReport(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=255)
    risk_level = models.CharField(max_length=20, default='Unknown')
    summary = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.place.name}"


class Certificate(models.Model):
    place = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True, blank=True, related_name='certificates')
    report = models.ForeignKey(AssessmentReport, on_delete=models.SET_NULL, null=True, blank=True, related_name='certificates')
    issuer_name = models.CharField(max_length=200)
    requestor_name = models.CharField(max_length=200)
    business_name = models.CharField(max_length=255)
    project_name = models.CharField(max_length=255, blank=True)
    issued_date = models.DateField(default=date.today)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Certificate for {self.business_name or self.project_name or self.requestor_name}"


class FloodRecord(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    place = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True, blank=True, related_name='flood_records')
    event_date = models.DateField()
    barangay = models.CharField(max_length=200, blank=True)
    location_description = models.CharField(max_length=255, blank=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, blank=True)
    affected_households = models.PositiveIntegerField(null=True, blank=True)
    impact_details = models.TextField(blank=True)
    source = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-event_date', '-created_at']

    def __str__(self):
        return f"{self.event_date} - {self.barangay or self.location_description or 'Unknown location'}"


class WeatherData(models.Model):
    location_name = models.CharField(max_length=255, default='Silay City')
    fetched_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField()

    class Meta:
        ordering = ['-fetched_at']

    def __str__(self):
        return f"Weather data for {self.location_name} at {self.fetched_at:%Y-%m-%d %H:%M}"