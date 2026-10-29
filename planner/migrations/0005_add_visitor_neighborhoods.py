from django.db import migrations


def add_neighborhoods(apps, schema_editor):
    Neighborhood = apps.get_model("planner", "Neighborhood")
    for name in (
        "Avondale",
        "Bridgeport",
        "Bronzeville",
        "Bucktown",
        "Edgewater",
        "Greektown",
        "Humboldt Park",
        "Hyde Park",
        "Lincoln Square",
        "Little Italy",
        "Pilsen",
        "Ravenswood",
        "Rogers Park",
        "Streeterville",
    ):
        Neighborhood.objects.using(schema_editor.connection.alias).get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [("planner", "0004_add_logan_square")]

    operations = [migrations.RunPython(add_neighborhoods, migrations.RunPython.noop)]
