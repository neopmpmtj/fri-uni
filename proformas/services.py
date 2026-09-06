from decimal import Decimal
import re

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from decimal import Decimal
import re

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    ActivityLog,
    ActorType,
    ChangeLog,
    Item,
    Parameter,
    Proforma,
    ProformaLine,
    SubFamily,
    TubingLength,
    VatRate,
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


KNOWN_PARAMETER_KEYS = (
    "currency",
    "default_upfront_discount_percent",
    "tubing_length_unit",
)


def get_parameter(key, default=None):
    row = Parameter.objects.filter(key=key).first()
    if row is None:
        return default
    return row.value


def update_equipment_list_price(item, new_price, *, reason, actor):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("A reason is required when changing list price.")
    new_price = Decimal(str(new_price))
    old = Item.all_objects.get(pk=item.pk).list_price
    if old == new_price:
        return item
    item.list_price = new_price
    item.updated_by = actor
    item.save(update_fields=["list_price", "updated_at", "updated_by"])
    log_change(
        entity_type="items",
        entity_id=item.pk,
        field="list_price",
        old_value=old,
        new_value=new_price,
        actor=actor,
        reason=reason,
    )
    return item


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
    return Decimal(str(value)).quantize(TWOPLACES)


def require_draft(proforma):
    if proforma.status != Proforma.Status.DRAFT:
        raise ValidationError("Only draft proformas can be edited.")


def next_proforma_number(year=None):
    year = year or timezone.now().year
    prefix = f"PF-{year}-"
    existing = (
        Proforma.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = int(existing.rsplit("-", 1)[-1]) + 1 if existing else 1
    return f"{prefix}{seq:04d}"


def recompute_draft_totals(proforma):
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
    proforma = Proforma(
        site=site,
        number=next_proforma_number(),
        status=Proforma.Status.DRAFT,
        upfront_discount_percent=Decimal(str(discount_percent)),
        extra_labour=money(extra_labour or 0),
        observations=observations or "",
        created_by=user,
        updated_by=user,
    )
    proforma.save()
    return recompute_draft_totals(proforma)


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
        proforma.upfront_discount_percent = Decimal(str(upfront_discount_percent))
    if extra_labour is not None:
        proforma.extra_labour = money(extra_labour)
    if observations is not None:
        proforma.observations = observations
    proforma.updated_by = user
    proforma.save()
    return recompute_draft_totals(proforma)


def _line_money(item, quantity, extra_tubing, tubing_length):
    quantity = int(quantity)
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.")
    unit_price = money(item.list_price)
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


def add_line(proforma, item, user, *, quantity=1, extra_tubing=False, tubing_length=None):
    require_draft(proforma)
    values = _line_money(item, quantity, extra_tubing, tubing_length)
    line = ProformaLine.objects.create(
        proforma=proforma,
        item=item,
        created_by=user,
        updated_by=user,
        **values,
    )
    recompute_draft_totals(proforma)
    return line


def update_line(line, user, *, item=None, quantity=None, extra_tubing=None, tubing_length=None):
    proforma = line.proforma
    require_draft(proforma)
    item = item if item is not None else line.item
    quantity = line.quantity if quantity is None else quantity
    extra_tubing = line.extra_tubing if extra_tubing is None else extra_tubing
    if extra_tubing is False:
        tubing_length = None
    elif tubing_length is None:
        tubing_length = line.tubing_length
    values = _line_money(item, quantity, extra_tubing, tubing_length)
    for key, value in values.items():
        setattr(line, key, value)
    line.item = item
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
    client.soft_delete(user)


def delete_site(site, user):
    require_delete_permission(user)
    site.soft_delete(user)


def delete_family(family, user):
    require_delete_permission(user)
    family.soft_delete(user)


def delete_sub_family(sub_family, user):
    require_delete_permission(user)
    sub_family.soft_delete(user)


def delete_brand(brand, user):
    require_delete_permission(user)
    brand.soft_delete(user)


def delete_item(item, user):
    require_delete_permission(user)
    item.soft_delete(user)


def delete_vat_rate(vat_rate, user):
    require_delete_permission(user)
    if Item.objects.filter(vat_rate=vat_rate).exists():
        raise ValidationError("Cannot delete a VAT rate that is used by items.")
    vat_rate.soft_delete(user)


def delete_tubing_length(tubing, user):
    require_delete_permission(user)
    if ProformaLine.objects.filter(tubing_length=tubing).exists():
        raise ValidationError("Cannot delete a tubing length that is used on a proforma.")
    tubing.soft_delete(user)


INTERNAL_CODE_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
VAT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def normalize_internal_code(internal_code):
    return (internal_code or "").strip().upper()


def validate_internal_code(internal_code, *, exclude_item_id=None):
    code = normalize_internal_code(internal_code)
    if not code:
        raise ValidationError("Internal code is required.")
    if INTERNAL_CODE_PATTERN.fullmatch(code) is None:
        raise ValidationError(
            "Internal code may only contain letters, digits, dots, hyphens, and underscores."
        )
    qs = Item.objects.filter(internal_code__iexact=code)
    if exclude_item_id:
        qs = qs.exclude(pk=exclude_item_id)
    if qs.exists():
        raise ValidationError(f'Internal code "{code}" is already used by another item.')
    return code


def _clear_other_defaults(instance):
    if not getattr(instance, "is_default", False):
        return
    model = type(instance)
    qs = model.objects.filter(is_default=True)
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    if isinstance(instance, SubFamily):
        qs = qs.filter(family_id=instance.family_id)
    elif isinstance(instance, Item):
        qs = qs.filter(sub_family_id=instance.sub_family_id, brand_id=instance.brand_id)
    qs.update(is_default=False)


def percent_to_rate(percent):
    value = Decimal(str(percent))
    if value < 0 or value > 100:
        raise ValidationError("VAT percent must be between 0 and 100.")
    return (value / Decimal("100")).quantize(Decimal("0.0001"))


def normalize_vat_code(code):
    return (code or "").strip().upper()


def validate_vat_code(code, *, exclude_id=None):
    normalized = normalize_vat_code(code)
    if not normalized:
        raise ValidationError("VAT code is required.")
    if VAT_CODE_PATTERN.fullmatch(normalized) is None:
        raise ValidationError(
            "VAT code may only contain letters, digits, dots, hyphens, and underscores."
        )
    qs = VatRate.objects.filter(code__iexact=normalized)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    if qs.exists():
        raise ValidationError(f'VAT code "{normalized}" is already used.')
    return normalized


@transaction.atomic
def save_audited(instance, user):
    _clear_other_defaults(instance)
    instance.updated_by = user
    if not instance.pk:
        instance.created_by = user
    instance.save()
    return instance


def save_item(item, user):
    item.internal_code = validate_internal_code(
        item.internal_code, exclude_item_id=item.pk
    )
    return save_audited(item, user)


def save_vat_rate(vat_rate, user):
    vat_rate.code = validate_vat_code(vat_rate.code, exclude_id=vat_rate.pk)
    return save_audited(vat_rate, user)


@transaction.atomic
def save_tubing_length(tubing, user, *, reason=""):
    new_length = tubing.length
    new_price = tubing.price
    if tubing.pk:
        original = TubingLength.all_objects.get(pk=tubing.pk)
        if original.price != new_price:
            update_tubing_price(original, new_price, reason=reason, actor=user)
            tubing.refresh_from_db()
        tubing.length = new_length
        tubing.price = new_price
    return save_audited(tubing, user)


def save_parameter(parameter, user):
    return save_audited(parameter, user)


def issue_proforma(proforma, user):
    require_draft(proforma)
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
    for line in proforma.lines.select_related(
        "item__sub_family__family", "item__brand", "tubing_length"
    ):
        line.brand_name = line.item.brand.name
        line.family_name = line.item.sub_family.family.name
        line.sub_family_name = line.item.sub_family.name
        line.internal_code = line.item.internal_code
        line.kind = line.item.kind
        line.btu = line.item.btu
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
