// Enables Enter / ArrowDown to move to next field, ArrowUp to move to previous field.
// Submits the form when Enter is pressed on the last field.
function initFormKeyboardNav(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    function getFields() {
        return Array.from(form.querySelectorAll('[data-nav]'));
    }

    form.addEventListener('keydown', function (e) {
        const fields = getFields();
        const idx = fields.indexOf(e.target);
        if (idx === -1) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            const next = fields[idx + 1];
            if (next) next.focus();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            const prev = fields[idx - 1];
            if (prev) prev.focus();
        } else if (e.key === 'Enter') {
            // allow textareas to insert newline naturally
            if (e.target.tagName === 'TEXTAREA') return;
            e.preventDefault();
            const next = fields[idx + 1];
            if (next) {
                next.focus();
            } else {
                form.requestSubmit ? form.requestSubmit() : form.submit();
            }
        }
    });
}
