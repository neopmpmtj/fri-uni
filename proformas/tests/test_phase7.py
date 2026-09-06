from django.urls import reverse

from proformas.services import add_line, create_draft, issue_proforma


def _issued(staff_user, site, indoor):
    proforma = create_draft(site, staff_user, discount_percent=10)
    add_line(proforma, indoor, staff_user, quantity=1)
    return issue_proforma(proforma, staff_user)


def test_quote_html_uses_snapshot_client_name(client, staff_user, site, indoor):
    proforma = _issued(staff_user, site, indoor)
    site.client.name = "Renamed Ltd"
    site.client.save()
    client.force_login(staff_user)
    response = client.get(reverse("proforma_quote", args=[proforma.pk]))
    assert response.status_code == 200
    body = response.content.decode()
    assert "Acme" in body
    assert "Renamed Ltd" not in body


def test_pdf_download(client, staff_user, site, indoor):
    proforma = _issued(staff_user, site, indoor)
    client.force_login(staff_user)
    response = client.get(reverse("proforma_pdf", args=[proforma.pk]))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert len(response.content) > 0


def test_portuguese_quote_label(client, staff_user, site, indoor):
    proforma = _issued(staff_user, site, indoor)
    client.force_login(staff_user)
    client.cookies["fu-lang"] = "pt"
    response = client.get(reverse("proforma_quote", args=[proforma.pk]))
    assert "Totais" in response.content.decode()
