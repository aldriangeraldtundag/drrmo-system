import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Convert GIS shapefiles from data/ into GeoJSON files for the CDRA map.'

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        source_dir = base_dir / 'data'
        output_dir = source_dir / 'geojson'
        output_dir.mkdir(parents=True, exist_ok=True)

        layers = [
            {
                'name': 'barangay boundary',
                'input': source_dir / 'silay_barangaymap.shp',
                'output': output_dir / 'silay_barangaymap.geojson',
                'src_srs': 'EPSG:4326',
            },
            {
                'name': 'flood hazard',
                'input': source_dir / 'SilayCity_Admin_MGB_Flooding_10k.shp',
                'output': output_dir / 'SilayCity_Admin_MGB_Flooding_10k.geojson',
                'src_srs': 'EPSG:32651',
            },
        ]

        for layer in layers:
            input_path = layer['input']
            output_path = layer['output']
            if not input_path.exists():
                self.stderr.write(self.style.ERROR(f"Missing source file: {input_path}"))
                continue

            command = ['ogr2ogr', '-f', 'GeoJSON']
            if layer.get('src_srs'):
                command.extend(['-s_srs', layer['src_srs']])
            command.extend(['-t_srs', 'EPSG:4326', str(output_path), str(input_path)])

            self.stdout.write(f"Importing {layer['name']} from {input_path.name}...")
            subprocess.run(command, check=True)
            self.stdout.write(self.style.SUCCESS(f"Created {output_path.name}"))

        self.stdout.write(self.style.SUCCESS('GeoJSON import complete.'))
