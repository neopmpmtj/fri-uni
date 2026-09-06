from django import forms
from django.core.exceptions import ValidationError

from .models import Client, EquipmentModel, ProformaLine, Site, TubingLength


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


class ProformaLineForm(forms.ModelForm):
    class Meta:
        model = ProformaLine
        fields = ("model", "quantity", "extra_tubing", "tubing_length")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["model"].queryset = EquipmentModel.objects.select_related(
            "style__brand"
        ).order_by("style__brand__name", "btu")
        self.fields["tubing_length"].queryset = TubingLength.objects.order_by("length")
        self.fields["tubing_length"].required = False

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("extra_tubing") and not cleaned.get("tubing_length"):
            raise ValidationError("Tubing length is required when extra tubing is needed.")
        return cleaned

