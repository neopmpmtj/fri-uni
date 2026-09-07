import pytest
from django.core.management import call_command
from django.urls import reverse

from accounts.models import User
from proformas.models import Client, Proforma, Site
from proformas.seed import DEMO_ADMIN_EMAIL, DEMO_MANAGER_EMAIL, DEMO_PASSWORD


@pytest.mark.django_db
def test_seed_demo_creates_users_clients_and_quotes():
    call_command("seed_demo")
    call_command("seed_demo")
    admin = User.objects.get(email=DEMO_ADMIN_EMAIL)
    manager = User.objects.get(email=DEMO_MANAGER_EMAIL)
    assert admin.role == User.Role.ADMIN
    assert admin.can_delete
    assert manager.role == User.Role.STAFF
    assert not manager.can_delete
    assert User.objects.filter(email=DEMO_ADMIN_EMAIL).count() == 1
    assert Client.objects.count() == 3
    assert Site.objects.count() == 5
    assert Proforma.objects.filter(status=Proforma.Status.ISSUED).count() == 2
    assert Proforma.objects.filter(status=Proforma.Status.DRAFT).count() == 2
    assert Proforma.objects.filter(status=Proforma.Status.CANCELLED).count() == 1
    assert Proforma.objects.count() == 5


@pytest.mark.django_db
def test_manager_cannot_delete_client(client):
    call_command("seed_demo")
    manager = User.objects.get(email=DEMO_MANAGER_EMAIL)
    org = Client.objects.get(name="Construtora Atlantico, Lda.")
    client.force_login(manager)
    response = client.post(
        reverse("client_list"), {"id": str(org.pk), "action": "delete"}
    )
    assert response.status_code == 403
    assert Client.objects.filter(pk=org.pk).exists()
    page = client.get(reverse("client_list"), {"id": str(org.pk)})
    assert page.status_code == 200
    assert b'value="delete"' not in page.content


@pytest.mark.django_db
def test_admin_can_delete_client(client):
    call_command("seed_demo")
    admin = User.objects.get(email=DEMO_ADMIN_EMAIL)
    org = Client.objects.create(name="Empty Client Ltd")
    client.force_login(admin)
    response = client.post(
        reverse("client_list"), {"id": str(org.pk), "action": "delete"}
    )
    assert response.status_code == 302
    assert not Client.objects.filter(pk=org.pk).exists()


@pytest.mark.django_db
def test_admin_cannot_delete_client_with_sites(client):
    call_command("seed_demo")
    admin = User.objects.get(email=DEMO_ADMIN_EMAIL)
    org = Client.objects.get(name="Residencias do Tejo, Lda.")
    client.force_login(admin)
    response = client.post(
        reverse("client_list"), {"id": str(org.pk), "action": "delete"}, follow=True
    )
    assert response.status_code == 200
    assert Client.objects.filter(pk=org.pk).exists()
    assert b"still has sites" in response.content


@pytest.mark.django_db
def test_manager_cannot_delete_site(client):
    call_command("seed_demo")
    manager = User.objects.get(email=DEMO_MANAGER_EMAIL)
    site = Site.objects.get(alias_1="Moradia Cascais")
    client.force_login(manager)
    response = client.post(
        reverse("site_list"), {"id": str(site.pk), "action": "delete"}
    )
    assert response.status_code == 403
    assert Site.objects.filter(pk=site.pk).exists()
    page = client.get(reverse("site_list"), {"id": str(site.pk)})
    assert page.status_code == 200
    assert b'value="delete"' not in page.content


@pytest.mark.django_db
def test_manager_forbidden_on_admin(client):
    call_command("seed_demo")
    manager = User.objects.get(email=DEMO_MANAGER_EMAIL)
    client.force_login(manager)
    response = client.get("/admin/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_demo_users_can_log_in(client):
    call_command("seed_demo")
    assert client.login(email=DEMO_MANAGER_EMAIL, password=DEMO_PASSWORD)
    assert client.login(email=DEMO_ADMIN_EMAIL, password=DEMO_PASSWORD)
