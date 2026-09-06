from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from . import services
from .models import ActivityLog, ChangeLog, Parameter, TubingLength


class PriceReasonForm(forms.ModelForm):
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class TubingLengthForm(PriceReasonForm):
    class Meta:
        model = TubingLength
        fields = "__all__"


@admin.register(TubingLength)
class TubingLengthAdmin(admin.ModelAdmin):
    form = TubingLengthForm
    list_display = ("length", "price")

    def save_model(self, request, obj, form, change):
        if change:
            original = TubingLength.all_objects.get(pk=obj.pk)
            if original.price != obj.price:
                try:
                    services.update_tubing_price(
                        original,
                        obj.price,
                        reason=form.cleaned_data.get("reason"),
                        actor=request.user,
                    )
                except ValidationError as exc:
                    form.add_error("reason", exc)
                    raise
                return
        obj.updated_by = request.user
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ("key", "value")


@admin.register(ChangeLog)
class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "entity_type", "field", "actor", "reason")
    readonly_fields = [f.name for f in ChangeLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "action", "object_type", "actor")
    readonly_fields = [f.name for f in ActivityLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
