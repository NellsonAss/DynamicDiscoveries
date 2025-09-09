// JavaScript for cost and location override visual indicators
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize override field monitoring
    initializeOverrideFields();
    
    // Monitor for dynamically added inline forms
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && node.classList && node.classList.contains('inline-related')) {
                        initializeOverrideFields(node);
                    }
                });
            }
        });
    });
    
    const inlineGroups = document.querySelectorAll('.inline-group');
    inlineGroups.forEach(function(group) {
        observer.observe(group, { childList: true, subtree: true });
    });
    
    function initializeOverrideFields(container = document) {
        // Handle cost selectors
        const costSelectors = container.querySelectorAll('.cost-selector');
        costSelectors.forEach(function(selector) {
            selector.addEventListener('change', function() {
                updateDefaultValues(this, 'cost');
            });
            // Initialize on page load
            if (selector.value) {
                updateDefaultValues(selector, 'cost');
            }
        });
        
        // Handle location selectors
        const locationSelectors = container.querySelectorAll('.location-selector');
        locationSelectors.forEach(function(selector) {
            selector.addEventListener('change', function() {
                updateDefaultValues(this, 'location');
            });
            // Initialize on page load
            if (selector.value) {
                updateDefaultValues(selector, 'location');
            }
        });
        
        // Handle override fields
        const overrideFields = container.querySelectorAll('.override-field');
        overrideFields.forEach(function(field) {
            field.addEventListener('input', function() {
                checkForModification(this);
            });
            field.addEventListener('change', function() {
                checkForModification(this);
            });
            // Initialize on page load
            checkForModification(field);
        });
    }
    
    function updateDefaultValues(selector, type) {
        const row = selector.closest('tr, .inline-related');
        if (!row) return;
        
        const selectedId = selector.value;
        if (!selectedId) return;
        
        // Find the rate and frequency fields in the same row
        const rateField = row.querySelector('[data-field-type="rate"]');
        const frequencyField = row.querySelector('[data-field-type="frequency"]');
        
        if (!rateField || !frequencyField) return;
        
        // Fetch default values via AJAX
        fetchDefaultValues(selectedId, type).then(function(defaults) {
            if (defaults) {
                // Update data attributes
                rateField.setAttribute('data-default-value', defaults.rate);
                frequencyField.setAttribute('data-default-value', defaults.frequency);
                
                // If fields are empty, populate with defaults
                if (!rateField.value || rateField.value === '0' || rateField.value === '0.00') {
                    rateField.value = defaults.rate;
                }
                if (!frequencyField.value) {
                    frequencyField.value = defaults.frequency;
                }
                
                // Check for modifications
                checkForModification(rateField);
                checkForModification(frequencyField);
            }
        });
    }
    
    function fetchDefaultValues(id, type) {
        const endpoint = type === 'cost' ? '/admin/costs/' + id + '/defaults/' : '/admin/locations/' + id + '/defaults/';
        
        // For now, we'll use a simple approach since we don't have the AJAX endpoint
        // In a real implementation, you would make an AJAX call here
        return Promise.resolve(null);
    }
    
    function checkForModification(field) {
        const defaultValue = field.getAttribute('data-default-value');
        const currentValue = field.value;
        
        if (defaultValue && currentValue && currentValue !== defaultValue) {
            field.classList.add('modified');
            markRowAsModified(field);
            addTooltip(field, defaultValue);
        } else {
            field.classList.remove('modified');
            removeTooltip(field);
            checkRowModificationStatus(field);
        }
    }
    
    function markRowAsModified(field) {
        const row = field.closest('tr, .inline-related');
        if (row) {
            row.classList.add('modified');
        }
    }
    
    function checkRowModificationStatus(field) {
        const row = field.closest('tr, .inline-related');
        if (row) {
            const modifiedFields = row.querySelectorAll('.override-field.modified');
            if (modifiedFields.length === 0) {
                row.classList.remove('modified');
            }
        }
    }
    
    function addTooltip(field, defaultValue) {
        // Remove existing tooltip
        removeTooltip(field);
        
        const wrapper = document.createElement('div');
        wrapper.className = 'field-tooltip';
        
        const tooltip = document.createElement('span');
        tooltip.className = 'tooltip-text';
        tooltip.textContent = 'Default: ' + defaultValue;
        
        // Wrap the field
        field.parentNode.insertBefore(wrapper, field);
        wrapper.appendChild(field);
        wrapper.appendChild(tooltip);
    }
    
    function removeTooltip(field) {
        const wrapper = field.closest('.field-tooltip');
        if (wrapper) {
            const parent = wrapper.parentNode;
            parent.insertBefore(field, wrapper);
            parent.removeChild(wrapper);
        }
    }
    
    // Add visual feedback for calculated fields
    function updateCalculatedFields() {
        const calculatedFields = document.querySelectorAll('[class*="calculated"]');
        calculatedFields.forEach(function(field) {
            const value = parseFloat(field.textContent.replace(/[$,]/g, ''));
            if (!isNaN(value)) {
                field.classList.add('calculated-field');
                if (value > 0) {
                    field.classList.add('positive');
                } else if (value === 0) {
                    field.classList.add('zero');
                }
            }
        });
    }
    
    // Initialize calculated fields
    updateCalculatedFields();
    
    // Update calculated fields when forms change
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('override-field') || e.target.classList.contains('cost-selector') || e.target.classList.contains('location-selector')) {
            setTimeout(updateCalculatedFields, 100);
        }
    });
});

// Helper function to format currency values
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(value);
}

// Helper function to compare values (handles different data types)
function valuesEqual(val1, val2) {
    // Handle numeric comparisons
    if (!isNaN(val1) && !isNaN(val2)) {
        return parseFloat(val1) === parseFloat(val2);
    }
    // Handle string comparisons
    return String(val1).toLowerCase() === String(val2).toLowerCase();
}
