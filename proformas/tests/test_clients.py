import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from accounts.models import User
from proformas.forms import SiteForm
from proformas.models import Client, Site
from proformas.services import (
    normalize_postal_code,
    save_client,
    validate_tax_number,
)


def client_kwargs(**overrides):
    data = {
        "kind": Client.Kind.PERSON,
        "name": "Acme",
        "tax_number": "512345678",
        "street": "Rua Teste 1",
        "postal_code": "1000-001",
        "city": "Lisboa",
        "country_code": "PT",
    }
    data.update(overrides)
    return data


@pytest.mark.unit
@pytest.mark.django_db
def test_normalize_postal_code_accepts_dash():
    assert normalize_postal_code("1000-001") == "1000-001"


@pytest.mark.unit
@pytest.mark.django_db
def test_normalize_postal_code_inserts_dash():
    assert normalize_postal_code("1000001") == "1000-001"


@pytest.mark.unit
@pytest.mark.django_db
def test_normalize_postal_code_rejects_bad_length():
    with pytest.raises(ValidationError):
        normalize_postal_code("10000")


@pytest.mark.unit
@pytest.mark.django_db
def test_validate_tax_number_checksum():
    assert validate_tax_number("501442600") == "501442600"


@pytest.mark.unit
@pytest.mark.django_db
def test_validate_tax_number_rejects_bad_checksum():
    with pytest.raises(ValidationError):
        validate_tax_number("501442601")


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff@example.com", password="pass12345", role=User.Role.STAFF
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_save_client_creates_hq_site(staff_user):
    client = Client(**client_kwargs())
    save_client(client, staff_user)
    hq = Site.objects.get(client=client, is_headquarters=True)
    assert hq.alias_1 == "Acme"
    assert hq.street == client.street
    assert hq.postal_code == client.postal_code
    assert hq.city == client.city


@pytest.mark.unit
@pytest.mark.django_db
def test_save_client_edit_does_not_rewrite_hq(staff_user):
    client = Client(**client_kwargs())
    save_client(client, staff_user)
    hq = Site.objects.get(client=client, is_headquarters=True)
    client.name = "Renamed"
    client.street = "Other street"
    save_client(client, staff_user)
    hq.refresh_from_db()
    assert hq.alias_1 == "Acme"
    assert hq.street == "Rua Teste 1"


@pytest.mark.integration
@pytest.mark.django_db
def test_duplicate_live_nif_rejected(client, staff_user):
    client.force_login(staff_user)
    payload = {
        "kind": "person",
        "name": "First",
        "tax_number": "512345678",
        "street": "Rua A",
        "postal_code": "1000-001",
        "city": "Lisboa",
        "country_code": "PT",
        "phone": "",
        "email": "",
    }
    assert client.post(reverse("client_list"), payload).status_code == 302
    payload["name"] = "Second"
    response = client.post(reverse("client_list"), payload)
    assert response.status_code == 200
    assert b"this NIF already exists" in response.content


@pytest.mark.integration
@pytest.mark.django_db
def test_issued_quote_snapshots_client_billing(client, staff_user, site, indoor):
    from proformas.services import add_line, create_draft, issue_proforma

    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user)
    issue_proforma(proforma, staff_user)
    site.client.tax_number = "999999990"
    site.client.street = "Changed"
    site.client.save()
    client.force_login(staff_user)
    body = client.get(reverse("proforma_quote", args=[proforma.pk])).content.decode()
    assert "512345678" in body
    assert "Rua Sede 1" in body


@pytest.mark.unit
@pytest.mark.django_db
def test_site_form_rejects_hq_client_change(staff_user):
    first = Client(**client_kwargs(name="First", tax_number="501442600"))
    second = Client(**client_kwargs(name="Second", tax_number="502757191"))
    save_client(first, staff_user)
    save_client(second, staff_user)
    hq = Site.objects.get(client=first, is_headquarters=True)
    form = SiteForm(
        data={
            "client": str(second.pk),
            "alias_1": hq.alias_1,
            "alias_2": "",
            "alias_3": "",
            "alias_4": "",
            "street": hq.street,
            "postal_code": hq.postal_code,
            "city": hq.city,
            "notes": "",
        },
        instance=hq,
    )
    form.fields["client"].disabled = False
    assert not form.is_valid()
    assert "headquarters" in str(form.errors["client"]).lower()


@pytest.mark.integration
@pytest.mark.django_db
def test_hq_site_cannot_be_reassigned(client, staff_user):
    first = Client(**client_kwargs(name="First", tax_number="501442600"))
    second = Client(**client_kwargs(name="Second", tax_number="502757191"))
    save_client(first, staff_user)
    save_client(second, staff_user)
    hq = Site.objects.get(client=first, is_headquarters=True)
    client.force_login(staff_user)
    response = client.post(
        reverse("site_list"),
        {
            "id": str(hq.pk),
            "client": str(second.pk),
            "alias_1": hq.alias_1,
            "alias_2": "",
            "alias_3": "",
            "alias_4": "",
            "street": hq.street,
            "postal_code": hq.postal_code,
            "city": hq.city,
            "notes": "",
        },
    )
    assert response.status_code == 302
    hq.refresh_from_db()
    assert hq.client_id == first.pk


@pytest.mark.integration
@pytest.mark.django_db
def test_site_post_without_postal_code_rejected(client, staff_user):
    org = Client.objects.create(**client_kwargs())
    client.force_login(staff_user)
    response = client.post(
        reverse("site_list"),
        {
            "client": org.pk,
            "alias_1": "Obra",
            "alias_2": "",
            "alias_3": "",
            "alias_4": "",
            "street": "Rua B",
            "postal_code": "",
            "city": "Lisboa",
            "notes": "",
        },
    )
    assert response.status_code == 200
    assert not Site.objects.filter(alias_1="Obra").exists()
