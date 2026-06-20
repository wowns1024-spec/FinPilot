from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_investmentprofile"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name="InvestmentProfile",
                ),
            ],
            database_operations=[],
        ),
    ]
