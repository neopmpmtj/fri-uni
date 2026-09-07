from django import forms
from django.contrib import admin

from . import services
from .models import (
    ActivityLog,
    Brand,
    ChangeLog,
    EquipmentModel,
    Parameter,
    Style,
    TubingLength,
)


class SoftDeleteAdminMixin:
    def delete_model(self, request, obj):
        obj.soft_delete(request.user)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.soft_delete(request.user)


class PriceReasonForm(forms.ModelForm):
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class EquipmentModelForm(PriceReasonForm):
    class Meta:
        model = EquipmentModel
        fields = ("style", "kind", "btu", "list_price")

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk:
            original = EquipmentModel.all_objects.get(pk=self.instance.pk)
            if original.list_price != cleaned.get("list_price") and not (
                cleaned.get("reason") or ""
            ).strip():
                self.add_error("reason", "A reason is required when changing list price.")
        return cleaned


class TubingLengthForm(PriceReasonForm):
    class Meta:
        model = TubingLength
        fields = ("length", "price")

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk:
            original = TubingLength.all_objects.get(pk=self.instance.pk)
            if original.price != cleaned.get("price") and not (
                cleaned.get("reason") or ""
            ).strip():
                self.add_error("reason", "A reason is required when changing tubing price.")
        return cleaned


@admin.register(Brand)
class BrandAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("name", "updated_at")
    search_fields = ("name",)
    fields = ("name",)


@admin.register(Style)
class StyleAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("name", "brand", "updated_at")
    list_filter = ("brand",)
    search_fields = ("name", "brand__name")
    fields = ("brand", "name")


@admin.register(EquipmentModel)
class EquipmentModelAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    form = EquipmentModelForm
    list_display = ("style", "kind", "btu", "list_price")
    list_filter = ("kind", "style__brand")

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        if not change:
            obj.created_by = request.user
        if change:
            original = EquipmentModel.all_objects.get(pk=obj.pk)
            if original.list_price != obj.list_price:
                services.update_equipment_list_price(
                    original,
                    obj.list_price,
                    reason=form.cleaned_data.get("reason"),
                    actor=request.user,
                )
        super().save_model(request, obj, form, change)


@admin.register(TubingLength)
class TubingLengthAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    form = TubingLengthForm
    list_display = ("length", "price")

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        if not change:
            obj.created_by = request.user
        if change:
            original = TubingLength.all_objects.get(pk=obj.pk)
            if original.price != obj.price:
                services.update_tubing_price(
                    original,
                    obj.price,
                    reason=form.cleaned_data.get("reason"),
                    actor=request.user,
                )
        super().save_model(request, obj, form, change)


@admin.register(Parameter)
class ParameterAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("key", "value")
    fields = ("key", "value")


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
