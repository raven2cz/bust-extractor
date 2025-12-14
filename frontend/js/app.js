/**
 * Bust Extractor Pro - Main Application
 * ======================================
 * Professional web-based tool for extracting character portraits (busts)
 * from sprite sheets with AI-powered background removal.
 * 
 * @fileoverview Main application module handling UI interactions, canvas rendering,
 *               mask editing, and API communication.
 * @author raven2cz
 * @version 2.0
 * @license MIT
 */

'use strict';

// =============================================================================
// Application Version & Configuration
// =============================================================================

/**
 * Application version - single source of truth for version display
 * @constant {string}
 */
const APP_VERSION = '2.0';

/**
 * API base URL - empty for same-origin requests
 * @constant {string}
 */
const API = '';

console.log(`=== Bust Extractor Pro v${APP_VERSION} Script Loading ===`);

// =============================================================================
// Core Utilities
// =============================================================================

/**
 * Shorthand for document.getElementById
 * @param {string} id - Element ID
 * @returns {HTMLElement|null} The element or null if not found
 */
const $ = id => document.getElementById(id);

/**
 * Current language code for translations
 * @type {string}
 */
let currentLang = 'en';

/**
 * Cached processed image for alignment view performance
 * @type {HTMLImageElement|null}
 */
let processedImgCache = null;

/**
 * Secondary file for difference matting mode
 * @type {File|null}
 */
let secondaryFile = null;

// =============================================================================
// Global Upload Handlers (accessible from inline HTML events)
// =============================================================================

/**
 * Triggers the file input dialog for image upload
 * @function
 */
window.triggerUpload = () => {
    console.log('triggerUpload called');
    const fi = $('fileInput');
    console.log('fileInput element:', fi);
    if (fi) fi.click();
};

/**
 * Handles dragover event for drag-and-drop upload
 * @param {DragEvent} e - The drag event
 */
window.handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
};

/**
 * Handles drop event for drag-and-drop upload
 * @param {DragEvent} e - The drop event
 */
window.handleDrop = (e) => {
    console.log('handleDrop called');
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        console.log('File dropped:', e.dataTransfer.files[0].name);
        if (typeof upload === 'function') {
            upload(e.dataTransfer.files[0]);
        } else {
            console.error('upload function not yet defined');
        }
    }
};

console.log('Upload handlers registered');

// =============================================================================
// Application State
// =============================================================================

/**
 * Central application state object
 * @typedef {Object} AppState
 * @property {string|null} sessionId - Current server session ID
 * @property {string} view - Current view tab ('original'|'processed'|'mask'|'detection'|'alignment'|'results')
 * @property {Object} images - Base64 encoded image data
 * @property {Array<BustRegion>} busts - Detected bust regions
 * @property {string|null} selectedBustId - Currently selected bust ID
 * @property {Array} results - Extraction results
 * @property {number} autoTolerance - Auto-detected background tolerance
 * @property {number} zoom - Current zoom level
 * @property {Object} pan - Pan offset {x, y}
 * @property {boolean} dragging - Whether user is panning
 * @property {Object} lastMouse - Last mouse position
 * @property {Object} brush - Brush tool state
 * @property {HTMLCanvasElement|null} maskCanvas - Offline canvas for mask editing
 * @property {CanvasRenderingContext2D|null} maskCtx - Mask canvas context
 * @property {boolean} spacePressed - Whether spacebar is held
 * @property {Array<ImageData>} history - Undo history stack
 * @property {number} historyIdx - Current position in history
 * @property {Object} cachedImages - Performance cache for loaded images
 */

/**
 * @type {AppState}
 */
const state = {
    sessionId: null,
    view: 'original',
    images: {},
    busts: [],
    selectedBustId: null,
    results: [],
    autoTolerance: 30,
    zoom: 1,
    pan: { x: 0, y: 0 },
    dragging: false,
    lastMouse: { x: 0, y: 0 },
    brush: {
        active: false,
        tool: null,       // 'eraser' | 'restore' | null
        size: 20,
        hardness: 0.5
    },
    maskCanvas: null,
    maskCtx: null,
    spacePressed: false,
    history: [],
    historyIdx: -1,
    cachedImages: {}
};

// =============================================================================
// Method Info Mapping
// =============================================================================

/**
 * Maps background removal method values to translation keys
 * @constant {Object<string, string>}
 */
const methodInfo = {
    'rembg_birefnet-general': 'method_birefnet',
    'difference_matting': 'method_diff',
    'color_based': 'method_color',
    'rembg_isnet-anime': 'method_anime',
    'rembg_isnet-general-use': 'method_general',
    'rembg_u2net': 'method_u2net'
};

// =============================================================================
// UI Helper Functions
// =============================================================================

/**
 * Shows an element by setting display to 'block'
 * @param {string} id - Element ID
 */
function show(id) { 
    $(id).style.display = 'block'; 
}

/**
 * Hides an element by setting display to 'none'
 * @param {string} id - Element ID
 */
function hide(id) { 
    $(id).style.display = 'none'; 
}

/**
 * Toggles the 'open' class on a collapsible element
 * @param {string} id - Element ID
 */
function toggle(id) { 
    const el = $(id); 
    el.classList.toggle('open'); 
}

/**
 * Shows loading overlay with custom message
 * @param {string} text - Loading message to display
 */
function loading(text) { 
    $('loadingText').textContent = text; 
    $('loadingOverlay').classList.add('visible'); 
}

/**
 * Hides loading overlay
 */
function loaded() { 
    $('loadingOverlay').classList.remove('visible'); 
}

/**
 * Shows a toast notification
 * @param {string} msg - Message to display
 * @param {string} [type='success'] - Toast type ('success' | 'error')
 */
function toast(msg, type = 'success') {
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    $('toastContainer').appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

// =============================================================================
// Translation System
// =============================================================================

/**
 * Updates all UI elements with translations for current language
 */
function updateTranslations() {
    if (!translations || !translations[currentLang]) return;
    console.log("updateTranslations running for:", currentLang);
    const t = translations[currentLang];

    // Update text content
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key]) {
            if (el.tagName === 'INPUT' && el.type === 'button') {
                el.value = t[key];
            } else {
                el.innerHTML = t[key];
            }
        }
    });

    // Update title attributes
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        if (t[key]) el.title = t[key];
    });
}

/**
 * Sets the application language and updates UI
 * @param {string} lang - Language code ('en' | 'cz')
 */
function setLanguage(lang) {
    if (!translations || !translations[lang]) return;
    currentLang = lang;

    // Update language button states
    $('langEn').style.background = lang === 'en' ? 'var(--accent)' : 'var(--bg-input)';
    $('langEn').style.color = lang === 'en' ? 'white' : 'var(--text)';
    $('langCz').style.background = lang === 'cz' ? 'var(--accent)' : 'var(--bg-input)';
    $('langCz').style.color = lang === 'cz' ? 'white' : 'var(--text)';

    updateTranslations();
    updateUiForMethod();
}

// =============================================================================
// UI State Updates
// =============================================================================

/**
 * Updates UI visibility based on selected background removal method
 */
function updateUiForMethod() {
    const method = $('bgMethod').value;
    const isDiff = method === 'difference_matting';
    const isColor = method === 'color_based';
    const isAI = !isDiff && !isColor;

    // Toggle section visibility
    $('secondaryUploadSection').style.display = isDiff ? 'block' : 'none';
    $('validatorBox').style.display = isAI ? 'block' : 'none';
    $('refinementBox').style.display = isAI ? 'block' : 'none';

    // Update method info text
    const key = methodInfo[method];
    if (key && translations[currentLang] && translations[currentLang][key]) {
        $('methodInfo').innerHTML = translations[currentLang][key];
    } else {
        $('methodInfo').innerHTML = '';
    }
}

// =============================================================================
// History System (Undo/Redo)
// =============================================================================

/**
 * Saves current mask state to history stack
 * Implements branching history with max 20 states
 */
function saveHistoryState() {
    if (!state.maskCanvas) { 
        console.warn("saveHistoryState: No maskCanvas!"); 
        return; 
    }

    // Truncate forward history on new action (branching)
    if (state.historyIdx < state.history.length - 1) {
        console.log("saveHistoryState: Branching history. Slicing from", state.historyIdx + 1);
        state.history = state.history.slice(0, state.historyIdx + 1);
    }

    // Save full snapshot
    const snapshot = state.maskCtx.getImageData(0, 0, state.maskCanvas.width, state.maskCanvas.height);
    state.history.push(snapshot);
    
    // Cap history at 20 steps
    if (state.history.length > 20) state.history.shift();
    state.historyIdx = state.history.length - 1;

    console.log("saveHistoryState: Pushed. Len:", state.history.length, "Idx:", state.historyIdx);
    updateHistoryBtns();
}

/**
 * Undoes the last mask edit action
 */
function undo() {
    console.log("Undo triggered. Idx:", state.historyIdx);
    if (state.historyIdx > 0) {
        state.historyIdx--;
        const snapshot = state.history[state.historyIdx];
        state.maskCtx.putImageData(snapshot, 0, 0);
        renderCanvas();
        updateHistoryBtns();
    } else { 
        console.log("Undo limit reached"); 
    }
}

/**
 * Redoes the last undone mask edit action
 */
function redo() {
    console.log("Redo triggered. Idx:", state.historyIdx, "Len:", state.history.length);
    if (state.historyIdx < state.history.length - 1) {
        state.historyIdx++;
        const snapshot = state.history[state.historyIdx];
        state.maskCtx.putImageData(snapshot, 0, 0);
        renderCanvas();
        updateHistoryBtns();
    } else { 
        console.log("Redo limit reached"); 
    }
}

/**
 * Updates undo/redo button disabled states
 */
function updateHistoryBtns() {
    const undoBtn = $('btnUndo');
    const redoBtn = $('btnRedo');

    const undoDisabled = state.historyIdx <= 0;
    const redoDisabled = state.historyIdx >= state.history.length - 1;

    if (undoBtn) {
        undoBtn.disabled = undoDisabled;
        undoBtn.style.opacity = undoDisabled ? 0.3 : 1;
        undoBtn.style.cursor = undoDisabled ? 'default' : 'pointer';
    }
    if (redoBtn) {
        redoBtn.disabled = redoDisabled;
        redoBtn.style.opacity = redoDisabled ? 0.3 : 1;
        redoBtn.style.cursor = redoDisabled ? 'default' : 'pointer';
    }
}

// =============================================================================
// Canvas System
// =============================================================================

/** @type {HTMLCanvasElement|null} */
let visualCanvas = null;

/** @type {CanvasRenderingContext2D|null} */
let visualCtx = null;

/** @type {HTMLElement} */
const viewport = $('viewport');

/** @type {HTMLElement} */
const container = $('canvasContainer');

/**
 * Initializes the mask canvas from base64 data
 * Converts grayscale luminance to alpha channel
 * 
 * @param {number} width - Canvas width
 * @param {number} height - Canvas height
 * @param {string} maskDataBase64 - Base64 encoded mask image
 */
function initMaskCanvas(width, height, maskDataBase64) {
    // Create temporary canvas for conversion
    const tempC = document.createElement('canvas');
    tempC.width = width;
    tempC.height = height;
    const tempCtx = tempC.getContext('2d');

    // Create main mask canvas
    state.maskCanvas = document.createElement('canvas');
    state.maskCanvas.width = width;
    state.maskCanvas.height = height;
    state.maskCtx = state.maskCanvas.getContext('2d', { willReadFrequently: true });

    const img = new Image();
    img.onload = () => {
        // Draw raw grayscale image
        tempCtx.drawImage(img, 0, 0);

        // Convert luminance to alpha
        const iData = tempCtx.getImageData(0, 0, width, height);
        const data = iData.data;
        const targetData = state.maskCtx.createImageData(width, height);
        const tData = targetData.data;

        // Map luminance (R channel) to alpha
        for (let i = 0; i < data.length; i += 4) {
            const luma = data[i];
            tData[i] = 0;         // R
            tData[i + 1] = 0;     // G
            tData[i + 2] = 0;     // B
            tData[i + 3] = luma;  // Alpha = Luminance
        }

        // Resize visual canvas if needed
        if (visualCanvas && (visualCanvas.width !== img.width || visualCanvas.height !== img.height)) {
            visualCanvas.width = img.width;
            visualCanvas.height = img.height;
            fitToView();
        }

        state.maskCtx.putImageData(targetData, 0, 0);

        // Initialize history
        console.log("HISTORY INIT: Clearing history and pushing initial state.");
        state.history = [];
        state.historyIdx = -1;
        saveHistoryState();

        renderCanvas();
    };
    img.src = 'data:image/png;base64,' + maskDataBase64;
}

/**
 * Main canvas rendering function
 * Handles all view modes: original, processed, mask, detection, alignment, results
 */
function renderCanvas() {
    // Update toolbar visibility based on current view
    const canDraw = (state.view === 'processed' || state.view === 'mask') && state.images.mask;
    const toolbar = $('brushToolbar');
    if (canDraw) {
        toolbar.classList.add('visible');
    } else {
        toolbar.classList.remove('visible');
        if (state.brush.tool) setTool(null);
    }

    // RESULTS VIEW - Display extracted busts in grid
    if (state.view === 'results' && state.results.length) {
        renderResultsView();
        return;
    }

    // ALIGNMENT VIEW - Display bust alignment preview
    if (state.view === 'alignment') {
        renderAlignmentView();
        return;
    }

    // STANDARD VIEWS - Original, Processed, Mask, Detection
    renderStandardView();
}

/**
 * Renders the results view with extracted bust previews
 * @private
 */
function renderResultsView() {
    const prompt = $('initialUploadPrompt');
    if (prompt) prompt.style.display = 'none';

    if (visualCanvas) visualCanvas.style.display = 'none';

    // Configure container as flex grid
    container.style.display = 'flex';
    container.style.flexWrap = 'wrap';
    container.style.justifyContent = 'center';
    container.style.alignItems = 'flex-start';
    container.style.alignContent = 'flex-start';
    container.style.gap = '1rem';
    container.style.padding = '1rem';
    container.style.position = 'relative';
    container.style.transform = 'none';

    // Build results display if not already present
    if (!container.querySelector('.result-item')) {
        const existingCanvas = container.querySelector('canvas');
        container.innerHTML = '';
        if (existingCanvas) {
            existingCanvas.style.display = 'none';
            container.appendChild(existingCanvas);
        }

        state.results.forEach((r) => {
            const item = document.createElement('div');
            item.className = 'result-item';

            const img = document.createElement('img');
            img.src = 'data:image/png;base64,' + r.preview;

            const label = document.createElement('div');
            label.style.cssText = `
                font-size: 0.85rem;
                color: var(--accent);
                font-weight: 600;
            `;
            label.textContent = `${r.name} (${r.width}×${r.height})`;

            item.appendChild(img);
            item.appendChild(label);
            container.appendChild(item);
        });
    }
}

/**
 * Renders the alignment view for bust positioning
 * @private
 */
function renderAlignmentView() {
    const prompt = $('initialUploadPrompt');
    if (prompt) prompt.style.display = 'none';

    // Clean up results grid
    container.querySelectorAll('.result-item').forEach(el => el.remove());
    resetContainerStyles();

    container.style.display = 'block';
    container.style.position = 'absolute';

    ensureVisualCanvas();

    // Set alignment workspace size
    if (visualCanvas.width !== 1024 || visualCanvas.height !== 1024) {
        visualCanvas.width = 1024;
        visualCanvas.height = 1024;
        fitToView();
    }

    renderAlignment();
    updateTransform();
}

/**
 * Renders standard views (original, processed, mask, detection)
 * @private
 */
function renderStandardView() {
    // Clean up from other views
    container.querySelectorAll('.result-item').forEach(el => el.remove());
    resetContainerStyles();

    const imgData = state.images[state.view === 'processed' ? 'original' : state.view];

    // Handle initial state with no image
    const prompt = $('initialUploadPrompt');
    if (!imgData && !state.images.original) {
        container.style.display = 'flex';
        container.style.justifyContent = 'center';
        container.style.alignItems = 'center';
        if (prompt) prompt.style.display = 'block';
        return;
    }

    if (prompt) prompt.style.display = 'none';
    container.style.display = 'block';
    container.style.position = 'absolute';

    ensureVisualCanvas();

    // Load and cache base image
    const cacheKey = state.view === 'processed' ? 'original' : (state.view === 'mask' ? 'mask' : state.view);
    let baseImg = state.cachedImages[cacheKey];
    const desiredSrc = 'data:image/png;base64,' + (state.view === 'processed' ? state.images.original : (state.view === 'mask' ? state.images.mask : imgData));

    if (!baseImg || baseImg.src !== desiredSrc) {
        baseImg = new Image();
        baseImg.onload = () => {
            state.cachedImages[cacheKey] = baseImg;
            if (visualCanvas.width !== baseImg.width || visualCanvas.height !== baseImg.height) {
                if (baseImg.width === 0) return;
                visualCanvas.width = baseImg.width;
                visualCanvas.height = baseImg.height;
                fitToView();
            }
            renderCanvas();
        };
        baseImg.src = desiredSrc;
        if (!baseImg.complete) return;
    }

    // Resize canvas if needed
    if (visualCanvas.width !== baseImg.width || visualCanvas.height !== baseImg.height) {
        if (baseImg.width === 0) return;
        visualCanvas.width = baseImg.width;
        visualCanvas.height = baseImg.height;
        fitToView();
    }

    // Drawing logic based on view
    visualCtx.clearRect(0, 0, visualCanvas.width, visualCanvas.height);

    if (state.view === 'original' || state.view === 'detection') {
        visualCtx.drawImage(baseImg, 0, 0);
        
        // Overlay detection visualization
        if (state.view === 'detection' && state.images.detection) {
            let detImg = state.cachedImages['detection_cal'];
            if (!detImg || detImg.src !== 'data:image/png;base64,' + state.images.detection) {
                detImg = new Image();
                detImg.src = 'data:image/png;base64,' + state.images.detection;
                state.cachedImages['detection_cal'] = detImg;
            }
            if (detImg.complete) visualCtx.drawImage(detImg, 0, 0);
        }
    } else if (state.view === 'mask') {
        // White foreground on black background
        visualCtx.fillStyle = 'black';
        visualCtx.fillRect(0, 0, visualCanvas.width, visualCanvas.height);

        if (state.maskCanvas) {
            visualCtx.filter = 'invert(1)';
            visualCtx.drawImage(state.maskCanvas, 0, 0);
            visualCtx.filter = 'none';
        } else {
            visualCtx.drawImage(baseImg, 0, 0);
        }
    } else if (state.view === 'processed') {
        // Composite original with mask
        visualCtx.drawImage(baseImg, 0, 0);

        if (state.maskCanvas) {
            visualCtx.globalCompositeOperation = 'destination-in';
            visualCtx.drawImage(state.maskCanvas, 0, 0);
            visualCtx.globalCompositeOperation = 'source-over';
        }
    }

    updateTransform();
}

/**
 * Ensures visual canvas exists and is properly configured
 * @private
 */
function ensureVisualCanvas() {
    if (!visualCanvas) {
        visualCanvas = document.createElement('canvas');
        visualCanvas.id = 'mainCanvas';
        visualCtx = visualCanvas.getContext('2d');
        visualCanvas.style.display = 'block';
        container.appendChild(visualCanvas);
    }
    visualCanvas.style.display = 'block';
}

/**
 * Resets container flex/grid styles to defaults
 * @private
 */
function resetContainerStyles() {
    container.style.flexWrap = '';
    container.style.justifyContent = '';
    container.style.alignItems = '';
    container.style.alignContent = '';
    container.style.gap = '';
    container.style.padding = '';
}

// =============================================================================
// Transform & Zoom System
// =============================================================================

/**
 * Updates canvas container transform based on pan and zoom state
 */
function updateTransform() {
    container.style.transform = `translate3d(${state.pan.x}px, ${state.pan.y}px, 0) scale(${state.zoom})`;
    $('zoomDisplay').textContent = Math.round(state.zoom * 100) + '%';
}

/**
 * Zooms to a specific level, optionally centered on a point
 * @param {number} newZoom - Target zoom level
 * @param {number|null} [centerX=null] - X coordinate to zoom towards
 * @param {number|null} [centerY=null] - Y coordinate to zoom towards
 */
function zoomTo(newZoom, centerX = null, centerY = null) {
    const nextZoom = Math.max(0.1, Math.min(10, newZoom));
    
    if (centerX === null || centerY === null) {
        const vw = viewport.clientWidth;
        const vh = viewport.clientHeight;
        centerX = vw / 2;
        centerY = vh / 2;
    }
    
    // Calculate world coordinates at zoom center
    const worldX = (centerX - state.pan.x) / state.zoom;
    const worldY = (centerY - state.pan.y) / state.zoom;
    
    // Adjust pan to keep zoom center stationary
    state.pan.x = centerX - worldX * nextZoom;
    state.pan.y = centerY - worldY * nextZoom;
    state.zoom = nextZoom;
    
    updateTransform();
}

/**
 * Fits the canvas to viewport with padding
 */
function fitToView() {
    if (!visualCanvas) return;
    
    const vw = viewport.clientWidth;
    const vh = viewport.clientHeight;
    const iw = visualCanvas.width;
    const ih = visualCanvas.height;
    const padding = 40;
    
    const scaleW = (vw - padding) / iw;
    const scaleH = (vh - padding) / ih;
    
    state.zoom = Math.min(scaleW, scaleH, 1);
    state.pan.x = (vw - iw * state.zoom) / 2;
    state.pan.y = (vh - ih * state.zoom) / 2;
    
    updateTransform();
}

/**
 * Converts screen coordinates to image coordinates
 * @param {MouseEvent} e - Mouse event
 * @returns {{x: number, y: number}} Image coordinates
 */
function getImgCoords(e) {
    const rectV = viewport.getBoundingClientRect();
    const vx = e.clientX - rectV.left;
    const vy = e.clientY - rectV.top;

    const x = (vx - state.pan.x) / state.zoom;
    const y = (vy - state.pan.y) / state.zoom;
    
    return { x, y };
}

// =============================================================================
// Brush Tools System
// =============================================================================

/**
 * Sets the active brush tool
 * @param {string|null} tool - Tool name ('eraser'|'restore'|null)
 */
function setTool(tool) {
    state.brush.tool = tool;
    ['toolEraser', 'toolRestore'].forEach(id => $(id).classList.remove('active'));
    if (tool === 'eraser') $('toolEraser').classList.add('active');
    if (tool === 'restore') $('toolRestore').classList.add('active');
    updateCursor();
}

/**
 * Updates cursor display based on current tool and state
 */
function updateCursor() {
    const cursor = $('brushCursor');
    const size = state.brush.size;
    cursor.style.width = size + 'px';
    cursor.style.height = size + 'px';
    cursor.style.background = state.brush.tool === 'eraser' ? '#ef4444' : 
                              (state.brush.tool === 'restore' ? '#22c55e' : '#f0f0f5');

    // Set viewport cursor style
    viewport.style.cursor = state.spacePressed ? 'grab' : 
                           (state.brush.tool ? 'crosshair' : 'default');
    if (state.spacePressed && state.dragging) {
        viewport.style.cursor = 'grabbing';
    }
}

/**
 * Draws on the mask canvas at the current mouse position
 * Uses radial gradient for soft brush effect
 * @param {MouseEvent} e - Mouse event
 */
function draw(e) {
    if (!state.maskCtx || !state.brush.tool) return;

    const { x, y } = getImgCoords(e);
    const ctx = state.maskCtx;
    const r = state.brush.size / 2;
    const h = state.brush.hardness;

    // Create radial gradient for soft brush
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    const coreAlpha = 1;
    const edgeAlpha = 0;
    const fadeStart = h;

    g.addColorStop(0, `rgba(0,0,0,${coreAlpha})`);
    if (fadeStart > 0 && fadeStart < 1) {
        g.addColorStop(fadeStart, `rgba(0,0,0,${coreAlpha})`);
    }
    g.addColorStop(1, `rgba(0,0,0,${edgeAlpha})`);

    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);

    if (state.brush.tool === 'eraser') {
        ctx.globalCompositeOperation = 'destination-out';
        ctx.fill();
    } else {
        ctx.globalCompositeOperation = 'source-over';
        ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';

    renderCanvas();
}

/**
 * Binds mouse wheel to slider for fine control
 * @param {string} id - Slider element ID
 * @param {number} baseStep - Step size per wheel tick
 */
function bindWheel(id, baseStep) {
    const el = $(id);
    if (!el) return;

    let accumulator = 0;
    const pixelThreshold = 50;
    let resetTimer = null;

    el.addEventListener('wheel', e => {
        e.preventDefault();
        e.stopPropagation();

        let delta = e.deltaY;
        if (e.deltaMode === 1) delta *= 40;
        if (e.deltaMode === 2) delta *= 800;

        // Reset on direction change
        if (Math.sign(delta) !== Math.sign(accumulator) && accumulator !== 0) {
            accumulator = 0;
        }

        // Clear momentum buffer
        if (resetTimer) clearTimeout(resetTimer);
        resetTimer = setTimeout(() => { accumulator = 0; }, 150);

        accumulator += delta;

        if (Math.abs(accumulator) >= pixelThreshold) {
            const stepsToTake = Math.trunc(accumulator / pixelThreshold);

            if (stepsToTake !== 0) {
                const multiplier = e.shiftKey ? 10 : 1;
                const totalStep = baseStep * multiplier;

                const change = -(stepsToTake * totalStep);
                const oldVal = parseInt(el.value);
                el.value = oldVal + change;
                el.dispatchEvent(new Event('input'));

                accumulator = 0;
            }
        }
    }, { passive: false });
}

// =============================================================================
// Alignment System
// =============================================================================

/**
 * Ensures processed image is loaded for alignment view
 * @param {function(HTMLImageElement|null): void} cb - Callback with loaded image
 */
function ensureProcessedImage(cb) {
    if (processedImgCache) return cb(processedImgCache);
    if (!state.images.processed) return cb(null);

    const img = new Image();
    img.onload = () => {
        processedImgCache = img;
        cb(img);
    };
    img.src = 'data:image/png;base64,' + state.images.processed;
}

/**
 * Renders alignment preview with all busts overlaid
 */
function renderAlignment() {
    if (!visualCanvas || !visualCtx) return;

    const w = visualCanvas.width;
    const h = visualCanvas.height;
    visualCtx.clearRect(0, 0, w, h);

    ensureProcessedImage((img) => {
        if (!img) return;

        // Draw unselected busts first (underneath)
        state.busts.forEach(b => {
            if (b.id === state.selectedBustId || !b.enabled) return;
            drawBust(visualCtx, img, b, 0.4);
        });

        // Draw selected bust last (on top)
        const sel = state.busts.find(x => x.id === state.selectedBustId);
        if (sel && sel.enabled) {
            drawBust(visualCtx, img, sel, 0.75);
        }
    });
}

/**
 * Draws a single bust on the alignment canvas
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {HTMLImageElement} sourceImg - Source processed image
 * @param {Object} b - Bust region object
 * @param {number} opacity - Draw opacity (0-1)
 */
function drawBust(ctx, sourceImg, b, opacity) {
    const [left, top, right, bottom] = b.bbox;
    const sx = left;
    const sy = top;
    const sw = right - left;
    const sh = bottom - top;

    // Center bust in canvas with offsets
    const cx = visualCanvas.width / 2;
    const cy = visualCanvas.height / 2;
    const ox = b.offset_x || 0;
    const oy = b.offset_y || 0;

    const dx = cx - (sw / 2) + ox;
    const dy = cy - (sh / 2) + oy;

    ctx.globalAlpha = opacity;
    ctx.drawImage(sourceImg, sx, sy, sw, sh, dx, dy, sw, sh);
    ctx.globalAlpha = 1.0;
}

/**
 * Updates offset for currently selected bust
 * @param {string} prop - Property name ('offset_x' or 'offset_y')
 * @param {number} val - New offset value
 */
function updateSelectedOffset(prop, val) {
    if (state.selectedBustId) {
        const b = state.busts.find(x => x.id === state.selectedBustId);
        if (b) {
            b[prop] = val;
            renderCanvas();
        }
    }
}

// =============================================================================
// Busts Panel Rendering
// =============================================================================

/**
 * Renders the busts list panel based on current view and state
 */
function renderBusts() {
    const list = $('bustList');
    const bustsPanel = $('bustsPanel');
    const resultsPanel = $('resultsPanel');
    const bustCountBadge = $('bustCount');
    const rightPanelTitle = $('rightPanelTitle');

    // RESULTS VIEW - Show results summary
    if (state.view === 'results') {
        bustsPanel.style.display = 'none';
        resultsPanel.style.display = 'block';
        bustCountBadge.style.display = 'none';
        rightPanelTitle.textContent = translations[currentLang]['panel_results'] || '📊 Results';

        // Build summary
        const summary = $('resultsSummary');
        const enabledCount = state.results.length;
        const uniformSize = state.results.length > 0 ?
            `${state.results[0].width} × ${state.results[0].height}` : '—';

        summary.innerHTML = `
            <div style="margin-bottom:0.5rem;">
                <strong>${translations[currentLang]['lbl_exported'] || 'Exported'}:</strong> 
                ${enabledCount} ${translations[currentLang]['lbl_busts'] || 'busts'}
            </div>
            <div style="margin-bottom:0.5rem;">
                <strong>${translations[currentLang]['lbl_uniform_size'] || 'Uniform size'}:</strong> 
                ${uniformSize} px
            </div>
            <div style="margin-bottom:0.5rem;">
                <strong>${translations[currentLang]['lbl_format'] || 'Format'}:</strong> PNG (32-bit RGBA)
            </div>
            <div style="margin-bottom:0.5rem;">
                <strong>${translations[currentLang]['lbl_location'] || 'Saved to'}:</strong> 
                <code style="font-size:0.75rem; background:var(--bg-tertiary); padding:0.1rem 0.3rem; border-radius:3px;">output/${state.sessionId}/</code>
            </div>
            <div style="font-size:0.75rem; color:var(--text-dim); margin-top:1rem; padding:0.5rem; background:var(--bg-tertiary); border-radius:4px;">
                💡 ${translations[currentLang]['hint_download'] || 'Click Download to get ZIP with all files'}
            </div>
        `;

        // Show sprite sheet preview
        const spritePreview = $('spritePreviewResults');
        const spriteImg = $('spriteImgResults');
        if (state.images.spriteSheet) {
            spriteImg.src = 'data:image/png;base64,' + state.images.spriteSheet;
            spritePreview.style.display = 'block';
        } else {
            spritePreview.style.display = 'none';
        }

        return;
    }

    // OTHER VIEWS - Show busts panel
    bustsPanel.style.display = 'block';
    resultsPanel.style.display = 'none';
    bustCountBadge.style.display = 'inline';
    rightPanelTitle.textContent = translations[currentLang]['panel_busts'] || 'Busts';

    list.innerHTML = '';
    $('bustCount').textContent = state.busts.length;

    if (!state.busts.length) {
        list.innerHTML = translations[currentLang]['msg_no_busts'];
        $('proceedAlignBtn').style.display = 'none';
        $('offsetEditor').style.display = 'none';
        return;
    }

    const isDetection = state.view === 'detection';
    const isAlignment = state.view === 'alignment';

    $('proceedAlignBtn').style.display = isDetection ? 'block' : 'none';

    // Show offset editor only in alignment view with selection
    if (!isAlignment || !state.selectedBustId) {
        $('offsetEditor').style.display = 'none';
    } else {
        const b = state.busts.find(x => x.id === state.selectedBustId);
        if (b) {
            $('offX').value = b.offset_x || 0;
            $('offY').value = b.offset_y || 0;
            $('offXVal').textContent = b.offset_x || 0;
            $('offYVal').textContent = b.offset_y || 0;
            $('offsetEditor').style.display = 'block';
        }
    }

    // Render bust cards
    state.busts.forEach(b => {
        const card = document.createElement('div');
        card.className = `bust-card ${b.id === state.selectedBustId ? 'selected' : ''} ${!b.enabled ? 'disabled' : ''}`;
        card.onclick = () => {
            state.selectedBustId = b.id;
            renderBusts();
            if (state.view === 'alignment') renderCanvas();
        };

        const head = document.createElement('div');
        head.className = 'bust-header';

        const nameInp = document.createElement('input');
        nameInp.className = 'bust-name-input';
        nameInp.value = b.name;
        nameInp.onclick = e => e.stopPropagation();
        nameInp.onchange = e => b.name = e.target.value;

        const toggleBtn = document.createElement('button');
        toggleBtn.className = `bust-toggle ${b.enabled ? 'on' : 'off'}`;
        toggleBtn.textContent = b.enabled ? '✓' : '✕';
        toggleBtn.onclick = (e) => {
            e.stopPropagation();
            b.enabled = !b.enabled;
            renderBusts();
            if (state.view === 'alignment') renderCanvas();
        };

        head.appendChild(nameInp);
        head.appendChild(toggleBtn);

        const info = document.createElement('div');
        info.className = 'bust-info';
        info.textContent = `Area: ${b.area}px² | Center: ${b.center_x},${b.center_y}`;

        card.appendChild(head);
        card.appendChild(info);
        list.appendChild(card);
    });
}

// =============================================================================
// Mask Save Function
// =============================================================================

/**
 * Saves the current mask to the server
 * Converts alpha channel to grayscale for server processing
 * @async
 */
async function saveMask() {
    if (!state.maskCanvas || !state.sessionId) return;
    loading(translations[currentLang]['loading_save_mask']);
    
    try {
        // Create grayscale version of mask
        const tempC = document.createElement('canvas');
        tempC.width = state.maskCanvas.width;
        tempC.height = state.maskCanvas.height;
        const tempCtx = tempC.getContext('2d');

        tempCtx.fillStyle = 'black';
        tempCtx.fillRect(0, 0, tempC.width, tempC.height);
        tempCtx.clearRect(0, 0, tempC.width, tempC.height);
        tempCtx.drawImage(state.maskCanvas, 0, 0);

        // Convert alpha to white on black
        tempCtx.globalCompositeOperation = 'source-in';
        tempCtx.fillStyle = 'white';
        tempCtx.fillRect(0, 0, tempC.width, tempC.height);

        tempCtx.globalCompositeOperation = 'destination-over';
        tempCtx.fillStyle = 'black';
        tempCtx.fillRect(0, 0, tempC.width, tempC.height);
        tempCtx.globalCompositeOperation = 'source-over';

        const blob = await new Promise(r => tempC.toBlob(r, 'image/png'));
        const fd = new FormData();
        fd.append('session_id', state.sessionId);
        fd.append('mask_file', blob, 'mask.png');

        const res = await fetch(`${API}/api/update-mask`, { method: 'POST', body: fd });
        if (!res.ok) throw new Error("Save failed");
        const d = await res.json();

        state.images.processed = d.preview;
        state.images.mask = d.mask;
        initMaskCanvas(visualCanvas.width, visualCanvas.height, d.mask);

        if (d.clear_busts) {
            state.busts = [];
            renderBusts();
        }

        toast(translations[currentLang]['toast_mask_saved']);
    } catch (e) { 
        toast(translations[currentLang]['toast_save_err'] + ' ' + e.message, 'error'); 
    }
    loaded();
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Uploads an image file to the server
 * @async
 * @param {File} file - Image file to upload
 */
async function upload(file) {
    if (!file) return;
    loading(translations[currentLang]['loading_upload']);
    
    try {
        const fd = new FormData();
        fd.append('file', file);
        const r = await fetch(`${API}/api/upload`, { method: 'POST', body: fd });
        const d = await r.json();

        // Reset state for new image
        state.sessionId = d.session_id;
        state.images = { original: d.preview };
        state.busts = [];
        state.selectedBustId = null;
        state.results = [];
        state.cachedImages = {};
        processedImgCache = null;
        state.autoTolerance = d.auto_tolerance || 30;

        // Reset visual canvas
        visualCanvas = null;
        visualCtx = null;

        // Update tolerance sliders
        if ($('validatorTolerance')) {
            $('validatorTolerance').value = state.autoTolerance;
            $('valTolVal').textContent = state.autoTolerance;
        }

        hide('detectSection');
        hide('exportSection');
        show('bgSection');
        
        state.view = 'original';
        renderBusts();
        renderCanvas();
        
        console.log('Upload successful:', d);
        toast(`${translations[currentLang]['toast_uploaded']} ${d.width}×${d.height}px`);
    } catch (e) { 
        toast(translations[currentLang]['toast_err'] + ' ' + e.message, 'error'); 
    }
    loaded();
}

/**
 * Processes background removal on the uploaded image
 * @async
 */
async function removeBackground() {
    if (!state.sessionId) {
        console.error('No session ID!');
        return;
    }
    
    const method = $('bgMethod').value;
    console.log('Starting Remove Background...', { method, session: state.sessionId });
    loading(translations[currentLang]['loading_process']);

    try {
        const fd = new FormData();
        fd.append('session_id', state.sessionId);
        fd.append('method', method);

        // Tolerance
        if ($('validatorBox').style.display !== 'none' || method === 'color_based') {
            fd.append('tolerance', $('validatorTolerance').value);
        } else {
            fd.append('tolerance', 30);
        }

        // Validator params
        if ($('hybridCleansing') && $('hybridCleansing').checked) {
            fd.append('hybrid_cleansing_enabled', true);
            fd.append('hybrid_cleansing_erosion', $('validatorErosion').value);
        }

        // Refinement params
        fd.append('mask_erode', $('erode').value);
        fd.append('mask_dilate', $('dilate').value);
        fd.append('alpha_matting', $('alphaMatting').checked);

        // Feather params
        fd.append('feather_enabled', $('featherOn').checked);
        fd.append('feather_radius', $('featherR').value);
        fd.append('feather_strength', $('featherS').value / 100);

        // Despill params
        fd.append('despill_enabled', $('despillOn').checked);
        fd.append('despill_strength', $('despillS').value / 100);
        fd.append('despill_color', $('despillColor').value);

        // Decontamination params
        if ($('deconOn').checked) {
            fd.append('decontaminate_enabled', true);
            fd.append('decontaminate_strength', $('deconS').value / 100);
            fd.append('decontaminate_threshold', $('deconTh').value);
        }

        // Difference matting secondary file
        if (method === 'difference_matting' && secondaryFile) {
            fd.append('secondary_file', secondaryFile);
        }

        const r = await fetch(`${API}/api/remove-background`, { method: 'POST', body: fd });
        if (!r.ok) throw new Error((await r.json()).detail);

        const d = await r.json();
        state.images.processed = d.preview;
        state.images.mask = d.mask;
        initMaskCanvas(d.width, d.height, d.mask);

        show('detectSection');
        state.view = 'processed';
        document.querySelector('[data-view="processed"]').click();
        toast(translations[currentLang]['toast_done']);
    } catch (e) { 
        toast('Chyba: ' + e.message, 'error'); 
    }
    loaded();
}

/**
 * Detects bust regions in the processed image
 * @async
 */
async function detectBusts() {
    if (!state.sessionId) return;
    loading(translations[currentLang]['loading_detect']);
    
    try {
        const fd = new FormData();
        fd.append('session_id', state.sessionId);
        fd.append('min_area_ratio', $('minArea').value / 100);
        
        const r = await fetch(`${API}/api/detect-busts`, { method: 'POST', body: fd });
        const d = await r.json();
        
        state.busts = d.busts;
        state.images.detection = d.visualization;
        
        show('exportSection');
        renderBusts();
        state.view = 'detection';
        document.querySelector('[data-view="detection"]').click();
        toast(`${translations[currentLang]['toast_detected']} ${d.count}`);
    } catch (e) { 
        toast('Chyba: ' + e.message, 'error'); 
    }
    loaded();
}

/**
 * Extracts busts and creates export files
 * @async
 */
async function extractBusts() {
    if (!state.sessionId || !state.busts.length) return;
    loading(translations[currentLang]['loading_extract']);
    
    try {
        // Update all bust data on server
        const fd0 = new FormData();
        fd0.append('session_id', state.sessionId);
        fd0.append('busts_json', JSON.stringify(state.busts));
        await fetch(`${API}/api/update-all-busts`, { method: 'POST', body: fd0 });

        // Extract
        const fd = new FormData();
        fd.append('session_id', state.sessionId);
        fd.append('padding', $('padding').value);
        fd.append('uniform_width', $('uniformW').value);
        fd.append('uniform_height', $('uniformH').value);
        fd.append('sprite_sheet_padding', $('sheetPad').value);
        fd.append('export_individual', $('expIndiv').checked);
        fd.append('export_sprite_sheet', $('expSheet').checked);

        const fmt = $('exportFormat') ? $('exportFormat').value : 'PNG';
        fd.append('format', fmt);

        const r = await fetch(`${API}/api/extract`, { method: 'POST', body: fd });
        const d = await r.json();
        
        state.results = d.results;
        state.images.spriteSheet = d.sprite_sheet || null;

        state.view = 'results';
        renderBusts();
        document.querySelector('[data-view="results"]').click();
        toast(`${translations[currentLang]['toast_extracted']} ${d.uniform_size.width}×${d.uniform_size.height}px`);
    } catch (e) { 
        toast('Chyba: ' + e.message, 'error'); 
    }
    loaded();
}

/**
 * Downloads all extracted files as ZIP
 * @async
 */
async function downloadAll() {
    if (!state.sessionId) return;
    loading(translations[currentLang]['loading_download']);
    
    try {
        const fd = new FormData();
        fd.append('session_id', state.sessionId);
        
        const r = await fetch(`${API}/api/download-all`, { method: 'POST', body: fd });
        const blob = await r.blob();
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'busts.zip';
        a.click();
        URL.revokeObjectURL(url);
        
        toast(translations[currentLang]['toast_downloaded']);
    } catch (e) { 
        toast('Chyba: ' + e.message, 'error'); 
    }
    loaded();
}

/**
 * Handles secondary file upload for difference matting
 * @param {File} file - Secondary image file
 */
function handleSecUpload(file) {
    if (!file) return;
    secondaryFile = file;
    $('secFileStatus').style.display = 'block';
    $('uploadZoneSec').style.borderColor = 'var(--success)';
    toast(translations[currentLang]['toast_sec_uploaded']);
}

// =============================================================================
// Slider Binding Helper
// =============================================================================

/**
 * Binds a slider input to a value display element
 * @param {string} id - Slider element ID
 * @param {string} outId - Output display element ID
 * @param {function} [fmt=v=>v] - Value formatter function
 */
function bindSlider(id, outId, fmt = v => v) {
    const el = $(id);
    if (el && $(outId)) {
        el.oninput = () => $(outId).textContent = fmt(el.value);
    }
}

// =============================================================================
// Event Listeners Initialization
// =============================================================================

/**
 * Initializes all event listeners when DOM is ready
 */
function initEventListeners() {
    // Language buttons
    $('langEn').onclick = () => setLanguage('en');
    $('langCz').onclick = () => setLanguage('cz');
    
    // Method selector
    if ($('bgMethod')) $('bgMethod').onchange = updateUiForMethod;

    // Proceed to alignment button
    if ($('proceedAlignBtn')) {
        $('proceedAlignBtn').onclick = () => {
            state.view = 'alignment';
            document.querySelector('[data-view="alignment"]').click();
        };
    }

    // Tool buttons
    $('toolEraser').onclick = function() { 
        this.blur(); 
        setTool(state.brush.tool === 'eraser' ? null : 'eraser'); 
    };
    $('toolRestore').onclick = function() { 
        this.blur(); 
        setTool(state.brush.tool === 'restore' ? null : 'restore'); 
    };
    $('btnUndo').onclick = undo;
    $('btnRedo').onclick = redo;
    $('toggleTools').onclick = () => {
        const t = $('brushToolbar');
        t.style.display = t.style.display === 'none' ? 'flex' : 'none';
    };

    // Brush controls
    $('brushSize').oninput = (e) => {
        state.brush.size = parseInt(e.target.value);
        $('brushSizeVal').textContent = state.brush.size + 'px';
        updateCursor();
    };

    $('brushHardness').oninput = (e) => {
        state.brush.hardness = parseInt(e.target.value) / 100;
        $('brushHardnessVal').textContent = e.target.value + '%';
    };

    // Bind wheel controls
    bindWheel('brushSize', 1);
    bindWheel('brushHardness', 5);
    bindWheel('offX', 1);
    bindWheel('offY', 1);

    // Prevent toolbar from hijacking viewport events
    $('brushToolbar').onmousedown = e => e.stopPropagation();
    $('brushToolbar').addEventListener('wheel', e => e.stopPropagation(), { passive: false });

    // Toolbar drag
    const tbEl = $('brushToolbar');
    const tbH = $('toolbarDragHandle');
    const tbDrag = { active: false, x: 0, y: 0 };

    tbH.onmousedown = (e) => {
        tbDrag.active = true;
        const offL = tbEl.offsetLeft;
        const offT = tbEl.offsetTop;
        tbEl.style.right = 'auto';
        tbEl.style.left = offL + 'px';
        tbEl.style.top = offT + 'px';
        tbDrag.x = e.clientX - offL;
        tbDrag.y = e.clientY - offT;
        e.stopPropagation();
        e.preventDefault();
    };

    // Global mouse move handler
    window.addEventListener('mousemove', e => {
        state.clientMouse = { x: e.clientX, y: e.clientY };

        if (tbDrag.active) {
            tbEl.style.left = (e.clientX - tbDrag.x) + 'px';
            tbEl.style.top = (e.clientY - tbDrag.y) + 'px';
        }

        if (state.dragging) {
            const dx = e.clientX - state.lastMouse.x;
            const dy = e.clientY - state.lastMouse.y;
            state.pan.x += dx;
            state.pan.y += dy;
            state.lastMouse = { x: e.clientX, y: e.clientY };
            updateTransform();
        } else if (state.brush.active) {
            draw(e);
        }
    });

    // Global mouse up handler
    window.addEventListener('mouseup', () => {
        if (state.brush.active) {
            console.log("MouseUp: Brush was active. Saving history.");
            saveHistoryState();
        }

        tbDrag.active = false;
        state.dragging = false;
        state.brush.active = false;
        viewport.classList.remove('dragging');
    });

    // Keyboard shortcuts
    window.addEventListener('keydown', e => {
        if (e.target.tagName === 'INPUT') return;

        if (e.ctrlKey && e.code === 'KeyZ') { e.preventDefault(); undo(); return; }
        if (e.ctrlKey && e.code === 'KeyY') { e.preventDefault(); redo(); return; }

        if (e.code === 'Space') {
            e.preventDefault();
            if (!state.spacePressed) {
                state.spacePressed = true;
                if (state.brush.active) {
                    state.brush.active = false;
                    state.dragging = true;
                    if (state.clientMouse) {
                        state.lastMouse = { ...state.clientMouse };
                    }
                }
                updateCursor();
                if (state.dragging) viewport.classList.add('dragging');
            }
        }
        if (e.key === 'e') setTool('eraser');
        if (e.key === 'r') setTool('restore');
        if (e.ctrlKey && e.key === 's') { e.preventDefault(); saveMask(); }
    });

    window.addEventListener('keyup', e => {
        if (e.code === 'Space') {
            state.spacePressed = false;
            const isMouseDown = (state.clientMouse && e.buttons === 1) || false;

            if (state.dragging && isMouseDown && state.brush.tool) {
                state.dragging = false;
                state.brush.active = true;
            }

            if (!isMouseDown) {
                state.dragging = false;
            }

            updateCursor();
            viewport.classList.remove('dragging');
        }
    });

    // Viewport mouse events
    viewport.addEventListener('mousedown', e => {
        if (e.button !== 0) return;

        const isPan = state.spacePressed || !state.brush.tool || 
                      (state.view !== 'processed' && state.view !== 'mask');

        if (isPan) {
            state.dragging = true;
            state.lastMouse = { x: e.clientX, y: e.clientY };
            viewport.classList.add('dragging');
            e.preventDefault();
        } else {
            state.brush.active = true;
            e.preventDefault();
            e.stopPropagation();
            draw(e);
        }
    });

    // Viewport wheel zoom
    viewport.addEventListener('wheel', e => {
        e.preventDefault();
        const rect = viewport.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const sensitivity = 0.0015;
        const safeDelta = Math.max(-200, Math.min(200, e.deltaY));
        const factor = Math.exp(-safeDelta * sensitivity);

        zoomTo(state.zoom * factor, mouseX, mouseY);
    }, { passive: false });

    // Zoom buttons
    $('zoomIn').onclick = () => zoomTo(state.zoom * 1.25);
    $('zoomOut').onclick = () => zoomTo(state.zoom / 1.25);
    $('zoomFit').onclick = fitToView;
    $('zoom100').onclick = () => {
        state.zoom = 1;
        if (visualCanvas) {
            state.pan.x = (viewport.clientWidth - visualCanvas.width) / 2;
            state.pan.y = (viewport.clientHeight - visualCanvas.height) / 2;
        } else {
            state.pan = { x: 0, y: 0 };
        }
        updateTransform();
    };

    // Background buttons
    const bgBtns = ['bgTransparent', 'bgDark', 'bgLight'];
    bgBtns.forEach(id => {
        $(id).onclick = () => {
            bgBtns.forEach(b => $(b).classList.remove('active'));
            $(id).classList.add('active');
            viewport.className = 'canvas-viewport ' +
                (id === 'bgTransparent' ? 'bg-transparent' : 
                 id === 'bgDark' ? 'bg-dark' : 'bg-light');
        };
    });

    // Tab navigation
    document.querySelectorAll('.tab').forEach(tab => {
        tab.onclick = () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            state.view = tab.dataset.view;

            if (state.view !== 'results') {
                container.style.display = 'block';
                resetContainerStyles();
                container.style.position = 'absolute';
            }

            renderCanvas();
            renderBusts();
        };
    });

    // Validator toggle
    const hybC = $('hybridCleansing');
    if (hybC) {
        hybC.onchange = (e) => {
            if ($('validatorSettings')) {
                $('validatorSettings').style.display = e.target.checked ? 'block' : 'none';
            }
        };
    }

    // Decontamination toggle
    const decOn = $('deconOn');
    if (decOn) {
        decOn.onchange = (e) => {
            if ($('deconSettings')) {
                $('deconSettings').style.display = e.target.checked ? 'block' : 'none';
            }
        };
    }

    // Bind all sliders
    bindSlider('validatorTolerance', 'valTolVal');
    bindSlider('validatorErosion', 'valEroVal');
    bindSlider('erode', 'erodeVal');
    bindSlider('dilate', 'dilateVal');
    bindSlider('featherR', 'featherRVal');
    bindSlider('featherS', 'featherSVal', v => (v / 100).toFixed(2));
    bindSlider('despillS', 'despillSVal', v => (v / 100).toFixed(2));
    bindSlider('deconS', 'deconSVal', v => (v / 100).toFixed(2));
    bindSlider('deconTh', 'deconThVal');
    bindSlider('minArea', 'minAreaVal', v => v + '%');
    bindSlider('padding', 'paddingVal');
    bindSlider('sheetPad', 'sheetPadVal');
    bindSlider('offX', 'offXVal');
    bindSlider('offY', 'offYVal');

    // File input handlers
    if ($('fileInput')) $('fileInput').onchange = e => upload(e.target.files[0]);

    // Action buttons
    $('removeBgBtn').onclick = removeBackground;
    $('detectBtn').onclick = detectBusts;
    $('extractBtn').onclick = extractBusts;
    $('downloadBtnPanel').onclick = downloadAll;
    $('saveMaskBtn').onclick = saveMask;

    // Secondary upload for difference matting
    $('uploadZoneSec').onclick = () => $('fileInputSec').click();
    $('uploadZoneSec').ondragover = e => e.preventDefault();
    $('uploadZoneSec').ondrop = e => {
        e.preventDefault();
        handleSecUpload(e.dataTransfer.files[0]);
    };
    $('fileInputSec').onchange = e => handleSecUpload(e.target.files[0]);

    // Offset sliders
    $('offX').oninput = (e) => {
        const val = parseInt(e.target.value);
        $('offXVal').textContent = val;
        updateSelectedOffset('offset_x', val);
    };
    $('offY').oninput = (e) => {
        const val = parseInt(e.target.value);
        $('offYVal').textContent = val;
        updateSelectedOffset('offset_y', val);
    };

    // Reset offsets button
    $('resetOffsetsBtn').onclick = () => {
        if (state.selectedBustId) {
            const b = state.busts.find(x => x.id === state.selectedBustId);
            if (b) {
                b.offset_x = 0;
                b.offset_y = 0;
                $('offX').value = 0;
                $('offY').value = 0;
                $('offXVal').textContent = 0;
                $('offYVal').textContent = 0;
                renderCanvas();
            }
        }
    };
}

// =============================================================================
// Application Initialization
// =============================================================================

/**
 * Main initialization function
 * Called when the page loads
 */
function initApp() {
    // Update version display
    document.title = `Bust Extractor Pro v${APP_VERSION}`;
    if ($('versionBadge')) $('versionBadge').textContent = `v${APP_VERSION}`;

    // Initialize event listeners
    initEventListeners();

    // Set default language and update UI
    setLanguage('en');
    updateUiForMethod();
    renderCanvas();

    console.log(`Bust Extractor Pro v${APP_VERSION} LOADED`);
    console.log('State:', state);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
