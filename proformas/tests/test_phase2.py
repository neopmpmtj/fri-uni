from django.db import IntegrityError
import pytest

from proformas.models import Client


@pytest.mark.django_db
def test_live_client_name_must_be_unique():
    Client.objects.create(name="Acme")
    with pytest.raises(IntegrityError):
        Client.objects.create(name="Acme")


@pytest.mark.django_db
def test_soft_deleted_client_name_can_be_reused():
    first = Client.objects.create(name="Acme")
    first.soft_delete()
    Client.objects.create(name="Acme")
    assert Client.objects.filter(name="Acme").count() == 1
    assert Client.all_objects.filter(name="Acme").count() == 2
