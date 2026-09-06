from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from accounts.models import User
from proformas.models import Brand, ChangeLog, EquipmentModel, Style
from proformas.services import update_equipment_list_price


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="pass12345",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def equipment(db):
    brand = Brand.objects.create(name="TestBrand")
    style = Style.objects.create(brand=brand, name="Split")
    return EquipmentModel.objects.create(
        style=style,
        kind=EquipmentModel.Kind.INDOOR,
        btu=9000,
        list_price=Decimal("500.00"),
    )


@pytest.mark.django_db
def test_list_price_without_reason_fails(equipment, admin_user):
    with pytest.raises(ValidationError):
        update_equipment_list_price(
            equipment, Decimal("510.00"), reason="", actor=admin_user
        )


@pytest.mark.django_db
def test_list_price_with_reason_writes_change_log(equipment, admin_user):
    update_equipment_list_price(
        equipment, Decimal("510.00"), reason="supplier increase", actor=admin_user
    )
    log = ChangeLog.objects.get(field="list_price")
    assert log.reason == "supplier increase"
    assert log.new_value == "510.00"
    equipment.refresh_from_db()
    assert equipment.list_price == Decimal("510.00")


@pytest.mark.django_db
def test_seed_catalog_twice_does_not_duplicate_brands():
    call_command("seed_catalog")
    call_command("seed_catalog")
    assert Brand.objects.filter(name="Mitsubishi").count() == 1
    assert Brand.objects.filter(
        name__in=["Mitsubishi", "LG", "Nippon", "Daikin"]
    ).count() == 4
    daikin_styles = set(
        Style.objects.filter(brand__name="Daikin").values_list("name", flat=True)
    )
    assert daikin_styles == {
        "Sensira",
        "Comfora",
        "Perfera",
        "Perfera Floor",
        "Stylish",
        "Emura",
        "Ururu Sarara",
    }
