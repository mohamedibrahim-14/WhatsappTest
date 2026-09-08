(function () {
    'use strict';

    function updateStateAndPhoneFields() {
        var countrySelect = document.getElementById('country_id');
        var stateWrapper = document.querySelector('.field-state'); 
        var stateSelect = document.getElementById('state_id');
        var mobileInput = document.getElementById('mobile');
        var nameInput = document.getElementById('name');
        var mobileHint = document.getElementById('mobile-hint');
        var nameHint = document.getElementById('name-hint');

        if (!countrySelect || !stateWrapper || !stateSelect || !nameInput) return;

        var selectedOption = countrySelect.options[countrySelect.selectedIndex];
        var countryId = selectedOption ? selectedOption.value : null;
        var countryCode = selectedOption ? selectedOption.getAttribute('data-code') : null;

        // Show/hide state field - FIX: Use empty string instead of 'block'
        if (countryCode === 'EG') {
            stateWrapper.style.display = '';  // Remove inline style to show
            stateWrapper.classList.remove('d-none');
        } else {
            stateWrapper.style.display = 'none';  // Hide when not Egypt
        }

        // Populate Egyptian states
        stateSelect.innerHTML = '<option value="">Choose State...</option>';
        if (countryCode === 'EG') {
            var allStatesData = document.getElementById('all_states_data');
            if (allStatesData) {
                var stateOptions = allStatesData.querySelectorAll('.state-option');
                stateOptions.forEach(function (stateData) {
                    if (stateData.dataset.countryId === countryId) {
                        var option = document.createElement('option');
                        option.value = stateData.dataset.stateId;
                        option.textContent = stateData.dataset.stateName;
                        if (stateData.dataset.selected === 'true') option.selected = true;
                        stateSelect.appendChild(option);
                    }
                });
            }
        }

        // Phone input rules
        if (mobileInput) {
            if (countryCode === 'EG') {
                mobileInput.pattern = '^01\\d{9}$';
                mobileInput.placeholder = '01XXXXXXXXX';
                if (mobileHint) mobileHint.textContent = 'Example: 01012345678 (Egyptian number)';
            } else {
                mobileInput.removeAttribute('pattern');
                mobileInput.placeholder = 'Enter phone number';
                if (mobileHint) mobileHint.textContent = 'Enter a valid phone number';
            }
        }

        // Name input rules
        if (nameInput) {
            if (countryCode === 'EG') {
                nameInput.pattern = '^[\\u0600-\\u06FF\\s]+$';
                nameInput.placeholder = 'مثال : محمد ابراهيم محمد';
                if (nameHint) nameHint.textContent = 'Full name (three parts) must be in Arabic only.';
            } else {
                nameInput.removeAttribute('pattern');
                nameInput.placeholder = 'Example: John Michael Smith';
                if (nameHint) nameHint.textContent = 'Full name (three parts)';
            }
        }
    }

    window.updateStateAndPhoneFields = updateStateAndPhoneFields;

    document.addEventListener('DOMContentLoaded', function () {
        var countrySelect = document.getElementById('country_id');
        if (countrySelect) {
            countrySelect.addEventListener('change', updateStateAndPhoneFields);
            updateStateAndPhoneFields();
        }
    });
})();