from django.contrib import admin

from syncservice.models import HrPerson, SyncConfig


# Register your models here.
@admin.register(HrPerson)
class HrPersonAdmin(admin.ModelAdmin):
    list_display = ['employee_number', 'full_name', 'employee_status', 'person_type', 'creation_date']
    list_filter = ['employee_status', 'person_type', 'creation_date']
    search_fields = ['employee_number', 'full_name', 'english_name', 'email_address']
    readonly_fields = ['person_id', 'creation_date', 'last_update_date']


@admin.register(SyncConfig)
class SyncConfigAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description']
    search_fields = ['key', 'description']