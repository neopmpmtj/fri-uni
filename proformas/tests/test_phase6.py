from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from proformas.models import ActivityLog, Proforma
from proformas.services import (
    add_line,
    create_draft,
    issue_proforma,
    update_draft,
    cancel_proforma,
)


@pytest.fixture
def issued(db, staff_user, site, indoor):
    proforma = create_draft(site, staff_user, discount_percent=10)
    add_line(proforma, indoor, staff_user, quantity=1)
    return issue_proforma(proforma, staff_user)


def test_issue_freezes_line_price_after_catalog_change(issued, indoor):
    frozen_price = issued.lines.first().unit_price
    frozen_total = issued.grand_total
    indoor.list_price = Decimal("999.00")
    indoor.save()
    issued.refresh_from_db()
    assert issued.lines.first().unit_price == frozen_price
    assert issued.grand_total == frozen_total
    assert frozen_price == Decimal("500.00")


def test_issue_snapshots_client_name(issued, site):
    original = issued.client_name
    site.client.name = "Renamed Ltd"
    site.client.save()
    issued.refresh_from_db()
    assert issued.client_name == original
    assert original == "Acme"


def test_issued_money_update_rejected(issued, staff_user):
    with pytest.raises(ValidationError):
        update_draft(issued, staff_user, extra_labour=Decimal("99.00"))


def test_cancel_does_not_return_to_draft(issued, staff_user):
    cancel_proforma(issued, staff_user)
    issued.refresh_from_db()
    assert issued.status == Proforma.Status.CANCELLED
    assert ActivityLog.objects.filter(action="cancel_proforma").exists()
    with pytest.raises(ValidationError):
        update_draft(issued, staff_user, observations="nope")
