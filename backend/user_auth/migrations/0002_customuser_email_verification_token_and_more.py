# Generated by Django 5.1.4 on 2024-12-19 16:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_auth', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='email_verification_token',
            field=models.CharField(blank=True, max_length=100, verbose_name='email verification token'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='email_verified',
            field=models.BooleanField(default=False, verbose_name='email verified'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='department',
            field=models.CharField(default='Non assigné', help_text='The department this user belongs to.', max_length=50, verbose_name='department'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='customuser',
            name='employee_id',
            field=models.CharField(default='EMP000', help_text='Required. 10 characters or fewer.', max_length=10, unique=True, verbose_name='employee ID'),
            preserve_default=False,
        ),
    ]
