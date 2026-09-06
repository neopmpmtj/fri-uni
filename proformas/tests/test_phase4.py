import pytest
from django.urls import reverse

from accounts.models import User
from proformas.models import Client, Site


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff@example.com", password="pass12345", role=User.Role.STAFF
    )


@pytest.mark.django_db
def test_staff_can_create_client_and_site(client, staff_user):
    client.force_login(staff_user)
    response = client.post(reverse("client_list"), {"name": "Acme", "phone": "", "email": ""})
    assert response.status_code == 302
    org = Client.objects.get(name="Acme")
    response = client.post(
        reverse("site_list"),
        {
            "client": org.pk,
            "alias_1": "House 1",
            "alias_2": "",
            "alias_3": "",
            "alias_4": "",
            "street": "",
            "postal_code": "",
            "city": "",
            "notes": "",
        },
    )
    assert response.status_code == 302
    assert Site.objects.filter(alias_1="House 1", client=org).exists()


@pytest.mark.django_db
def test_duplicate_live_client_name_rejected(client, staff_user):
    Client.objects.create(name="Acme")
    client.force_login(staff_user)
    response = client.post(reverse("client_list"), {"name": "Acme", "phone": "", "email": ""})
    assert response.status_code == 200
    assert Client.objects.filter(name="Acme").count() == 1
    assert b"already exists" in response.content
