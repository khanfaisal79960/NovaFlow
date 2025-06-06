document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const lightIcon = document.querySelector('[data-theme-icon-light]');
    const darkIcon = document.querySelector('[data-theme-icon-dark]');

    function updateThemeIcons() {
        if (themeToggle.checked) {
            // Dark mode is active
            lightIcon.style.display = 'none';
            darkIcon.style.display = 'inline-block';
        } else {
            // Light mode is active
            lightIcon.style.display = 'inline-block';
            darkIcon.style.display = 'none';
        }
    }

    // Initial update of icons based on current theme
    updateThemeIcons();

    if (themeToggle) {
        themeToggle.addEventListener('change', function() {
            fetch('/toggle_theme')
                .then(response => {
                    if (response.ok) {
                        // Reload the page to apply theme from Flask session,
                        // or fetch current theme and update classes
                        // For simplicity, we'll reload.
                        window.location.reload();
                    } else {
                        console.error('Failed to toggle theme');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        });
    }
});