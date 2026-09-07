import pytest
from django.urls import reverse

from proformas.services import accept_proforma, add_line, create_draft, issue_proforma

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def issued(client, staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user, quantity=1)
    return issue_proforma(proforma, staff_user)


def test_post_mark_accepted_on_issued_detail(client, staff_user, issued):
    client.force_login(staff_user)
    response = client.post(
        reverse("proforma_detail", args=[issued.pk]),
        {"action": "accept_proforma"},
    )
    assert response.status_code == 302
    issued.refresh_from_db()
    assert issued.accepted_at is not None

    page = client.get(reverse("proforma_detail", args=[issued.pk]))
    assert page.status_code == 200
    assert b"status-pill--accepted" in page.content
    assert b"Clear accepted" in page.content


def test_post_unaccept_on_issued_detail(client, staff_user, issued):
    accept_proforma(issued, staff_user)
    client.force_login(staff_user)
    response = client.post(
        reverse("proforma_detail", args=[issued.pk]),
        {"action": "unaccept_proforma"},
    )
    assert response.status_code == 302
    issued.refresh_from_db()
    assert issued.accepted_at is None

    page = client.get(reverse("proforma_detail", args=[issued.pk]))
    assert page.status_code == 200
    assert b"Mark accepted" in page.content
