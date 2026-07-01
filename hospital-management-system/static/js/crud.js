function initCrudPage(config) {
    const {
        apiBase, fieldMap, entityLabel, renderRow, emptyColspan,
        readOnly = false
    } = config;

    const tableBody = document.getElementById('tableBody');
    const formModal = document.getElementById('formModal');
    const entityForm = document.getElementById('entityForm');
    const formTitle = document.getElementById('formTitle');
    const addBtn = document.getElementById('addBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    const entityIdInput = document.getElementById('entityId');

    let dirty = false; // tracks whether form has unsaved changes

    function fieldEls() {
        return Object.keys(fieldMap).map(id => document.getElementById(id));
    }

    function markDirty() { dirty = true; }

    function attachDirtyTracking() {
        fieldEls().forEach(el => {
            if (!el) return;
            el.addEventListener('input', markDirty);
            el.addEventListener('change', markDirty);
        });
    }

    function resetForm() {
        entityIdInput.value = '';
        fieldEls().forEach(el => {
            if (!el) return;
            if (el.tagName === 'SELECT') el.selectedIndex = 0;
            else el.value = '';
        });
        dirty = false;
    }

    function openForm(mode, row) {
        resetForm();
        if (mode === 'add') {
            formTitle.textContent = `Add ${entityLabel}`;
        } else {
            formTitle.textContent = `Edit ${entityLabel}`;
            entityIdInput.value = row.id;
            Object.entries(fieldMap).forEach(([elId, key]) => {
                const el = document.getElementById(elId);
                if (el && row[key] !== undefined && row[key] !== null) {
                    el.value = row[key];
                }
            });
        }
        dirty = false;
        formModal.classList.remove('hidden');
        const first = fieldEls().find(Boolean);
        if (first) first.focus();
    }

    async function closeForm(forceCheck) {
        if (forceCheck && dirty) {
            const ok = await showConfirm('Discard unsaved changes?');
            if (!ok) return;
        }
        formModal.classList.add('hidden');
        resetForm();
    }

    async function loadTable() {
        tableBody.innerHTML = `<tr><td colspan="${emptyColspan}" class="empty-row">Loading...</td></tr>`;
        try {
            const res = await fetch(apiBase);
            const rows = await res.json();
            if (!rows.length) {
                tableBody.innerHTML = `<tr><td colspan="${emptyColspan}" class="empty-row">No records found.</td></tr>`;
                return;
            }
            tableBody.innerHTML = rows.map(renderRow).join('');
            attachRowActions(rows);
        } catch (err) {
            tableBody.innerHTML = `<tr><td colspan="${emptyColspan}" class="empty-row">Failed to load data.</td></tr>`;
        }
    }

    function attachRowActions(rows) {
        if (readOnly) return;
        tableBody.querySelectorAll('.btn-edit').forEach(btn => {
            btn.addEventListener('click', () => {
                const row = rows.find(r => String(r.id) === btn.dataset.id);
                if (row) openForm('edit', row);
            });
        });
        tableBody.querySelectorAll('.btn-danger').forEach(btn => {
            btn.addEventListener('click', async () => {
                const ok = await showConfirm(`Delete this ${entityLabel.toLowerCase()}? This cannot be undone.`);
                if (!ok) return;
                await fetch(`${apiBase}/${btn.dataset.id}`, { method: 'DELETE' });
                loadTable(); // auto-refresh
            });
        });
    }

    if (addBtn) {
        addBtn.addEventListener('click', () => openForm('add'));
    }
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => closeForm(true));
    }

    if (entityForm) {
        entityForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {};
            Object.entries(fieldMap).forEach(([elId, key]) => {
                const el = document.getElementById(elId);
                if (el) payload[key] = el.value;
            });

            const id = entityIdInput.value;
            const method = id ? 'PUT' : 'POST';
            const url = id ? `${apiBase}/${id}` : apiBase;

            try {
                const res = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    dirty = false;
                    formModal.classList.add('hidden');
                    resetForm();
                    loadTable(); // auto-refresh after add/edit
                } else {
                    alert('Something went wrong. Please check the form and try again.');
                }
            } catch (err) {
                alert('Network error. Please try again.');
            }
        });
        attachDirtyTracking();
    }

    // Clicking outside the modal box also triggers cancel-confirm
    if (formModal) {
        formModal.addEventListener('click', (e) => {
            if (e.target === formModal) closeForm(true);
        });
    }

    loadTable();
}
