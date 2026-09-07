import re
from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    ActivityLog,
    ActorType,
    ChangeLog,
    EquipmentModel,
    Parameter,
    Proforma,
    ProformaLine,
    TubingLength,
)
from .pdf import build_proforma_pdf  # noqa: F401


def log_change(
    *,
    entity_type,
    entity_id,
    field,
    old_value,
    new_value,
    actor=None,
    actor_type=ActorType.USER,
    reason="",
):
    return ChangeLog.objects.create(
        entity_type=entity_type,
        entity_id=entity_id,
        field=field,
        old_value="" if old_value is None else str(old_value),
        new_value="" if new_value is None else str(new_value),
        actor=actor,
        actor_type=actor_type,
        reason=reason or "",
        created_by=actor,
        updated_by=actor,
    )


def log_activity(
    *,
    action,
    object_type,
    object_id,
    actor=None,
    actor_type=ActorType.USER,
    details="",
):
    return ActivityLog.objects.create(
        actor=actor,
        actor_type=actor_type,
        action=action,
        object_type=object_type,
        object_id=object_id,
        details=details or "",
        created_by=actor,
        updated_by=actor,
    )


def get_parameter(key, default=None):
    row = Parameter.objects.filter(key=key).first()
    if row is None:
        return default
    return row.value


def update_equipment_list_price(equipment, new_price, *, reason, actor):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("A reason is required when changing list price.")
    new_price = Decimal(str(new_price))
    old = EquipmentModel.all_objects.get(pk=equipment.pk).list_price
    if old == new_price:
        return equipment
    equipment.list_price = new_price
    equipment.updated_by = actor
    equipment.save(update_fields=["list_price", "updated_at", "updated_by"])
    log_change(
        entity_type="models",
        entity_id=equipment.pk,
        field="list_price",
        old_value=old,
        new_value=new_price,
        actor=actor,
        reason=reason,
    )
    return equipment


def update_tubing_price(tubing, new_price, *, reason, actor):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("A reason is required when changing tubing price.")
    new_price = Decimal(str(new_price))
    old = TubingLength.all_objects.get(pk=tubing.pk).price
    if old == new_price:
        return tubing
    tubing.price = new_price
    tubing.updated_by = actor
    tubing.save(update_fields=["price", "updated_at", "updated_by"])
    log_change(
        entity_type="tubing_lengths",
        entity_id=tubing.pk,
        field="price",
        old_value=old,
        new_value=new_price,
        actor=actor,
        reason=reason,
    )
    return tubing


TWOPLACES = Decimal("0.01")


def money(value):
    try:
        return Decimal(str(value)).quantize(TWOPLACES)
    except (InvalidOperation, TypeError) as exc:
        raise ValidationError("Enter a valid amount.") from exc


def discount_percent_value(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValidationError("Enter a valid discount percent.") from exc
    if amount < 0 or amount > 100:
        raise ValidationError("Discount percent must be between 0 and 100.")
    return amount


def labour_value(value):
    amount = money(value or 0)
    if amount < 0:
        raise ValidationError("Extra labour cannot be negative.")
    return amount


def require_draft(proforma):
    if proforma.status != Proforma.Status.DRAFT:
        raise ValidationError("Only draft proformas can be edited.")


def next_proforma_number(year=None):
    year = year or timezone.now().year
    prefix = f"PF-{year}-"
    pattern = re.compile(rf"^PF-{year}-(\d+)$")
    seqs = []
    for number in Proforma.objects.filter(number__startswith=prefix).values_list(
        "number", flat=True
    ):
        match = pattern.fullmatch(number)
        if match:
            seqs.append(int(match.group(1)))
    seq = max(seqs) + 1 if seqs else 1
    return f"{prefix}{seq:04d}"


NUMBER_ALLOCATION_ATTEMPTS = 5


def recompute_draft_totals(proforma):
    require_draft(proforma)
    lines = list(proforma.lines.all())
    equipment = sum((line.quantity * line.unit_price for line in lines), Decimal("0.00"))
    tubing = sum((line.quantity * line.tubing_amount for line in lines), Decimal("0.00"))
    equipment = money(equipment)
    tubing = money(tubing)
    discount = money(equipment * proforma.upfront_discount_percent / Decimal("100"))
    grand = money(equipment - discount + tubing + proforma.extra_labour)
    proforma.equipment_subtotal = equipment
    proforma.tubing_total = tubing
    proforma.discount_amount = discount
    proforma.grand_total = grand
    proforma.save(
        update_fields=[
            "equipment_subtotal",
            "tubing_total",
            "discount_amount",
            "grand_total",
            "updated_at",
        ]
    )
    return proforma


def create_draft(
    site,
    user,
    *,
    discount_percent=None,
    extra_labour=0,
    observations="",
):
    if discount_percent is None:
        discount_percent = get_parameter("default_upfront_discount_percent", "10")
    discount = discount_percent_value(discount_percent)
    labour = labour_value(extra_labour or 0)
    last_error = None
    for _ in range(NUMBER_ALLOCATION_ATTEMPTS):
        try:
            with transaction.atomic():
                proforma = Proforma(
                    site=site,
                    number=next_proforma_number(),
                    status=Proforma.Status.DRAFT,
                    upfront_discount_percent=discount,
                    extra_labour=labour,
                    observations=observations or "",
                    created_by=user,
                    updated_by=user,
                )
                proforma.save()
                recompute_draft_totals(proforma)
                log_activity(
                    action="create_proforma",
                    object_type="proforma",
                    object_id=proforma.pk,
                    actor=user,
                )
                return proforma
        except IntegrityError as exc:
            last_error = exc
    raise ValidationError("Could not allocate a unique proforma number.") from last_error


def update_draft(
    proforma,
    user,
    *,
    upfront_discount_percent=None,
    extra_labour=None,
    observations=None,
):
    require_draft(proforma)
    if upfront_discount_percent is not None:
        proforma.upfront_discount_percent = discount_percent_value(
            upfront_discount_percent
        )
    if extra_labour is not None:
        proforma.extra_labour = labour_value(extra_labour)
    if observations is not None:
        proforma.observations = observations
    proforma.updated_by = user
    proforma.save()
    return recompute_draft_totals(proforma)


def _line_money(model, quantity, extra_tubing, tubing_length):
    quantity = int(quantity)
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.")
    unit_price = money(model.list_price)
    if extra_tubing:
        if tubing_length is None:
            raise ValidationError("Tubing length is required when extra tubing is needed.")
        tubing_amount = money(tubing_length.price)
    else:
        tubing_length = None
        tubing_amount = money(0)
    line_total = money(quantity * (unit_price + tubing_amount))
    return {
        "quantity": quantity,
        "extra_tubing": bool(extra_tubing),
        "tubing_length": tubing_length,
        "unit_price": unit_price,
        "tubing_amount": tubing_amount,
        "line_total": line_total,
    }


def add_line(proforma, model, user, *, quantity=1, extra_tubing=False, tubing_length=None):
    require_draft(proforma)
    values = _line_money(model, quantity, extra_tubing, tubing_length)
    line = ProformaLine.objects.create(
        proforma=proforma,
        model=model,
        created_by=user,
        updated_by=user,
        **values,
    )
    recompute_draft_totals(proforma)
    return line


def update_line(line, user, *, model=None, quantity=None, extra_tubing=None, tubing_length=None):
    proforma = line.proforma
    require_draft(proforma)
    model = model if model is not None else line.model
    quantity = line.quantity if quantity is None else quantity
    extra_tubing = line.extra_tubing if extra_tubing is None else extra_tubing
    if extra_tubing is False:
        tubing_length = None
    elif tubing_length is None:
        tubing_length = line.tubing_length
    values = _line_money(model, quantity, extra_tubing, tubing_length)
    for key, value in values.items():
        setattr(line, key, value)
    line.model = model
    line.updated_by = user
    line.save()
    recompute_draft_totals(proforma)
    return line


def remove_line(line, user):
    require_draft(line.proforma)
    line.soft_delete(user)
    recompute_draft_totals(line.proforma)


def require_delete_permission(user):
    if not getattr(user, "can_delete", False):
        raise PermissionDenied("Only admin can delete.")


def delete_client(client, user):
    require_delete_permission(user)
    if client.sites.exists():
        raise ValidationError("Cannot delete a client that still has sites.")
    client.soft_delete(user)


def delete_site(site, user):
    require_delete_permission(user)
    if site.proformas.exists():
        raise ValidationError("Cannot delete a site that still has proformas.")
    site.soft_delete(user)


def issue_proforma(proforma, user):
    require_draft(proforma)
    if not proforma.lines.exists():
        raise ValidationError("Cannot issue a proforma with no lines.")
    recompute_draft_totals(proforma)
    site = proforma.site
    client = site.client
    proforma.client_name = client.name
    proforma.client_phone = client.phone or ""
    proforma.client_email = client.email or ""
    proforma.site_alias_1 = site.alias_1
    proforma.site_alias_2 = site.alias_2 or ""
    proforma.site_alias_3 = site.alias_3 or ""
    proforma.site_alias_4 = site.alias_4 or ""
    proforma.site_street = site.street or ""
    proforma.site_postal_code = site.postal_code or ""
    proforma.site_city = site.city or ""
    proforma.site_notes = site.notes or ""
    for line in proforma.lines.select_related("model__style__brand", "tubing_length"):
        line.brand_name = line.model.style.brand.name
        line.style_name = line.model.style.name
        line.kind = line.model.kind
        line.btu = line.model.btu
        line.tubing_length_value = (
            line.tubing_length.length if line.tubing_length_id else None
        )
        line.updated_by = user
        line.save()
    proforma.status = Proforma.Status.ISSUED
    proforma.updated_by = user
    proforma.save()
    log_activity(
        action="issue_proforma",
        object_type="proforma",
        object_id=proforma.pk,
        actor=user,
    )
    return proforma


def cancel_proforma(proforma, user):
    if proforma.status != Proforma.Status.ISSUED:
        raise ValidationError("Only issued proformas can be cancelled.")
    proforma.status = Proforma.Status.CANCELLED
    proforma.updated_by = user
    proforma.save(update_fields=["status", "updated_at", "updated_by"])
    log_activity(
        action="cancel_proforma",
        object_type="proforma",
        object_id=proforma.pk,
        actor=user,
    )
    return proforma
