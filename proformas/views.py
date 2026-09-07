from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .forms import (
    BrandForm,
    ClientForm,
    FamilyForm,
    ItemForm,
    ItemPriceForm,
    NewDraftForm,
    ParameterForm,
    PowerForm,
    ProformaHeaderForm,
    ProformaLineForm,
    SiteForm,
    SubFamilyForm,
    TubingLengthForm,
    VatRateForm,
)
from .models import (
    Brand,
    Client,
    Family,
    Item,
    Parameter,
    Power,
    Proforma,
    ProformaLine,
    Site,
    SubFamily,
    TubingLength,
    VatRate,
)
from .pdf import build_proforma_pdf
from .quote_i18n import quote_labels
from accounts.lang import normalize_lang


ITEM_SORT_FIELDS = {
    "internal_code": ["internal_code"],
    "family": ["sub_family__family__name"],
    "sub_family": ["sub_family__name"],
    "manufacturer": ["brand__name"],
    "kind": ["kind"],
    "power": ["power__power", "power__unit"],
}


def _item_sort_context(request):
    sort = request.GET.get("sort", "internal_code").strip()
    if sort not in ITEM_SORT_FIELDS:
        sort = "internal_code"
    direction = request.GET.get("dir", "asc").strip().lower()
    if direction not in ("asc", "desc"):
        direction = "asc"

    def link_for(col):
        params = request.GET.copy()
        if col == sort and direction == "asc":
            params["dir"] = "desc"
        else:
            params["dir"] = "asc"
        params["sort"] = col
        return params.urlencode()

    prefix = "-" if direction == "desc" else ""
    ordering = [f"{prefix}{field}" for field in ITEM_SORT_FIELDS[sort]]
    if sort != "internal_code":
        ordering.append("internal_code")

    return {
        "sort": sort,
        "dir": direction,
        "sort_urls": {col: link_for(col) for col in ITEM_SORT_FIELDS},
        "ordering": ordering,
    }


def _save_audited(form, user):
    obj = form.save(commit=False)
    obj.updated_by = user
    if not obj.pk:
        obj.created_by = user
    obj.save()
    return obj


@login_required
def client_list(request):
    editing = None
    form = ClientForm()
    if request.method == "POST":
        pk = request.POST.get("id")
        if request.POST.get("action") == "delete" and pk:
            services.delete_client(get_object_or_404(Client, pk=pk), request.user)
            return redirect("client_list")
        instance = get_object_or_404(Client, pk=pk) if pk else None
        form = ClientForm(request.POST, instance=instance)
        if form.is_valid():
            _save_audited(form, request.user)
            return redirect("client_list")
        editing = instance
    elif request.GET.get("id"):
        editing = get_object_or_404(Client, pk=request.GET["id"])
        form = ClientForm(instance=editing)

    q = request.GET.get("q", "").strip()
    clients = Client.objects.order_by("name")
    if q:
        clients = clients.filter(name__icontains=q)

    drawer_open = bool(editing or form.errors or request.GET.get("new"))
    return render(
        request,
        "proformas/client_list.html",
        {
            "clients": clients,
            "form": form,
            "editing": editing,
            "q": q,
            "drawer_open": drawer_open,
            "nav_active": "clients",
            "page_title": "Clients",
        },
    )


@login_required
def site_list(request):
    editing = None
    form = SiteForm()
    if request.method == "POST":
        pk = request.POST.get("id")
        if request.POST.get("action") == "delete" and pk:
            services.delete_site(get_object_or_404(Site, pk=pk), request.user)
            return redirect("site_list")
        instance = get_object_or_404(Site, pk=pk) if pk else None
        form = SiteForm(request.POST, instance=instance)
        if form.is_valid():
            _save_audited(form, request.user)
            return redirect("site_list")
        editing = instance
    elif request.GET.get("id"):
        editing = get_object_or_404(Site, pk=request.GET["id"])
        form = SiteForm(instance=editing)

    q = request.GET.get("q", "").strip()
    client_id = request.GET.get("client", "").strip()
    sites = Site.objects.select_related("client").order_by("alias_1")
    if q:
        sites = sites.filter(alias_1__icontains=q)
    if client_id:
        sites = sites.filter(client_id=client_id)

    drawer_open = bool(editing or form.errors or request.GET.get("new"))
    return render(
        request,
        "proformas/site_list.html",
        {
            "sites": sites,
            "form": form,
            "editing": editing,
            "q": q,
            "client_id": client_id,
            "clients": Client.objects.order_by("name"),
            "drawer_open": drawer_open,
            "nav_active": "sites",
            "page_title": "Sites",
        },
    )


@login_required
def proforma_list(request):
    draft_form = NewDraftForm()
    if request.method == "POST" and request.POST.get("action") == "create":
        draft_form = NewDraftForm(request.POST)
        if draft_form.is_valid():
            proforma = services.create_draft(draft_form.cleaned_data["site"], request.user)
            return redirect("proforma_detail", pk=proforma.pk)

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    rows = Proforma.objects.select_related("site__client").order_by("-updated_at")
    if q:
        rows = rows.filter(number__icontains=q)
    if status:
        rows = rows.filter(status=status)

    drawer_open = bool(draft_form.errors or request.GET.get("new"))
    return render(
        request,
        "proformas/proforma_list.html",
        {
            "proformas": rows,
            "draft_form": draft_form,
            "q": q,
            "status": status,
            "drawer_open": drawer_open,
            "nav_active": "proformas",
            "page_title": "Proformas",
            "status_choices": Proforma.Status.choices,
        },
    )


@login_required
def proforma_detail(request, pk):
    proforma = get_object_or_404(
        Proforma.objects.select_related("site__client"), pk=pk
    )
    is_draft = proforma.status == Proforma.Status.DRAFT
    header_form = ProformaHeaderForm(
        initial={
            "upfront_discount_percent": proforma.upfront_discount_percent,
            "extra_labour": proforma.extra_labour,
            "observations": proforma.observations,
        }
    )
    line_form = ProformaLineForm()
    editing_line = None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_header" and is_draft:
            header_form = ProformaHeaderForm(request.POST)
            if header_form.is_valid():
                services.update_draft(
                    proforma,
                    request.user,
                    upfront_discount_percent=header_form.cleaned_data[
                        "upfront_discount_percent"
                    ],
                    extra_labour=header_form.cleaned_data["extra_labour"],
                    observations=header_form.cleaned_data["observations"],
                )
                return redirect("proforma_detail", pk=proforma.pk)
        elif action == "delete_line" and is_draft:
            line = get_object_or_404(ProformaLine, pk=request.POST.get("id"), proforma=proforma)
            services.remove_line(line, request.user)
            return redirect("proforma_detail", pk=proforma.pk)
        elif action == "save_line" and is_draft:
            pk_line = request.POST.get("id")
            instance = (
                get_object_or_404(ProformaLine, pk=pk_line, proforma=proforma)
                if pk_line
                else None
            )
            line_form = ProformaLineForm(request.POST, instance=instance)
            if line_form.is_valid():
                data = line_form.cleaned_data
                if instance:
                    services.update_line(
                        instance,
                        request.user,
                        item=data["item"],
                        quantity=data["quantity"],
                        extra_tubing=data["extra_tubing"],
                        tubing_length=data["tubing_length"],
                    )
                else:
                    services.add_line(
                        proforma,
                        data["item"],
                        request.user,
                        quantity=data["quantity"],
                        extra_tubing=data["extra_tubing"],
                        tubing_length=data["tubing_length"],
                    )
                return redirect("proforma_detail", pk=proforma.pk)
            editing_line = instance
        elif action == "issue" and is_draft:
            services.issue_proforma(proforma, request.user)
            return redirect("proforma_detail", pk=proforma.pk)
        elif action == "cancel_proforma" and proforma.status == Proforma.Status.ISSUED:
            services.cancel_proforma(proforma, request.user)
            return redirect("proforma_detail", pk=proforma.pk)

    if request.GET.get("line"):
        editing_line = get_object_or_404(
            ProformaLine, pk=request.GET["line"], proforma=proforma
        )
        line_form = ProformaLineForm(instance=editing_line)

    lines = proforma.lines.select_related(
        "item__sub_family__family", "item__brand", "item__power", "tubing_length"
    ).order_by("pk")
    drawer_open = bool(
        editing_line or line_form.errors or request.GET.get("new_line")
    )
    is_draft = proforma.status == Proforma.Status.DRAFT
    if not is_draft:
        for field in header_form.fields.values():
            field.disabled = True
    return render(
        request,
        "proformas/proforma_detail.html",
        {
            "proforma": proforma,
            "lines": lines,
            "header_form": header_form,
            "line_form": line_form,
            "editing_line": editing_line,
            "drawer_open": drawer_open,
            "is_draft": is_draft,
            "is_issued": proforma.status == Proforma.Status.ISSUED,
            "is_cancelled": proforma.status == Proforma.Status.CANCELLED,
            "nav_active": "proformas",
            "page_title": proforma.number,
        },
    )


def _quote_lang(request):
    return normalize_lang(request.COOKIES.get("fu-lang", "en"))


def _issued_or_cancelled(proforma):
    if proforma.status == Proforma.Status.DRAFT:
        raise Http404("Quote is available after issue.")
    return proforma


@login_required
def proforma_quote(request, pk):
    proforma = _issued_or_cancelled(
        get_object_or_404(Proforma.objects.select_related("site"), pk=pk)
    )
    lang = _quote_lang(request)
    return render(
        request,
        "proformas/quote.html",
        {
            "proforma": proforma,
            "lines": proforma.lines.all(),
            "labels": quote_labels(lang),
            "company_name": "fri-uni",
            "nav_active": "proformas",
            "page_title": proforma.number,
        },
    )


@login_required
def proforma_pdf(request, pk):
    proforma = _issued_or_cancelled(get_object_or_404(Proforma, pk=pk))
    lang = _quote_lang(request)
    pdf_bytes = build_proforma_pdf(proforma, lang=lang)
    services.log_activity(
        action="download_pdf",
        object_type="proforma",
        object_id=proforma.pk,
        actor=request.user,
    )
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{proforma.number}.pdf"'
    return response


def _drawer_list(
    request,
    *,
    model,
    form_class,
    template,
    redirect_name,
    delete_fn,
    nav_active,
    page_title,
    extra_context=None,
    save_fn=None,
):
    editing = None
    form = form_class()
    if request.method == "POST":
        pk = request.POST.get("id")
        if request.POST.get("action") == "delete" and pk:
            instance = get_object_or_404(model, pk=pk)
            try:
                delete_fn(instance, request.user)
            except ValidationError as exc:
                form = form_class(instance=instance)
                form.add_error(None, exc)
                editing = instance
            else:
                return redirect(redirect_name)
        else:
            instance = get_object_or_404(model, pk=pk) if pk else None
            form = form_class(request.POST, instance=instance)
            if form.is_valid():
                obj = form.save(commit=False)
                if save_fn:
                    save_fn(obj, request.user)
                elif isinstance(obj, Item):
                    services.save_item(obj, request.user)
                else:
                    services.save_audited(obj, request.user)
                return redirect(redirect_name)
            editing = instance
    elif request.GET.get("id"):
        editing = get_object_or_404(model, pk=request.GET["id"])
        form = form_class(instance=editing)

    drawer_open = bool(editing or form.errors or request.GET.get("new"))
    context = {
        "form": form,
        "editing": editing,
        "drawer_open": drawer_open,
        "nav_active": nav_active,
        "page_title": page_title,
    }
    if extra_context:
        context.update(extra_context)
    return render(request, template, context)


@login_required
def family_list(request):
    q = request.GET.get("q", "").strip()
    rows = Family.objects.order_by("name")
    if q:
        rows = rows.filter(name__icontains=q)
    return _drawer_list(
        request,
        model=Family,
        form_class=FamilyForm,
        template="proformas/family_list.html",
        redirect_name="family_list",
        delete_fn=services.delete_family,
        nav_active="",
        page_title="Families",
        extra_context={"families": rows, "q": q},
    )


@login_required
def sub_family_list(request):
    q = request.GET.get("q", "").strip()
    family_id = request.GET.get("family", "").strip()
    rows = SubFamily.objects.select_related("family", "brand").order_by("family__name", "name")
    if q:
        rows = rows.filter(name__icontains=q)
    if family_id:
        rows = rows.filter(family_id=family_id)
    return _drawer_list(
        request,
        model=SubFamily,
        form_class=SubFamilyForm,
        template="proformas/sub_family_list.html",
        redirect_name="sub_family_list",
        delete_fn=services.delete_sub_family,
        nav_active="",
        page_title="Sub-families",
        extra_context={
            "sub_families": rows,
            "q": q,
            "family_id": family_id,
            "families": Family.objects.order_by("name"),
        },
    )


@login_required
def manufacturer_list(request):
    q = request.GET.get("q", "").strip()
    rows = Brand.objects.order_by("name")
    if q:
        rows = rows.filter(name__icontains=q)
    return _drawer_list(
        request,
        model=Brand,
        form_class=BrandForm,
        template="proformas/manufacturer_list.html",
        redirect_name="manufacturer_list",
        delete_fn=services.delete_brand,
        nav_active="",
        page_title="Manufacturers",
        extra_context={"manufacturers": rows, "q": q},
    )


@login_required
def manufacturer_pricelist(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    editing = None
    form = ItemPriceForm()
    if request.method == "POST":
        item = get_object_or_404(Item, pk=request.POST.get("id"), brand=brand)
        form = ItemPriceForm(request.POST)
        if form.is_valid():
            try:
                services.update_equipment_list_price(
                    item,
                    form.cleaned_data["list_price"],
                    reason=form.cleaned_data.get("reason"),
                    actor=request.user,
                )
            except ValidationError as exc:
                form.add_error("reason", exc)
                editing = item
            else:
                return redirect("manufacturer_pricelist", pk=brand.pk)
        editing = item
    elif request.GET.get("id"):
        editing = get_object_or_404(Item, pk=request.GET["id"], brand=brand)
        form = ItemPriceForm(initial={"list_price": editing.list_price})

    q = request.GET.get("q", "").strip()
    items = (
        Item.objects.filter(brand=brand)
        .select_related("sub_family__family", "power")
        .order_by("internal_code")
    )
    if q:
        items = items.filter(internal_code__icontains=q)
    drawer_open = bool(editing or form.errors)
    return render(
        request,
        "proformas/manufacturer_pricelist.html",
        {
            "brand": brand,
            "items": items,
            "form": form,
            "editing": editing,
            "q": q,
            "drawer_open": drawer_open,
            "nav_active": "",
            "page_title": brand.name,
        },
    )


@login_required
def item_list(request):
    q = request.GET.get("q", "").strip()
    family_id = request.GET.get("family", "").strip()
    brand_id = request.GET.get("brand", "").strip()
    sort_ctx = _item_sort_context(request)
    rows = Item.objects.select_related(
        "sub_family__family", "brand", "vat_rate", "power"
    ).order_by(*sort_ctx["ordering"])
    if q:
        rows = rows.filter(internal_code__icontains=q)
    if family_id:
        rows = rows.filter(sub_family__family_id=family_id)
    if brand_id:
        rows = rows.filter(brand_id=brand_id)
    extra = {
        "items": rows,
        "q": q,
        "family_id": family_id,
        "brand_id": brand_id,
        "families": Family.objects.order_by("name"),
        "manufacturers": Brand.objects.order_by("name"),
        "sort": sort_ctx["sort"],
        "dir": sort_ctx["dir"],
        "sort_urls": sort_ctx["sort_urls"],
    }
    return _drawer_list(
        request,
        model=Item,
        form_class=ItemForm,
        template="proformas/item_list.html",
        redirect_name="item_list",
        delete_fn=services.delete_item,
        nav_active="items",
        page_title="Items",
        extra_context=extra,
    )


@login_required
def power_list(request):
    q = request.GET.get("q", "").strip()
    rows = Power.objects.order_by("power", "unit")
    if q:
        rows = rows.filter(unit__icontains=q) | rows.filter(power__icontains=q)
        rows = rows.distinct()
    return _drawer_list(
        request,
        model=Power,
        form_class=PowerForm,
        template="proformas/power_list.html",
        redirect_name="power_list",
        delete_fn=services.delete_power,
        nav_active="",
        page_title="Powers",
        extra_context={"powers": rows, "q": q},
        save_fn=services.save_power,
    )


@login_required
def vat_rate_list(request):
    q = request.GET.get("q", "").strip()
    rows = VatRate.objects.order_by("rate")
    if q:
        rows = rows.filter(code__icontains=q) | rows.filter(label__icontains=q)
        rows = rows.distinct()
    return _drawer_list(
        request,
        model=VatRate,
        form_class=VatRateForm,
        template="proformas/vat_rate_list.html",
        redirect_name="vat_rate_list",
        delete_fn=services.delete_vat_rate,
        nav_active="",
        page_title="VAT rates",
        extra_context={"vat_rates": rows, "q": q},
        save_fn=services.save_vat_rate,
    )


@login_required
def parameter_list(request):
    editing = None
    form = ParameterForm()
    if request.method == "POST":
        pk = request.POST.get("id")
        if not pk or request.POST.get("action") == "delete":
            raise Http404()
        instance = get_object_or_404(
            Parameter, pk=pk, key__in=services.KNOWN_PARAMETER_KEYS
        )
        form = ParameterForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            services.save_parameter(obj, request.user)
            return redirect("parameter_list")
        editing = instance
    elif request.GET.get("id"):
        editing = get_object_or_404(
            Parameter, pk=request.GET["id"], key__in=services.KNOWN_PARAMETER_KEYS
        )
        form = ParameterForm(instance=editing)

    rows = Parameter.objects.filter(key__in=services.KNOWN_PARAMETER_KEYS).order_by(
        "key"
    )
    drawer_open = bool(editing or form.errors)
    return render(
        request,
        "proformas/parameter_list.html",
        {
            "parameters": rows,
            "form": form,
            "editing": editing,
            "drawer_open": drawer_open,
            "nav_active": "",
            "page_title": "Parameters",
        },
    )


@login_required
def tubing_length_list(request):
    editing = None
    form = TubingLengthForm()
    if request.method == "POST":
        pk = request.POST.get("id")
        if request.POST.get("action") == "delete" and pk:
            instance = get_object_or_404(TubingLength, pk=pk)
            try:
                services.delete_tubing_length(instance, request.user)
            except ValidationError as exc:
                form = TubingLengthForm(instance=instance)
                form.add_error(None, exc)
                editing = instance
            else:
                return redirect("tubing_length_list")
        else:
            instance = get_object_or_404(TubingLength, pk=pk) if pk else None
            form = TubingLengthForm(request.POST, instance=instance)
            if form.is_valid():
                obj = form.save(commit=False)
                try:
                    services.save_tubing_length(
                        obj,
                        request.user,
                        reason=form.cleaned_data.get("reason", ""),
                    )
                except ValidationError as exc:
                    form.add_error("reason", exc)
                    editing = instance
                else:
                    return redirect("tubing_length_list")
            editing = instance
    elif request.GET.get("id"):
        editing = get_object_or_404(TubingLength, pk=request.GET["id"])
        form = TubingLengthForm(instance=editing)

    q = request.GET.get("q", "").strip()
    rows = TubingLength.objects.order_by("length")
    if q:
        try:
            rows = rows.filter(length=Decimal(q.replace(",", ".")))
        except InvalidOperation:
            rows = rows.none()
    drawer_open = bool(editing or form.errors or request.GET.get("new"))
    return render(
        request,
        "proformas/tubing_length_list.html",
        {
            "tubing_lengths": rows,
            "form": form,
            "editing": editing,
            "q": q,
            "drawer_open": drawer_open,
            "nav_active": "",
            "page_title": "Tubing lengths",
        },
    )



