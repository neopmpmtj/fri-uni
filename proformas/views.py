from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .forms import ClientForm, NewDraftForm, ProformaHeaderForm, ProformaLineForm, SiteForm
from .models import Client, Proforma, ProformaLine, Site
from .pdf import build_proforma_pdf
from .quote_i18n import quote_labels
from accounts.lang import normalize_lang


def _save_audited(form, user):
    obj = form.save(commit=False)
    obj.updated_by = user
    if not obj.pk:
        obj.created_by = user
    obj.save()
    return obj


def _validation_message(exc):
    if hasattr(exc, "messages"):
        return " ".join(str(message) for message in exc.messages)
    return str(exc)


@login_required
def client_list(request):
    editing = None
    form = ClientForm()
    if request.method == "POST":
        pk = request.POST.get("id")
        if request.POST.get("action") == "delete" and pk:
            try:
                services.delete_client(get_object_or_404(Client, pk=pk), request.user)
            except ValidationError as exc:
                messages.error(request, _validation_message(exc))
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
            try:
                services.delete_site(get_object_or_404(Site, pk=pk), request.user)
            except ValidationError as exc:
                messages.error(request, _validation_message(exc))
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
        if action in {"save_header", "delete_line", "save_line", "issue"} and not is_draft:
            messages.error(request, "Only draft proformas can be edited.")
            return redirect("proforma_detail", pk=proforma.pk)
        if action == "cancel_proforma" and proforma.status != Proforma.Status.ISSUED:
            messages.error(request, "Only issued proformas can be cancelled.")
            return redirect("proforma_detail", pk=proforma.pk)
        try:
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
                line = get_object_or_404(
                    ProformaLine, pk=request.POST.get("id"), proforma=proforma
                )
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
                            model=data["model"],
                            quantity=data["quantity"],
                            extra_tubing=data["extra_tubing"],
                            tubing_length=data["tubing_length"],
                        )
                    else:
                        services.add_line(
                            proforma,
                            data["model"],
                            request.user,
                            quantity=data["quantity"],
                            extra_tubing=data["extra_tubing"],
                            tubing_length=data["tubing_length"],
                        )
                    return redirect("proforma_detail", pk=proforma.pk)
                editing_line = instance
            elif action == "issue" and is_draft:
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
                    proforma.refresh_from_db()
                    services.issue_proforma(proforma, request.user)
                    return redirect("proforma_detail", pk=proforma.pk)
            elif action == "cancel_proforma" and proforma.status == Proforma.Status.ISSUED:
                services.cancel_proforma(proforma, request.user)
                return redirect("proforma_detail", pk=proforma.pk)
        except ValidationError as exc:
            messages.error(request, _validation_message(exc))
            return redirect("proforma_detail", pk=proforma.pk)

    if request.GET.get("line"):
        editing_line = get_object_or_404(
            ProformaLine, pk=request.GET["line"], proforma=proforma
        )
        line_form = ProformaLineForm(instance=editing_line)

    lines = proforma.lines.select_related(
        "model__style__brand", "tubing_length"
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
