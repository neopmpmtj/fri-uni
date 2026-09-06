from decimal import Decimal

import pytest

from accounts.models import User
from proformas.models import (
    Brand,
    Client,
    Family,
    Item,
    Parameter,
    Power,
    Site,
    SubFamily,
    TubingLength,
    VatRate,
)


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff@example.com", password="pass12345", role=User.Role.STAFF
    )


@pytest.fixture
def site(db):
    org = Client.objects.create(name="Acme")
    return Site.objects.create(client=org, alias_1="House 1")


@pytest.fixture
def indoor(db):
    Parameter.objects.get_or_create(
        key="default_upfront_discount_percent", defaults={"value": "10"}
    )
    family = Family.objects.create(name="Air conditioners", is_default=True)
    sub = SubFamily.objects.create(family=family, name="Split", is_default=True)
    brand = Brand.objects.create(name="Mitsu")
    vat, _ = VatRate.objects.get_or_create(
        code="VAT23",
        defaults={
            "label": "23%",
            "rate": Decimal("0.2300"),
            "is_default": True,
        },
    )
    power, _ = Power.objects.get_or_create(
        power=Decimal("9000"), unit="BTU"
    )
    return Item.objects.create(
        sub_family=sub,
        brand=brand,
        vat_rate=vat,
        power=power,
        internal_code="MIT-SPL-I-9",
        kind=Item.Kind.INDOOR,
        max_volume_m3=Decimal("20"),
        list_price=Decimal("500.00"),
    )


@pytest.fixture
def tubing(db):
    return TubingLength.objects.create(length=Decimal("5.00"), price=Decimal("40.00"))
