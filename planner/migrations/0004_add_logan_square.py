from django.db import migrations


def add_logan_square(apps, schema_editor):
    Neighborhood = apps.get_model("planner", "Neighborhood")
    Neighborhood.objects.using(schema_editor.connection.alias).get_or_create(
        name="Logan Square"
    )


class Migration(migrations.Migration):
    dependencies = [("planner", "0003_alter_itineraryactivity_address_and_more")]

    operations = [migrations.RunPython(add_logan_square, migrations.RunPython.noop)]
