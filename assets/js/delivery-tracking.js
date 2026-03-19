class DeliveryTracker {
    constructor() {
        this.agentId = window.agentId;
        this.watchId = null;
        this.currentPos = null;
        this.map = null;
        this.directionsService = null;
        this.directionsRenderer = null;
        this.currentLocationMarker = null;
        this.pickupMarker = null;
        this.deliveryMarker = null;
        
        // Initialize charts and other non-map features
        new DeliveryCharts(this.agentId);
        this.updateBatteryStatus();
    }

    async init() {
        console.log("Initializing DeliveryTracker Map...");
        const defaultCenter = { lat: 18.5204, lng: 73.8567 }; // Pune default

        // Import necessary libraries for modern features
        const { Map } = await google.maps.importLibrary("maps");
        const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
        const { DirectionsRenderer, Route } = await google.maps.importLibrary("routes");
        
        this.MapElement = Map;
        this.AdvancedMarkerElement = AdvancedMarkerElement;
        this.PinElement = PinElement;
        this.Route = Route;

        this.map = new Map(document.getElementById('map'), {
            zoom: 14,
            center: defaultCenter,
            styles: this.getMapStyles(),
            disableDefaultUI: true,
            zoomControl: false,
            mapId: 'DEMO_MAP_ID' // Required for AdvancedMarkerElement
        });

        // Modern Directions Setup
        this.directionsRenderer = new DirectionsRenderer({
            suppressMarkers: true,
            polylineOptions: {
                strokeColor: '#E62727', 
                strokeWeight: 5,
                strokeOpacity: 0.8
            }
        });
        this.directionsRenderer.setMap(this.map);

        this.setupMapControls();
        this.startTracking();
        
        // Hide loading
        const loader = document.getElementById('map-loading');
        if (loader) loader.style.display = 'none';
        
        console.log("Map Initialized Successfully.");
    }

    getMapStyles() {
        return [
            { "featureType": "all", "elementType": "geometry.fill", "stylers": [{"weight": "2.00"}] },
            { "featureType": "all", "elementType": "geometry.stroke", "stylers": [{"color": "#9c9c9c"}] },
            { "featureType": "landscape", "elementType": "geometry.fill", "stylers": [{"color": "#ffffff"}] },
            { "featureType": "poi", "elementType": "all", "stylers": [{"visibility": "off"}] },
            { "featureType": "road", "elementType": "geometry.fill", "stylers": [{"color": "#eeeeee"}] },
            { "featureType": "water", "elementType": "geometry.fill", "stylers": [{"color": "#c8d7d4"}] }
        ];
    }

    setupMapControls() {
        const centerBtn = document.getElementById('center-location');
        const trafficBtn = document.getElementById('toggle-traffic');
        const fullscreenBtn = document.getElementById('fullscreen-map');

        if (centerBtn) {
            centerBtn.onclick = () => {
                if (this.currentPos) {
                    this.map.panTo(this.currentPos);
                    this.map.setZoom(16);
                }
            };
        }

        if (trafficBtn) {
            let trafficLayer = null;
            trafficBtn.onclick = () => {
                if (trafficLayer) {
                    trafficLayer.setMap(null);
                    trafficLayer = null;
                    trafficBtn.classList.remove('active');
                } else {
                    trafficLayer = new google.maps.TrafficLayer();
                    trafficLayer.setMap(this.map);
                    trafficBtn.classList.add('active');
                }
            };
        }

        if (fullscreenBtn) {
            fullscreenBtn.onclick = () => {
                const mapContainer = document.getElementById('tracking-map');
                if (mapContainer.requestFullscreen) mapContainer.requestFullscreen();
            };
        }
    }

    startTracking() {
        if (!navigator.geolocation) return;

        this.watchId = navigator.geolocation.watchPosition(
            (pos) => {
                this.currentPos = {
                    lat: pos.coords.latitude,
                    lng: pos.coords.longitude
                };
                this.updateRiderMarker(this.currentPos);
                this.updateMetrics(pos.coords.speed);
                this.syncLocation(this.currentPos);
            },
            (err) => console.warn("Geolocation Error:", err),
            { enableHighAccuracy: true, maximumAge: 30000, timeout: 27000 }
        );
    }

    lastSyncTime = 0;
    async syncLocation(pos) {
        const now = Date.now();
        if (now - this.lastSyncTime < 10000) return; // Sync every 10s

        try {
            await fetch(`/api/delivery/location/${this.agentId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(pos)
            });
            this.lastSyncTime = now;
        } catch (e) {
            console.warn("Location sync failed", e);
        }
    }

    updateRiderMarker(pos) {
        if (this.currentLocationMarker) {
            this.currentLocationMarker.position = pos;
        } else {
            // Create a custom bike icon element for AdvancedMarkerElement
            const bikeIconDiv = document.createElement('div');
            bikeIconDiv.style.color = '#E62727';
            bikeIconDiv.style.fontSize = '24px';
            bikeIconDiv.innerHTML = '<i class="fas fa-motorcycle" style="text-shadow: 0 0 3px white;"></i>';

            this.currentLocationMarker = new this.AdvancedMarkerElement({
                position: pos,
                map: this.map,
                content: bikeIconDiv,
                title: 'Rider Location'
            });
            this.map.setCenter(pos);
        }
    }

    async calculateRoute(destination) {
        if (!this.currentPos || !this.Route) return;

        const request = {
            origin: {
                location: {
                    latLng: {
                        latitude: this.currentPos.lat,
                        longitude: this.currentPos.lng
                    }
                }
            },
            destination: {
                location: {
                    latLng: {
                        latitude: destination.lat,
                        longitude: destination.lng
                    }
                }
            },
            travelMode: 'DRIVE',
            routingPreference: 'TRAFFIC_AWARE',
            fieldMask: 'routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.legs.steps'
        };

        try {
            const response = await this.Route.computeRoutes(request);
            if (response.routes && response.routes.length > 0) {
                const routeData = response.routes[0];
                
                // Draw path using Polyline since computeRoutes output is different from DirectionsService
                this.renderRoutePath(routeData.polyline.encodedPolyline);

                const leg = routeData.legs[0];
                const etaLabel = document.getElementById('delivery-eta');
                if (etaLabel) {
                    // Convert duration (seconds) to readable text
                    const mins = Math.round(parseInt(leg.duration.replace('s', '')) / 60);
                    etaLabel.textContent = `ETA: ${mins} mins`;
                }
                
                this.updateNavigationSidebar(leg.steps);
                
                const bounds = new google.maps.LatLngBounds();
                bounds.extend(this.currentPos);
                bounds.extend(destination);
                this.map.fitBounds(bounds);
            }
        } catch (error) {
            console.error("Route calculation failed:", error);
        }
    }

    currentRoutePath = null;
    renderRoutePath(encodedPolyline) {
        if (this.currentRoutePath) {
            this.currentRoutePath.setMap(null);
        }

        const path = google.maps.geometry.encoding.decodePath(encodedPolyline);
        this.currentRoutePath = new google.maps.Polyline({
            path: path,
            geodesic: true,
            strokeColor: '#E62727',
            strokeOpacity: 0.8,
            strokeWeight: 5,
            map: this.map
        });
    }

    updateNavigationSidebar(steps) {
        const sidebar = document.getElementById('nav-instructions-list');
        if (!sidebar) return;

        sidebar.innerHTML = '';
        steps.slice(0, 5).forEach(step => {
            const div = document.createElement('div');
            div.className = 'instruction-item';
            div.innerHTML = `
                <div class="instruction-icon"><i class="fas fa-arrow-right"></i></div>
                <div class="instruction-text">
                    <span class="instruction-action">${step.navigationInstruction ? step.navigationInstruction.instructions : 'Proceed'}</span>
                    <span class="instruction-distance">${step.distanceMeters}m</span>
                </div>
            `;
            sidebar.appendChild(div);
        });
    }

    updateMetrics(speed) {
        const speedEl = document.getElementById('current-speed');
        if (speedEl) {
            const kmh = speed ? Math.round(speed * 3.6) : 0;
            speedEl.textContent = `${kmh} km/h`;
        }
    }

    updateBatteryStatus() {
        if ('getBattery' in navigator) {
            navigator.getBattery().then(battery => {
                const update = () => {
                    const el = document.getElementById('device-battery');
                    if (el) el.textContent = `${Math.round(battery.level * 100)}%`;
                };
                update();
                battery.addEventListener('levelchange', update);
            });
        }
    }
}

class DeliveryCharts {
    constructor(agentId) {
        this.agentId = agentId;
        this.charts = {};
        this.initializeCharts();
    }

    async initializeCharts() {
        let data = {
            earnings: [0, 0, 0, 0, 0, 0, 0],
            performance: [50, 50, 50, 50, 50]
        };

        try {
            const resp = await fetch(`/api/delivery/analytics/${this.agentId}`);
            if (resp.ok) {
                const result = await resp.json();
                data = result;
            }
        } catch (e) {
            console.warn("Could not fetch real analytics, using fallback data");
        }

        this.createEarningsChart(data.earnings);
        this.createPerformanceChart(data.performance);
    }

    createEarningsChart(earningData) {
        const ctx = document.getElementById('earnings-chart');
        if (!ctx) return;

        const color = getComputedStyle(document.documentElement).getPropertyValue('--orange').trim() || '#E62727';

        this.charts.earnings = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Daily Earnings (₹)',
                    data: earningData,
                    borderColor: color,
                    backgroundColor: 'rgba(230, 39, 39, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: color,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    createPerformanceChart(perfData) {
        const ctx = document.getElementById('performance-chart');
        if (!ctx) return;

        this.charts.performance = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Speed', 'Accuracy', 'Rating', 'Efficiency', 'Reliability'],
                datasets: [{
                    label: 'Performance',
                    data: perfData,
                    borderColor: '#1E93AB',
                    backgroundColor: 'rgba(30, 147, 171, 0.2)',
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    r: { beginAtZero: true, max: 100 }
                }
            }
        });
    }
}

function initMap() {
    window.deliveryTracker = new DeliveryTracker();
    window.deliveryTracker.init();
}

document.addEventListener('DOMContentLoaded', () => {
    // If google maps is already loaded (it might be since it's defer/async)
    if (window.google && window.google.maps && !window.deliveryTracker) {
        initMap();
    }
});
