# Silay City DRRMO Capstone

This is the Django-based capstone system for Silay City DRRMO.

## Setup

1. Activate the existing virtual environment:

   ```bash
   source venv/bin/activate
   ```

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run database migrations:

   ```bash
   python manage.py migrate
   ```

4. Create a superuser:

   ```bash
   python manage.py createsuperuser
   ```

5. Start the development server:

   ```bash
   python manage.py runserver
   ```

6. Open the app in your browser:
   - Home: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

## Import GIS layers

If you want to use the boundary and flood hazard layers from `data/`, run:

```bash
python manage.py import_layers
```

This converts the shapefiles into GeoJSON files under `data/geojson/` and enables the map overlay layers.

## Notes

- The project currently uses SQLite for local development.
- Future work will add PostGIS integration for spatial data and flood risk mapping.
- Existing shapefiles in the `data/` folder will be imported into the spatial database later.
