from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Brand,
    Client,
    Family,
    Item,
    Parameter,
    ProformaLine,
    Site,
    SubFamily,
    TubingLength,
    VatRate,
)
from .services import percent_to_rate, validate_internal_code, validate_vat_code


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ("name", "phone", "email")

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Client.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A live client with this name already exists.")
        return name


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = (
            "client",
            "alias_1",
            "alias_2",
            "alias_3",
            "alias_4",
            "street",
            "postal_code",
            "city",
            "notes",
        )
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class NewDraftForm(forms.Form):
    site = forms.ModelChoiceField(queryset=Site.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["site"].queryset = Site.objects.select_related("client").order_by(
            "client__name", "alias_1"
        )


class ProformaHeaderForm(forms.Form):
    upfront_discount_percent = forms.DecimalField(max_digits=5, decimal_places=2)
    extra_labour = forms.DecimalField(max_digits=12, decimal_places=2)
    observations = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class DataDefaultSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        instance = getattr(value, "instance", None)
        if instance is None:
            return option
        if getattr(instance, "is_default", False):
            option["attrs"]["data-default"] = "1"
        if isinstance(instance, SubFamily):
            option["attrs"]["data-family"] = str(instance.family_id)
        if isinstance(instance, Item):
            option["attrs"]["data-sub-family"] = str(instance.sub_family_id)
            option["attrs"]["data-brand"] = str(instance.brand_id)
        return option


class ProformaLineForm(forms.ModelForm):
    family = forms.ModelChoiceField(
        queryset=Family.objects.none(), required=False, widget=DataDefaultSelect
    )
    sub_family = forms.ModelChoiceField(
        queryset=SubFamily.objects.none(), required=False, widget=DataDefaultSelect
    )
    manufacturer = forms.ModelChoiceField(
        queryset=Brand.objects.none(), required=False, widget=DataDefaultSelect
    )

    class Meta:
        model = ProformaLine
        fields = ("item", "quantity", "extra_tubing", "tubing_length")
        widgets = {"item": DataDefaultSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        items = Item.objects.select_related("sub_family__family", "brand").order_by(
            "internal_code"
        )
        self.fields["item"].queryset = items
        self.fields["item"].label_from_instance = (
            lambda obj: f"{obj.internal_code} — {obj.kind} {obj.btu}"
        )
        self.fields["family"].queryset = Family.objects.order_by("name")
        self.fields["sub_family"].queryset = SubFamily.objects.select_related(
            "family"
        ).order_by("name")
        self.fields["manufacturer"].queryset = Brand.objects.order_by("name")
        self.fields["tubing_length"].queryset = TubingLength.objects.order_by("length")
        self.fields["tubing_length"].required = False
        if self.instance.pk and self.instance.item_id:
            item = self.instance.item
            self.fields["family"].initial = item.sub_family.family_id
            self.fields["sub_family"].initial = item.sub_family_id
            self.fields["manufacturer"].initial = item.brand_id

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("extra_tubing") and not cleaned.get("tubing_length"):
            raise ValidationError("Tubing length is required when extra tubing is needed.")
        return cleaned


class FamilyForm(forms.ModelForm):
    class Meta:
        model = Family
        fields = ("name", "is_default")

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Family.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A live family with this name already exists.")
        return name


class SubFamilyForm(forms.ModelForm):
    class Meta:
        model = SubFamily
        fields = ("family", "name", "is_default")

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get("name") or "").strip()
        family = cleaned.get("family")
        cleaned["name"] = name
        if name and family:
            qs = SubFamily.objects.filter(family=family, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    "A live sub-family with this name already exists in that family."
                )
        return cleaned


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ("name", "is_default")

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Brand.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A live manufacturer with this name already exists.")
        return name


class ItemForm(forms.ModelForm):
    family = forms.ModelChoiceField(
        queryset=Family.objects.none(), required=False, widget=DataDefaultSelect
    )

    class Meta:
        model = Item
        fields = (
            "sub_family",
            "brand",
            "vat_rate",
            "internal_code",
            "kind",
            "btu",
            "max_volume_m3",
            "is_default",
        )
        widgets = {"sub_family": DataDefaultSelect, "vat_rate": DataDefaultSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["family"].queryset = Family.objects.order_by("name")
        self.fields["sub_family"].queryset = SubFamily.objects.select_related(
            "family"
        ).order_by("family__name", "name")
        self.fields["brand"].queryset = Brand.objects.order_by("name")
        self.fields["vat_rate"].queryset = VatRate.objects.order_by("rate")
        self.fields["max_volume_m3"].required = False
        if self.instance.pk and self.instance.sub_family_id:
            self.fields["family"].initial = self.instance.sub_family.family_id
        elif not self.instance.pk:
            default_vat = VatRate.objects.filter(is_default=True).first()
            if default_vat:
                self.fields["vat_rate"].initial = default_vat.pk

    def clean_internal_code(self):
        return validate_internal_code(
            self.cleaned_data.get("internal_code"),
            exclude_item_id=self.instance.pk,
        )


class ItemPriceForm(forms.Form):
    list_price = forms.DecimalField(max_digits=12, decimal_places=2)
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class VatRateForm(forms.ModelForm):
    percent = forms.DecimalField(max_digits=6, decimal_places=2, min_value=0, max_value=100)

    class Meta:
        model = VatRate
        fields = ("code", "label", "is_default")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.rate is not None:
            self.fields["percent"].initial = self.instance.as_percent()

    def clean_code(self):
        return validate_vat_code(self.cleaned_data.get("code"), exclude_id=self.instance.pk)

    def clean(self):
        cleaned = super().clean()
        percent = cleaned.get("percent")
        if percent is not None:
            cleaned["rate"] = percent_to_rate(percent)
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.rate = self.cleaned_data["rate"]
        if commit:
            obj.save()
        return obj


class ParameterForm(forms.ModelForm):
    class Meta:
        model = Parameter
        fields = ("value",)
        widgets = {"value": forms.TextInput()}


class TubingLengthForm(forms.ModelForm):
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = TubingLength
        fields = ("length", "price")

    def clean_length(self):
        length = self.cleaned_data["length"]
        qs = TubingLength.objects.filter(length=length)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A live tubing length with this value already exists.")
        return length

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk:
            return cleaned
        new_price = cleaned.get("price")
        if new_price is not None and new_price != self.instance.price:
            if not (cleaned.get("reason") or "").strip():
                self.add_error("reason", "A reason is required when changing tubing price.")
        return cleaned

