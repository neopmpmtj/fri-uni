from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse

from accounts.models import User
from proformas.models import Brand, ChangeLog, Family, Item, SubFamily
from proformas.seed import FAMILY_AC
from proformas.services import (
    normalize_internal_code,
    update_equipment_list_price,
    validate_internal_code,
)


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="pass12345",
        role=User.Role.ADMIN,
    )


@pytest.mark.django_db
def test_internal_code_is_stored_uppercase():
    assert normalize_internal_code(" dai-sen-i-9 ") == "DAI-SEN-I-9"


@pytest.mark.django_db
def test_internal_code_unique_is_case_insensitive(indoor):
    with pytest.raises(ValidationError):
        validate_internal_code("mit-spl-i-9")


@pytest.mark.django_db
def test_list_price_without_reason_fails(indoor, admin_user):
    with pytest.raises(ValidationError):
        update_equipment_list_price(
            indoor, Decimal("510.00"), reason="", actor=admin_user
        )


@pytest.mark.django_db
def test_list_price_with_reason_writes_change_log(indoor, admin_user):
    update_equipment_list_price(
        indoor, Decimal("510.00"), reason="supplier increase", actor=admin_user
    )
    log = ChangeLog.objects.get(field="list_price")
    assert log.reason == "supplier increase"
    assert log.entity_type == "items"
    assert log.new_value == "510.00"
    indoor.refresh_from_db()
    assert indoor.list_price == Decimal("510.00")


@pytest.mark.django_db
def test_seed_catalog_twice_does_not_duplicate():
    call_command("seed_catalog")
    call_command("seed_catalog")
    assert Brand.objects.filter(name="Mitsubishi").count() == 1
    assert Brand.objects.filter(
        name__in=["Mitsubishi", "LG", "Nippon", "Daikin"]
    ).count() == 4
    ac = Family.objects.get(name=FAMILY_AC)
    assert ac.is_default
    names = set(
        SubFamily.objects.filter(family=ac).values_list("name", flat=True)
    )
    assert names == {
        "Split",
        "Sensira",
        "Comfora",
        "Perfera",
        "Perfera Floor",
        "Stylish",
        "Emura",
        "Ururu Sarara",
    }
    daikin_sensira = Item.objects.filter(
        brand__name="Daikin", sub_family__name="Sensira"
    )
    assert daikin_sensira.count() == 6
    indoor_9 = Item.objects.get(
        brand__name="Daikin",
        sub_family__name="Sensira",
        kind=Item.Kind.INDOOR,
        btu=9000,
    )
    assert indoor_9.internal_code == "DAI-SEN-I-9"
    assert indoor_9.max_volume_m3 == Decimal("20")


@pytest.mark.django_db
def test_sub_family_is_shared_across_brands():
    call_command("seed_catalog")
    split = SubFamily.objects.get(name="Split", family__name=FAMILY_AC)
    assert Item.objects.filter(sub_family=split, brand__name="Mitsubishi").exists()
    assert Item.objects.filter(sub_family=split, brand__name="LG").exists()
    assert not Item.objects.filter(
        sub_family=split, brand__name="Daikin"
    ).exists()


@pytest.mark.django_db
def test_staff_can_open_catalog_pages(client, staff_user):
    client.force_login(staff_user)
    for name in ("item_list", "family_list", "sub_family_list", "manufacturer_list"):
        response = client.get(reverse(name))
        assert response.status_code == 200
    dashboard = client.get("/")
    assert b'data-i18n="items"' in dashboard.content
    assert b'data-i18n="families"' in dashboard.content
    assert b"catalogAdmin" not in dashboard.content
