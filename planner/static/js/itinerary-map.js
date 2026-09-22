/* Coordinates and descriptions come from the server's Places-enriched itinerary. */
(() => {
  const mapElement = document.getElementById('map');
  const status = document.getElementById('map-status');
  window.showMapUnavailable = () => {
    mapElement.hidden = true;
    status.hidden = false;
  };
  window.gm_authFailure = window.showMapUnavailable;
  window.initItineraryMap = async () => {
    try {
      const { Map, InfoWindow, Polyline } = await google.maps.importLibrary('maps');
      const { AdvancedMarkerElement } = await google.maps.importLibrary('marker');
      const activities = JSON.parse(document.getElementById('itineraryCoords').textContent);
      const mapId = JSON.parse(document.getElementById('google-map-id').textContent);
      mapElement.hidden = false;
      const map = new Map(mapElement, {
        center: { lat: 41.8781, lng: -87.6298 }, zoom: 12, mapId,
      });
      const bounds = new google.maps.LatLngBounds();
      const paths = new globalThis.Map();
      const info = new InfoWindow();
      let count = 0;
      for (const activity of activities) {
        const lat = activity.latitude;
        const lng = activity.longitude;
        if (!Number.isFinite(lat) || !Number.isFinite(lng) ||
            Math.abs(lat) > 90 || Math.abs(lng) > 180 || (lat === 0 && lng === 0)) continue;
        const position = { lat, lng };
        const marker = new AdvancedMarkerElement({ map, position, title: activity.place });
        const content = document.createElement('div');
        const title = document.createElement('strong');
        title.textContent = activity.place;
        const description = document.createElement('p');
        description.textContent = activity.description;
        content.append(title, description);
        marker.addListener('click', () => {
          info.setContent(content);
          info.open({ map, anchor: marker });
        });
        const day = activity.day || 1;
        if (!paths.has(day)) paths.set(day, []);
        paths.get(day).push(position);
        bounds.extend(position);
        count += 1;
      }
      for (const path of paths.values()) {
        if (path.length > 1) new Polyline({ map, path, strokeColor: '#0d6efd', strokeWeight: 4 });
      }
      if (count === 1) {
        map.setCenter(bounds.getCenter());
        map.setZoom(15);
      } else if (count > 1) {
        map.fitBounds(bounds, 40);
      }
      status.hidden = count > 0;
      if (!count) status.textContent = 'Place locations are unavailable for this itinerary.';
    } catch (error) {
      window.showMapUnavailable();
    }
  };
})();
