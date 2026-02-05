/**
 * Assessment Wizard JavaScript
 * Handles autosave, step navigation, and form validation
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('wizard-form');
    if (!form) return;

    const systemId = form.dataset.systemId;
    const STORAGE_KEY = `sdrm_wizard_${systemId}`;

    // Load saved progress
    function loadProgress() {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (!saved) return;

        try {
            const data = JSON.parse(saved);
            for (const [key, value] of Object.entries(data)) {
                const elements = form.querySelectorAll(`[name="${key}"]`);
                elements.forEach(el => {
                    if (el.type === 'checkbox') {
                        const values = Array.isArray(value) ? value : [value];
                        el.checked = values.includes(el.value);
                    } else if (el.type === 'radio') {
                        el.checked = (el.value === value);
                    } else {
                        el.value = value;
                    }
                });
            }
        } catch (e) {
            console.error('Failed to load saved progress:', e);
        }
    }

    // Save progress to localStorage
    function saveProgress() {
        const formData = new FormData(form);
        const data = {};

        for (const [key, value] of formData.entries()) {
            if (data[key]) {
                if (!Array.isArray(data[key])) {
                    data[key] = [data[key]];
                }
                data[key].push(value);
            } else {
                data[key] = value;
            }
        }

        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }

    // Clear saved progress
    function clearProgress() {
        localStorage.removeItem(STORAGE_KEY);
    }

    // Handle Unknown checkbox for data types
    const unknownCheckbox = form.querySelector('[name="data_types_unknown"]');
    const dataTypeCheckboxes = form.querySelectorAll('[name="data_types"]');

    if (unknownCheckbox && dataTypeCheckboxes.length) {
        unknownCheckbox.addEventListener('change', () => {
            if (unknownCheckbox.checked) {
                dataTypeCheckboxes.forEach(cb => {
                    cb.checked = false;
                    cb.disabled = true;
                });
            } else {
                dataTypeCheckboxes.forEach(cb => {
                    cb.disabled = false;
                });
            }
        });

        // Also handle the reverse - uncheck Unknown if any data type is selected
        dataTypeCheckboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                if (cb.checked && unknownCheckbox.checked) {
                    unknownCheckbox.checked = false;
                }
            });
        });
    }

    // Load saved progress on page load
    loadProgress();

    // Save on any input change
    form.addEventListener('change', saveProgress);

    // Clear on successful submit
    form.addEventListener('submit', () => {
        clearProgress();
    });

    // Add visual feedback when data is saved
    let saveTimeout;
    form.addEventListener('change', () => {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => {
            const indicator = document.createElement('div');
            indicator.className = 'save-indicator';
            indicator.textContent = 'Progress saved';
            indicator.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #22c55e;
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 4px;
                font-size: 0.875rem;
                animation: fadeOut 2s forwards;
                z-index: 1000;
            `;
            document.body.appendChild(indicator);
            setTimeout(() => indicator.remove(), 2000);
        }, 500);
    });

    // Add animation style
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeOut {
            0%, 70% { opacity: 1; }
            100% { opacity: 0; }
        }
    `;
    document.head.appendChild(style);
});
