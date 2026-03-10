from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Human-readable service name', max_length=100)),
                ('app_label', models.CharField(
                    help_text="URL namespace of the Django app (e.g. 'reports', 'core')",
                    max_length=100,
                    unique=True,
                )),
                ('is_active', models.BooleanField(default=True)),
                ('description', models.TextField(blank=True)),
                ('allowed_groups', models.ManyToManyField(
                    blank=True,
                    help_text='Groups that can access this service',
                    related_name='accessible_services',
                    to='auth.group',
                )),
            ],
            options={
                'ordering': ['name'],
            },
        ),
    ]
