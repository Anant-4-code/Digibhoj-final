class CustomerTracker {
    constructor(orderId, googleMapsApiKey, providerLocation, deliveryLocation) {
        this.orderId = orderId;
        this.apiKey = googleMapsApiKey;
        this.providerLocation = providerLocation;
        this.deliveryLocation = deliveryLocation;
        this.map = null;
        this.riderMarker = null;
        this.pickupMarker = null;
        this.deliveryMarker = null;
        this.lastPos = null;
        this.targetPos = null;
        this.startTime = null;
        this.duration = 10000;
        this.isInitialized = false;
        
        this.initMap();
    }

    async initMap() {
        const defaultCenter = { lat: 18.5204, lng: 73.8567 };
        
        // Import necessary libraries including modern ones
        const { Map } = await google.maps.importLibrary("maps");
        const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
        const { Route } = await google.maps.importLibrary("routes");
        const { Geocoder } = await google.maps.importLibrary("geocoding");
        
        this.AdvancedMarkerElement = AdvancedMarkerElement;
        this.PinElement = PinElement;
        this.Route = Route;
        this.geocoder = new Geocoder();

        this.map = new Map(document.getElementById('live-tracking-map'), {
            zoom: 15,
            center: defaultCenter,
            styles: this.getMapStyles(),
            disableDefaultUI: true,
            zoomControl: true,
            mapId: 'DEMO_MAP_ID'
        });

        await this.geocodeLocations();
        this.startPolling();
    }

    async geocodeLocations() {
        const locations = [
            { text: this.providerLocation, type: 'pickup' },
            { text: this.deliveryLocation, type: 'delivery' }
        ];

        for (const loc of locations) {
            try {
                const result = await this.geocoder.geocode({ address: loc.text });
                if (result.results && result.results[0]) {
                    const pos = result.results[0].geometry.location.toJSON();
                    this.addStaticMarker(pos, loc.type);
                }
            } catch (e) {
                console.warn(`Geocoding failed for ${loc.type}:`, e);
            }
        }
        
        if (this.pickupPos && this.deliveryPos) {
            this.calculateRoute();
            const bounds = new google.maps.LatLngBounds();
            bounds.extend(this.pickupPos);
            bounds.extend(this.deliveryPos);
            this.map.fitBounds(bounds);
        }
    }

    addStaticMarker(pos, type) {
        let content;
        if (type === 'pickup') {
            this.pickupPos = pos;
            content = new this.PinElement({ background: '#1E93AB', borderColor: 'white', glyphColor: 'white' }).element;
        } else {
            this.deliveryPos = pos;
            content = new this.PinElement({ background: '#E62727', borderColor: 'white', glyphColor: 'white' }).element;
        }

        new this.AdvancedMarkerElement({
            position: pos,
            map: this.map,
            content: content,
            title: type === 'pickup' ? 'Provider' : 'Your Location'
        });
    }

    async calculateRoute() {
        if (!this.pickupPos || !this.deliveryPos || !this.Route) return;

        const request = {
            origin: { location: { latLng: { latitude: this.pickupPos.lat, longitude: this.pickupPos.lng } } },
            destination: { location: { latLng: { latitude: this.deliveryPos.lat, longitude: this.deliveryPos.lng } } },
            travelMode: 'DRIVE',
            fieldMask: 'routes.polyline.encodedPolyline'
        };

        try {
            const response = await this.Route.computeRoutes(request);
            if (response.routes && response.routes.length > 0) {
                const encodedPolyline = response.routes[0].polyline.encodedPolyline;
                const path = google.maps.geometry.encoding.decodePath(encodedPolyline);
                new google.maps.Polyline({
                    path: path,
                    geodesic: true,
                    strokeColor: '#666',
                    strokeOpacity: 0.4,
                    strokeWeight: 4,
                    map: this.map
                });
            }
        } catch (error) {
            console.error("Path calculation failed:", error);
        }
    }

    getMapStyles() {
        return [
            { "featureType": "all", "elementType": "geometry.fill", "stylers": [{"weight": "2.00"}] },
            { "featureType": "landscape", "elementType": "geometry.fill", "stylers": [{"color": "#f5f5f5"}] },
            { "featureType": "poi", "elementType": "all", "stylers": [{"visibility": "off"}] },
            { "featureType": "road", "elementType": "geometry.fill", "stylers": [{"color": "#ffffff"}] },
            { "featureType": "water", "elementType": "geometry.fill", "stylers": [{"color": "#e9e9e9"}] }
        ];
    }

    async startPolling() {
        setInterval(() => this.fetchRiderLocation(), 10000);
        this.fetchRiderLocation(); // Initial fetch
    }

    async fetchRiderLocation() {
        try {
            const resp = await fetch(`/api/customer/order/${this.orderId}/rider-location`);
            if (resp.ok) {
                const data = await resp.json();
                if (data.lat && data.lng) {
                    const newPos = { lat: data.lat, lng: data.lng };
                    this.updateRiderPosition(newPos);
                    this.checkProximity(newPos);
                }
            }
        } catch (e) {
            console.warn("Failed to fetch rider location", e);
        }
    }

    updateRiderPosition(newPos) {
        if (!this.riderMarker) {
            const bikeIconDiv = document.createElement('div');
            bikeIconDiv.style.color = '#E62727';
            bikeIconDiv.style.fontSize = '24px';
            bikeIconDiv.innerHTML = '<i class="fas fa-motorcycle" style="text-shadow: 0 0 3px white;"></i>';

            this.riderMarker = new this.AdvancedMarkerElement({
                position: newPos,
                map: this.map,
                content: bikeIconDiv,
                title: 'Rider is here'
            });
            this.map.setCenter(newPos);
            this.lastPos = newPos;
        } else {
            // Start interpolation pulse
            this.lastPos = {
                lat: this.riderMarker.position.lat,
                lng: this.riderMarker.position.lng
            };
            this.targetPos = newPos;
            this.startTime = performance.now();
            this.animateStep();
        }
    }

    animateStep() {
        const now = performance.now();
        const elapsed = now - this.startTime;
        const fraction = Math.min(elapsed / this.duration, 1);

        if (this.lastPos && this.targetPos) {
            const lat = this.lastPos.lat + (this.targetPos.lat - this.lastPos.lat) * fraction;
            const lng = this.lastPos.lng + (this.targetPos.lng - this.lastPos.lng) * fraction;
            const currentPos = { lat, lng };
            
            this.riderMarker.position = currentPos;
            
            if (fraction < 1) {
                requestAnimationFrame(() => this.animateStep());
            } else {
                this.map.panTo(this.targetPos);
            }
        }
    }

    hasNotifiedProximity = false;
    checkProximity(pos) {
        if (!this.deliveryPos || this.hasNotifiedProximity) return;

        const dist = google.maps.geometry.spherical.computeDistanceBetween(
            new google.maps.LatLng(pos.lat, pos.lng),
            new google.maps.LatLng(this.deliveryPos.lat, this.deliveryPos.lng)
        );

        if (dist < 500) { // 500 meters
            this.hasNotifiedProximity = true;
            if (window.showToast) {
                window.showToast("Your rider is almost there! Get ready to receive your meal. 🍛", "success");
            }
        }
    }
}
