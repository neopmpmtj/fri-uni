from decimal import Decimal

from django.core.management.base import BaseCommand

from proformas.models import (
    Brand,
    EquipmentModel,
    Parameter,
    Style,
    TubingLength,
)


BRANDS = ("Mitsubishi", "LG", "Nippon")
STYLE_NAME = "Split"
BTUS = (9000, 12000, 18000)
INDOOR_PRICES = {9000: "500.00", 12000: "650.00", 18000: "800.00"}
OUTDOOR_PRICES = {9000: "550.00", 12000: "700.00", 18000: "900.00"}
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


class Command(BaseCommand):
    help = "Idempotent demo catalog: brands, styles, models, tubing, parameters."

    def handle(self, *args, **options):
        for name in BRANDS:
            brand, _ = _live_get_or_create(Brand, name=name)
            style, _ = _live_get_or_create(Style, brand=brand, name=STYLE_NAME)
            for btu in BTUS:
                _live_get_or_create(
                    EquipmentModel,
                    defaults={"list_price": Decimal(INDOOR_PRICES[btu])},
                    style=style,
                    kind=EquipmentModel.Kind.INDOOR,
                    btu=btu,
                )
                _live_get_or_create(
                    EquipmentModel,
                    defaults={"list_price": Decimal(OUTDOOR_PRICES[btu])},
                    style=style,
                    kind=EquipmentModel.Kind.OUTDOOR,
                    btu=btu,
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
