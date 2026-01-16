from django.contrib import admin

from syncservice.models import HrPerson, HrPersonAccount, SyncConfig


# Register your models here.
@admin.register(HrPerson)
class HrPersonAdmin(admin.ModelAdmin):
    list_display = ['employee_number', 'full_name', 'employee_status', 'person_type', 'creation_date']
    list_filter = ['employee_status', 'person_type', 'creation_date']
    search_fields = ['employee_number', 'full_name', 'english_name', 'email_address']
    readonly_fields = ['person_id', 'creation_date', 'last_update_date']


@admin.register(HrPersonAccount)
class HrPersonAccountAdmin(admin.ModelAdmin):
    list_display = ['person', 'account_type', 'account_identifier', 'is_created', 'updated_at']
    list_filter = ['account_type', 'is_created', 'updated_at']
    search_fields = ['person__employee_number', 'person__full_name', 'account_identifier']
    list_editable = ['is_created']
    raw_id_fields = ['person']


@admin.register(SyncConfig)
class SyncConfigAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description']
    search_fields = ['key', 'description']