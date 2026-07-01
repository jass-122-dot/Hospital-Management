// Generic confirm-modal helper used across the app
function showConfirm(message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        const text = document.getElementById('confirmModalText');
        const yesBtn = document.getElementById('confirmModalYes');
        const noBtn = document.getElementById('confirmModalNo');

        text.textContent = message;
        modal.classList.remove('hidden');

        function cleanup(result) {
            modal.classList.add('hidden');
            yesBtn.removeEventListener('click', onYes);
            noBtn.removeEventListener('click', onNo);
            resolve(result);
        }
        function onYes() { cleanup(true); }
        function onNo() { cleanup(false); }

        yesBtn.addEventListener('click', onYes);
        noBtn.addEventListener('click', onNo);
    });
}

// Logout: clears any client-side token reference before navigating to /logout
document.addEventListener('DOMContentLoaded', function () {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function () {
            try {
                localStorage.removeItem('hms_token');
                sessionStorage.removeItem('hms_token');
            } catch (e) { /* ignore */ }
            // Server-side route /logout also clears the session token & redirects to login
        });
    }
});
