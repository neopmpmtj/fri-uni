from decimal import Decimal

import pytest

from accounts.models import User
from proformas.models import (
    Brand,
    Client,
    EquipmentModel,
    Parameter,
    Site,
    Style,
    TubingLength,
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
    brand = Brand.objects.create(name="Mitsu")
    style = Style.objects.create(brand=brand, name="Split")
    return EquipmentModel.objects.create(
        style=style,
        kind=EquipmentModel.Kind.INDOOR,
        btu=9000,
        list_price=Decimal("500.00"),
    )


@pytest.fixture
def tubing(db):
    return TubingLength.objects.create(length=Decimal("5.00"), price=Decimal("40.00"))
