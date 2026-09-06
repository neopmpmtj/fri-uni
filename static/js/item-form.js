document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("item-form");
    if (!form) {
        return;
    }
    const family = form.querySelector("#id_family");
    const subFamily = form.querySelector("#id_sub_family");
    if (!family || !subFamily) {
        return;
    }

    function filterSubFamilies() {
        const familyId = family.value;
        Array.prototype.forEach.call(subFamily.options, function (opt) {
            if (!opt.value) {
                opt.hidden = false;
                opt.disabled = false;
                return;
            }
            const visible = !familyId || opt.getAttribute("data-family") === familyId;
            opt.hidden = !visible;
            opt.disabled = !visible;
        });
        const selected = subFamily.options[subFamily.selectedIndex];
        if (selected && selected.hidden) {
            subFamily.value = "";
        }
    }

    family.addEventListener("change", function () {
        subFamily.value = "";
        filterSubFamilies();
    });
    filterSubFamilies();
});
