# Generated by Django 5.1.2 on 2024-11-02 12:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_appuser'),
    ]

    operations = [
        migrations.AddField(
            model_name='appuser',
            name='user_type',
            field=models.CharField(choices=[('teacher', 'Teacher'), ('expert', 'Expert'), ('student', 'Student')], default='admin', max_length=10),
        ),
    ]