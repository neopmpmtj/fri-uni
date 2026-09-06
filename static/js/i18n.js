const LANG_KEY = "fu-lang";

const FU_I18N = {
    en: {
        appName: "Proformas",
        language: "Language",
        settings: "Settings",
        settingsAria: "Settings",
        signOut: "Sign out",
        signedInAs: "Signed in as",
        home: "Home",
        clients: "Clients",
        sites: "Sites",
        proformas: "Proformas",
        catalogAdmin: "Catalog (Django admin)",
        catalogAdminDesc: "Brands, models, tubing, and parameters.",
        clientsDesc: "Customer organisations.",
        sitesDesc: "Work locations.",
        proformasDesc: "Draft, issue, and download quotes.",
        login: "Sign in",
        loginTitle: "Sign in",
        email: "Email",
        password: "Password",
        dashboardTitle: "Proformas",
        dashboardLead: "Choose a workspace.",
        comingSoon: "This workspace will be available in a later step.",
        search: "Search",
        newClient: "New client",
        newSite: "New site",
        newDraft: "New draft",
        save: "Save",
        close: "Close",
        edit: "Edit",
        delete: "Delete",
        name: "Name",
        phone: "Phone",
        actions: "Actions",
        client: "Client",
        alias1: "Alias 1",
        alias2: "Alias 2",
        alias3: "Alias 3",
        alias4: "Alias 4",
        street: "Street",
        postalCode: "Postal code",
        city: "City",
        notes: "Notes",
        filterClient: "Filter by client",
        allClients: "All clients",
        number: "Number",
        status: "Status",
        grandTotal: "Grand total",
        updated: "Updated",
        addLine: "Add line",
        issue: "Issue",
        cancel: "Cancel",
        viewQuote: "View quote",
        downloadPdf: "Download PDF",
        model: "Model",
        quantity: "Quantity",
        extraTubing: "Extra tubing",
        tubingLength: "Tubing length",
        lineTotal: "Line total",
        discountPercent: "Upfront discount %",
        extraLabour: "Extra labour",
        observations: "Observations",
        equipmentSubtotal: "Equipment",
        tubingTotal: "Tubing",
        discountAmount: "Discount",
        draft: "Draft",
        issued: "Issued",
        cancelled: "Cancelled",
        empty: "No rows yet.",
        site: "Site",
        allStatuses: "All statuses",
    },
    "pt-PT": {
        appName: "Proformas",
        language: "Idioma",
        settings: "Definições",
        settingsAria: "Definições",
        signOut: "Terminar sessão",
        signedInAs: "Sessão iniciada como",
        home: "Início",
        clients: "Clientes",
        sites: "Locais",
        proformas: "Proformas",
        catalogAdmin: "Catálogo (Django admin)",
        catalogAdminDesc: "Marcas, modelos, tubos e parâmetros.",
        clientsDesc: "Organizações cliente.",
        sitesDesc: "Locais de trabalho.",
        proformasDesc: "Rascunhos, emissão e descarga de orçamentos.",
        login: "Iniciar sessão",
        loginTitle: "Iniciar sessão",
        email: "Email",
        password: "Palavra-passe",
        dashboardTitle: "Proformas",
        dashboardLead: "Escolha um espaço de trabalho.",
        comingSoon: "Este espaço estará disponível num passo seguinte.",
        search: "Pesquisar",
        newClient: "Novo cliente",
        newSite: "Novo local",
        newDraft: "Novo rascunho",
        save: "Guardar",
        close: "Fechar",
        edit: "Editar",
        delete: "Eliminar",
        name: "Nome",
        phone: "Telefone",
        actions: "Acções",
        client: "Cliente",
        alias1: "Alias 1",
        alias2: "Alias 2",
        alias3: "Alias 3",
        alias4: "Alias 4",
        street: "Rua",
        postalCode: "Código postal",
        city: "Cidade",
        notes: "Notas",
        filterClient: "Filtrar por cliente",
        allClients: "Todos os clientes",
        number: "Número",
        status: "Estado",
        grandTotal: "Total",
        updated: "Actualizado",
        addLine: "Adicionar linha",
        issue: "Emitir",
        cancel: "Anular",
        viewQuote: "Ver orçamento",
        downloadPdf: "Descarregar PDF",
        model: "Modelo",
        quantity: "Quantidade",
        extraTubing: "Tubo extra",
        tubingLength: "Comprimento do tubo",
        lineTotal: "Total da linha",
        discountPercent: "Desconto pagamento antecipado %",
        extraLabour: "Mão de obra extra",
        observations: "Observações",
        equipmentSubtotal: "Equipamento",
        tubingTotal: "Tubo",
        discountAmount: "Desconto",
        draft: "Rascunho",
        issued: "Emitida",
        cancelled: "Anulada",
        empty: "Ainda não há linhas.",
        site: "Local",
        allStatuses: "Todos os estados",
    },
};
FU_I18N.pt = FU_I18N["pt-PT"];

function safeGet(key, fallback) {
    try {
        return localStorage.getItem(key) || fallback;
    } catch (error) {
        return fallback;
    }
}

function safeSet(key, value) {
    try {
        localStorage.setItem(key, value);
    } catch (error) {
        /* blocked storage */
    }
}

function normalizeLang(raw) {
    if (raw && String(raw).toLowerCase().startsWith("pt")) {
        return "pt";
    }
    return "en";
}

function currentLang() {
    return normalizeLang(safeGet(LANG_KEY, "en"));
}

function setLangCookie(lang) {
    document.cookie = "fu-lang=" + encodeURIComponent(lang) + "; path=/; SameSite=Lax";
}

function persistLang(lang) {
    const normalized = normalizeLang(lang);
    safeSet(LANG_KEY, normalized);
    setLangCookie(normalized);
    document.documentElement.lang = normalized === "pt" ? "pt-PT" : "en";
    document.dispatchEvent(new CustomEvent("fu-lang-changed"));
}

function t(key, vars) {
    const dict = FU_I18N[currentLang()] || FU_I18N.en;
    let text = dict[key] || FU_I18N.en[key] || key;
    if (vars) {
        Object.entries(vars).forEach(([name, value]) => {
            text = text.replaceAll(`{${name}}`, String(value));
        });
    }
    return text;
}

function applyStaticI18n() {
    const lang = currentLang();
    document.documentElement.lang = lang === "pt" ? "pt-PT" : "en";
    document.querySelectorAll("[data-i18n]").forEach((node) => {
        node.textContent = t(node.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
        node.setAttribute("placeholder", t(node.getAttribute("data-i18n-placeholder")));
    });
    document.querySelectorAll("[data-i18n-aria]").forEach((node) => {
        node.setAttribute("aria-label", t(node.getAttribute("data-i18n-aria")));
    });
}

document.addEventListener("DOMContentLoaded", function () {
    const lang = currentLang();
    persistLang(lang);
    applyStaticI18n();
    document.addEventListener("fu-lang-changed", applyStaticI18n);
});
