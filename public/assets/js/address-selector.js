/**
 * DigiBhoj Address Selector Component
 * Handles State/City mapping, Geolocation, and Map Picker integration.
 * Supports auto-filling from existing "combined" address strings.
 */

const STATE_CITY_MAP = {
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Thane", "Solapur"],
    "Karnataka": ["Bengaluru", "Mysuru", "Hubballi", "Mangaluru", "Belagavi", "Kalaburagi"],
    "Delhi": ["New Delhi", "North Delhi", "South Delhi", "West Delhi", "East Delhi"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Erode"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Ghaziabad", "Agra", "Varanasi", "Meerut"],
    "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Ramagundam"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Kota", "Bikaner", "Ajmer", "Udaipur"],
    "Madhya Pradesh": ["Indore", "Bhopal", "Jabalpur", "Gwalior", "Ujjain"]
};

function initAddressSelector(container) {
    const stateSelect = container.querySelector('.address-state');
    const citySelect = container.querySelector('.address-city');
    const detailedAddress = container.querySelector('.detailed-address');
    const hiddenFullAddress = container.querySelector('.full-address-input');
    const geoBtn = container.querySelector('.btn-get-location');
    const mapBtn = container.querySelector('.btn-pick-map');

    if (!stateSelect || !citySelect || !detailedAddress || !hiddenFullAddress) return;

    // Initialize States
    Object.keys(STATE_CITY_MAP).sort().forEach(state => {
        const option = document.createElement('option');
        option.value = state;
        option.textContent = state;
        stateSelect.appendChild(option);
    });

    // Helper: Update hidden field
    function updateFullAddress() {
        const state = stateSelect.value;
        const city = citySelect.value;
        const detail = detailedAddress.value.trim();
        
        let full = "";
        if (detail) full += detail;
        if (city) full += (full ? ", " : "") + city;
        if (state) full += (full ? ", " : "") + state;
        
        hiddenFullAddress.value = full;
    }

    // Helper: Parse existing address
    function parseExistingAddress() {
        const full = hiddenFullAddress.value.trim();
        if (!full) return;

        const parts = full.split(',').map(p => p.trim());
        if (parts.length < 1) return;

        // Try to find State (usually last or second to last)
        let stateFound = "";
        let cityFound = "";
        let details = [];

        // Simple heuristic: check parts against our map
        for (let i = parts.length - 1; i >= 0; i--) {
            const part = parts[i];
            if (!stateFound && STATE_CITY_MAP[part]) {
                stateFound = part;
            } else if (stateFound && !cityFound && STATE_CITY_MAP[stateFound].includes(part)) {
                cityFound = part;
            } else {
                details.unshift(part);
            }
        }

        if (stateFound) {
            stateSelect.value = stateFound;
            // Trigger city population
            stateSelect.dispatchEvent(new Event('change'));
            if (cityFound) {
                citySelect.value = cityFound;
            }
        }
        detailedAddress.value = details.join(', ');
    }

    // State Change Listener
    stateSelect.addEventListener('change', function() {
        const state = this.value;
        citySelect.innerHTML = '<option value="">-- Select City --</option>';
        citySelect.disabled = !state;

        if (state && STATE_CITY_MAP[state]) {
            STATE_CITY_MAP[state].sort().forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                option.textContent = city;
                citySelect.appendChild(option);
            });
        }
        updateFullAddress();
    });

    citySelect.addEventListener('change', updateFullAddress);
    detailedAddress.addEventListener('input', updateFullAddress);

    // Initial Parse
    parseExistingAddress();

    // Geolocation Support
    if (geoBtn) {
        geoBtn.addEventListener('click', function() {
            if (!navigator.geolocation) {
                alert("Geolocation is not supported.");
                return;
            }
            const originalText = geoBtn.innerHTML;
            geoBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i>';
            geoBtn.disabled = true;

            navigator.geolocation.getCurrentPosition(async (pos) => {
                const { latitude, longitude } = pos.coords;
                try {
                    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`);
                    const data = await res.json();
                    if (data && data.display_name) {
                        detailedAddress.value = data.display_name;
                        // Optional: Try to auto-select state if found in reverse geocode
                        const addr = data.address || {};
                        const state = addr.state || "";
                        if (STATE_CITY_MAP[state]) {
                            stateSelect.value = state;
                            stateSelect.dispatchEvent(new Event('change'));
                        }
                        updateFullAddress();
                    }
                } catch (e) {
                    detailedAddress.value = `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
                    updateFullAddress();
                } finally {
                    geoBtn.innerHTML = originalText;
                    geoBtn.disabled = false;
                }
            }, () => {
                alert("Location access denied.");
                geoBtn.innerHTML = originalText;
                geoBtn.disabled = false;
            });
        });
    }

    if (mapBtn) {
        mapBtn.addEventListener('click', () => alert("Maps API requires billing. See GOOGLE_MAPS_FIX.md"));
    }
}

// Auto-initialize all selectors on page
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.address-selector-container').forEach(initAddressSelector);
});
