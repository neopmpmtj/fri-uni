from decimal import Decimal

from django.core.management.base import BaseCommand

from proformas.models import (
    Brand,
    EquipmentModel,
    Parameter,
    Style,
    TubingLength,
)


SIMPLE_BRANDS = ("Mitsubishi", "LG", "Nippon")
SIMPLE_STYLE = "Split"
BTUS = (9000, 12000, 18000)
INDOOR_PRICES = {9000: "500.00", 12000: "650.00", 18000: "800.00"}
OUTDOOR_PRICES = {9000: "550.00", 12000: "700.00", 18000: "900.00"}

# Named ranges from Daikin PT air-to-air heat pumps (bombas de calor ar-ar):
# https://www.daikin.pt/pt_pt/particular/products-and-advice/product-categories/heat-pumps/air-to-air-heat-pumps.html
# Multi / Multi+ / pair are system layouts, not catalog styles.
DAIKIN_STYLES = (
    "Sensira",
    "Comfora",
    "Perfera",
    "Perfera Floor",
    "Stylish",
    "Emura",
    "Ururu Sarara",
)

# Round demo list prices, entry (Sensira) to flagship (Ururu Sarara). Not live prices.
DAIKIN_INDOOR = {
    "Sensira": {9000: "450.00", 12000: "580.00", 18000: "720.00"},
    "Comfora": {9000: "480.00", 12000: "620.00", 18000: "760.00"},
    "Perfera": {9000: "550.00", 12000: "700.00", 18000: "860.00"},
    "Perfera Floor": {9000: "580.00", 12000: "740.00", 18000: "920.00"},
    "Stylish": {9000: "620.00", 12000: "780.00", 18000: "960.00"},
    "Emura": {9000: "680.00", 12000: "860.00", 18000: "1050.00"},
    "Ururu Sarara": {9000: "750.00", 12000: "950.00", 18000: "1200.00"},
}
DAIKIN_OUTDOOR = {
    "Sensira": {9000: "500.00", 12000: "630.00", 18000: "780.00"},
    "Comfora": {9000: "530.00", 12000: "670.00", 18000: "820.00"},
    "Perfera": {9000: "600.00", 12000: "750.00", 18000: "920.00"},
    "Perfera Floor": {9000: "630.00", 12000: "790.00", 18000: "980.00"},
    "Stylish": {9000: "670.00", 12000: "840.00", 18000: "1020.00"},
    "Emura": {9000: "740.00", 12000: "920.00", 18000: "1120.00"},
    "Ururu Sarara": {9000: "820.00", 12000: "1020.00", 18000: "1280.00"},
}

TUBING = (("3.00", "25.00"), ("5.00", "40.00"), ("10.00", "70.00"))
PARAMETERS = (
    ("currency", "EUR"),
    ("default_upfront_discount_percent", "10"),
    ("tubing_length_unit", "m"),
)


def _live_get_or_create(model, defaults=None, **lookup):
    obj = model.objects.filter(**lookup).first()
    if obj:
        return obj, False
    data = dict(lookup)
    if defaults:
        data.update(defaults)
    return model.objects.create(**data), True


def _seed_capacity_models(style, indoor_prices, outdoor_prices):
    for btu in BTUS:
        _live_get_or_create(
            EquipmentModel,
            defaults={"list_price": Decimal(indoor_prices[btu])},
            style=style,
            kind=EquipmentModel.Kind.INDOOR,
            btu=btu,
        )
        _live_get_or_create(
            EquipmentModel,
            defaults={"list_price": Decimal(outdoor_prices[btu])},
            style=style,
            kind=EquipmentModel.Kind.OUTDOOR,
            btu=btu,
        )


class Command(BaseCommand):
    help = "Idempotent demo catalog: brands, styles, models, tubing, parameters."

    def handle(self, *args, **options):
        for name in SIMPLE_BRANDS:
            brand, _ = _live_get_or_create(Brand, name=name)
            style, _ = _live_get_or_create(Style, brand=brand, name=SIMPLE_STYLE)
            _seed_capacity_models(style, INDOOR_PRICES, OUTDOOR_PRICES)

        daikin, _ = _live_get_or_create(Brand, name="Daikin")
        for style_name in DAIKIN_STYLES:
            style, _ = _live_get_or_create(Style, brand=daikin, name=style_name)
            _seed_capacity_models(
                style, DAIKIN_INDOOR[style_name], DAIKIN_OUTDOOR[style_name]
            )

        for length, price in TUBING:
            _live_get_or_create(
                TubingLength,
                defaults={"price": Decimal(price)},
                length=Decimal(length),
            )
        for key, value in PARAMETERS:
            _live_get_or_create(Parameter, defaults={"value": value}, key=key)
        self.stdout.write("Catalog seed complete.")
