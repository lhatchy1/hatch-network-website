# ArcGIS Map Integration

## Overview

The Hatch Network website includes an interactive map powered by **ArcGIS API for JavaScript (v4.31)** with dark mode theming. The map is accessible via the "Map" tab in the navigation.

## Features

- **Dark Mode Integration**: Uses ArcGIS dark theme that matches the site's design
- **Interactive Controls**: Mouse wheel zoom, click-and-drag panning
- **Web Map Support**: Can load custom ArcGIS Web Maps for dynamic editing
- **Fallback Mode**: Default dark basemap if no Web Map ID is configured
- **Lazy Loading**: Map only initializes when the Map tab is opened (performance optimization)

## Configuration

### Using the Default Map

By default, the map uses ArcGIS's dark gray vector basemap centered on coordinates (46.8182° N, 8.2275° E) at zoom level 8.

**Location in code**: `index.html:1545`
```javascript
const ARCGIS_WEBMAP_ID = ""; // Empty = default dark basemap
```

### Using a Custom Web Map (Recommended for Easy Editing)

To enable dynamic map editing through ArcGIS Online:

1. **Create/Edit Map**: Go to https://arcgis.com and sign in
2. **Open Map Editor**: Click "Map" to create new or edit existing
3. **Customize**: Add markers, layers, popups, styling, etc.
4. **Save & Share**: Click "Save" then "Share" - make it public or organizational
5. **Get ID**: Copy the Web Map ID from the URL
   Example: `https://arcgis.com/home/webmap/viewer.html?webmap=YOUR_ID_HERE`
6. **Update Config**: Paste the ID into `ARCGIS_WEBMAP_ID` in `index.html:1545`

**Benefits**: All changes made in ArcGIS Online automatically appear on the website - no code changes needed!

## Technical Implementation

### Files Modified
- `index.html` - Complete integration

### Key Components

**HTML Structure** (`index.html:1406-1418`)
- Map tab container
- 700px height container with dark-themed styling
- Border and background colors use CSS variables for theme consistency

**API Loading** (`index.html:1515-1516`)
```html
<link rel="stylesheet" href="https://js.arcgis.com/4.31/esri/themes/dark/main.css">
<script src="https://js.arcgis.com/4.31/"></script>
```

**Initialization Logic** (`index.html:2528-2602`)
- `initArcGISMap()` function with lazy initialization
- Conditional loading: WebMap or default Map based on config
- AMD module loading using `require()`
- Console logging for debugging

### Map Modes

**Web Map Mode** (when `ARCGIS_WEBMAP_ID` is set):
```javascript
require(["esri/WebMap", "esri/views/MapView"], ...)
```
- Loads web map from ArcGIS Online portal
- Displays edit URL in console
- Error handling for sharing/permission issues

**Default Mode** (when `ARCGIS_WEBMAP_ID` is empty):
```javascript
require(["esri/Map", "esri/views/MapView"], ...)
```
- Uses `dark-gray-vector` basemap
- Default center: `[8.2275, 46.8182]`
- Default zoom level: `8`
- Displays tip about Web Map feature in console

## Debugging

Console logs are prefixed with `[ArcGIS]` for easy filtering:
- Initialization status
- Web Map loading success/failure
- Edit URLs for Web Maps
- Configuration tips

## Recent Changes

- **Commit 48c2e0e**: Enabled ArcGIS Web Map embedding for dynamic map editing
- **Commit d2bb493**: Added ArcGIS map integration with dark mode

## Dependencies

- ArcGIS API for JavaScript 4.31
- CDN-hosted (no local installation required)
- Dark theme CSS from Esri

## Performance Notes

- Map initialization is lazy (only when tab is opened)
- `mapInitialized` flag prevents duplicate initialization
- 700px fixed height for consistent rendering
