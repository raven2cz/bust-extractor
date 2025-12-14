/**
 * Bust Extractor Pro - Localization Module
 * =========================================
 * Contains all UI text translations for supported languages.
 * 
 * @fileoverview Internationalization (i18n) translations for the application UI.
 * @author raven2cz
 * @version 2.0
 * @license MIT
 * 
 * Supported Languages:
 * - English (en) - Default
 * - Czech (cz)
 * 
 * Usage:
 * - Translation keys are referenced via data-i18n attributes in HTML
 * - Title attributes use data-i18n-title
 * - Access programmatically via translations[lang][key]
 */

'use strict';

/**
 * @typedef {Object} TranslationSet
 * @property {string} title - Application title
 * @property {string} header_settings - Settings panel header
 * @property {string} sec_image - Image section title
 * @property {string} upload_text - Upload zone text
 * ... and many more translation keys
 */

/**
 * Translation dictionary containing all UI strings
 * @type {Object<string, TranslationSet>}
 */
const translations = {
    /**
     * Czech language translations
     */
    cz: {
        // Application
        title: "Bust Extractor Pro",
        header_settings: "Nastavení",
        
        // Image Upload Section
        sec_image: "📁 Obrázek",
        upload_text: "Klikněte nebo přetáhněte",
        sec_image_sec: "🌑 Druhý obrázek (Černé pozadí)",
        upload_text_sec: "Nahrajte verzi na černém pozadí",
        status_uploaded: "✓ Nahráno",
        
        // Background Removal Section
        sec_bg: "🎨 Odstranění pozadí",
        box_model: "1. Model a Metoda",
        lbl_model: "Vyberte model",
        box_validator: "2. Hybridní Validátor",
        badge_recom: "DOPORUČENO",
        chk_validator: "Aktivovat validátor",
        desc_validator: "Opraví místa, kde AI zapomněla vymazat pozadí (díry mezi vlasy).",
        lbl_tol: "Tolerance barvy",
        lbl_safety: "Ochrana (Min. velikost)",
        desc_safety: "Ignoruje malé 'chyby'. Větší hodnota = Méně děr.",
        
        // Mask Refinement
        box_refine: "3. Vylepšení masky",
        head_erode: "Erode & Dilate",
        chk_alpha: "Alpha Matting (Jemnější okraje)",
        head_feather: "Feather (Prolnutí)",
        chk_feather: "Povolit feathering",
        lbl_radius: "Radius",
        lbl_strength: "Síla",
        head_despill: "Despill (Odlesky)",
        chk_despill: "Povolit despill",
        lbl_color: "Barva",
        
        // Post Processing
        box_post: "4. Color Decontamination",
        chk_decon: "Aktivovat čištění hran",
        lbl_thresh: "Práh (Threshold)",
        desc_thresh: "Pixely nad touto hodnotou Alpha se nemění (chrání vnitřek).",
        
        // Actions
        btn_process: "🚀 SPUSTIT ZPRACOVÁNÍ",
        
        // Detection Section
        sec_detect: "🔍 Detekce",
        lbl_min_size: "Min. velikost oblasti (filtr šumu)",
        btn_detect: "🔍 Detekovat busty",
        
        // Export Section
        sec_export: "📦 Export",
        lbl_padding: "Padding",
        lbl_width: "Šířka",
        lbl_height: "Výška",
        chk_individual: "Jednotlivé soubory",
        chk_sheet: "Sprite Sheet",
        lbl_sheet_pad: "Sheet mezera",
        btn_extract: "✂️ Extrahovat",
        btn_download: "📥 Stáhnout ZIP",
        
        // Tabs
        tab_original: "Originál",
        tab_processed: "Zpracovaný",
        tab_mask: "Maska",
        tab_detect: "Detekce",
        tab_align: "Zarovnání",
        tab_results: "Výsledky",
        
        // Busts Panel
        panel_busts: "Busty",
        msg_no_busts: "Detekované busty se zobrazí zde",
        head_align: "📐 Zarovnání vybraného bustu",
        btn_save: "💾 Uložit",
        btn_preview: "👁️ Náhled",
        head_sprite: "✨ Sprite Sheet",
        
        // Loading Messages
        loading_process: "Zpracovávám...",
        loading_upload: "Nahrávám...",
        loading_detect: "Detekuji...",
        loading_preview: "Generuji náhled...",
        loading_extract: "Extrahuji...",
        loading_download: "Stahuji...",
        loading_save_mask: "Ukládám masku...",
        
        // Toast Messages
        toast_done: "Hotovo!",
        toast_uploaded: "Nahráno:",
        toast_detected: "Detekováno",
        toast_saved: "Offsety uloženy",
        toast_extracted: "Extrahováno!",
        toast_downloaded: "Staženo!",
        toast_err: "Chyba:",
        toast_mask_saved: "Maska uložena! Detekce je nyní přesnější.",
        toast_save_err: "Chyba uložení:",
        toast_sec_uploaded: "Druhý obrázek nahrán",
        
        // Method Descriptions
        method_birefnet: "🎯 <strong>BiRefNet:</strong> Nejlepší AI model. Skvělé okraje.",
        method_diff: "🎬 <strong>Difference:</strong> 2 obrázky (bílý + černý). Dokonalý ořez.",
        method_color: "🎨 <strong>Barva:</strong> Klasické klíčování. Pouze pro solidní pozadí.",
        method_anime: "Optimální pro Anime.",
        method_general: "Univerzální standard.",
        method_u2net: "Rychlý náhled.",
        
        // Tools
        tool_tools: "NÁSTROJE",
        tool_eraser_title: "Guma (E) - Zprůhlední pixely",
        tool_restore_title: "Obnovit (R) - Vrátí původní obraz",
        tool_undo_title: "Zpět (Ctrl+Z)",
        tool_redo_title: "Vpřed (Ctrl+Y)",
        tool_size_title: "Velikost štětce",
        tool_hardness_title: "Tvrdost (Softness)",
        tool_save_title: "Uložit změny (Ctrl+S)",
        tool_apply: "💾 Použít",
        lbl_size: "Velikost",
        lbl_hard: "Tvrdost",
        
        // Alignment & Results
        btn_reset: "↺ Reset",
        btn_proceed_align: "➡️ Přejít na Zarovnání",
        panel_results: "📊 Výsledky",
        head_results_info: "📊 Souhrn exportu",
        lbl_exported: "Exportováno",
        lbl_busts: "bustů",
        lbl_uniform_size: "Uniformní velikost",
        lbl_format: "Formát",
        lbl_location: "Uloženo v",
        hint_download: "Klikněte na Stáhnout pro ZIP se všemi soubory",
        hint_click_zoom: "Klikněte pro zobrazení v plné velikosti"
    },
    
    /**
     * English language translations (default)
     */
    en: {
        // Application
        title: "Bust Extractor Pro",
        header_settings: "Settings",
        
        // Image Upload Section
        sec_image: "📁 Image",
        upload_text: "Click or Drop Image",
        sec_image_sec: "🌑 Secondary Image (Black BG)",
        upload_text_sec: "Upload black background version",
        status_uploaded: "✓ Uploaded",
        
        // Background Removal Section
        sec_bg: "🎨 Background Removal",
        box_model: "1. Model & Method",
        lbl_model: "Select Model",
        box_validator: "2. Hybrid Validator",
        badge_recom: "RECOMMENDED",
        chk_validator: "Enable Validator",
        desc_validator: "Fixes missed background spots (e.g. hair gaps).",
        lbl_tol: "Color Tolerance",
        lbl_safety: "Safety (Min Area)",
        desc_safety: "Ignores small spots. Higher = Fewer holes.",
        
        // Mask Refinement
        box_refine: "3. Mask Refinement",
        head_erode: "Erode & Dilate",
        chk_alpha: "Alpha Matting (Softer Edges)",
        head_feather: "Feather",
        chk_feather: "Enable Feathering",
        lbl_radius: "Radius",
        lbl_strength: "Strength",
        head_despill: "Despill",
        chk_despill: "Enable Despill",
        lbl_color: "Color",
        
        // Post Processing
        box_post: "4. Color Decontamination",
        chk_decon: "Enable Decontamination",
        lbl_thresh: "Threshold",
        desc_thresh: "Pixels above this Alpha are protected.",
        
        // Actions
        btn_process: "🚀 PROCESS IMAGE",
        
        // Detection Section
        sec_detect: "🔍 Detection",
        lbl_min_size: "Min. Detectable Area (Noise Filter)",
        btn_detect: "🔍 Detect Busts",
        
        // Export Section
        sec_export: "📦 Export",
        lbl_padding: "Padding",
        lbl_width: "Width",
        lbl_height: "Height",
        chk_individual: "Individual Files",
        chk_sheet: "Sprite Sheet",
        lbl_sheet_pad: "Sheet Padding",
        btn_extract: "✂️ Extract",
        btn_download: "📥 Download ZIP",
        
        // Tabs
        tab_original: "Original",
        tab_processed: "Processed",
        tab_mask: "Mask",
        tab_detect: "Detection",
        tab_align: "Alignment",
        tab_results: "Results",
        
        // Busts Panel
        panel_busts: "Busts",
        msg_no_busts: "Detected busts will appear here",
        head_align: "📐 Align Selected Bust",
        btn_save: "💾 Save",
        btn_preview: "👁️ Preview",
        head_sprite: "✨ Sprite Sheet",
        
        // Loading Messages
        loading_process: "Processing...",
        loading_upload: "Uploading...",
        loading_detect: "Detecting...",
        loading_preview: "Generating preview...",
        loading_extract: "Extracting...",
        loading_download: "Downloading...",
        loading_save_mask: "Saving mask...",
        
        // Toast Messages
        toast_done: "Done!",
        toast_uploaded: "Uploaded:",
        toast_detected: "Detected",
        toast_saved: "Offsets saved",
        toast_extracted: "Extracted!",
        toast_downloaded: "Downloaded!",
        toast_err: "Error:",
        toast_mask_saved: "Mask saved! Detection precision updated.",
        toast_save_err: "Save Error:",
        toast_sec_uploaded: "Secondary image uploaded",
        
        // Method Descriptions
        method_birefnet: "🎯 <strong>BiRefNet:</strong> Best AI model. Great edges.",
        method_diff: "🎬 <strong>Difference:</strong> 2 images (White + Black). Perfect cut.",
        method_color: "🎨 <strong>Color:</strong> Classic keying. Solid background only.",
        method_anime: "Optimal for Anime.",
        method_general: "Universal standard.",
        method_u2net: "Fast preview.",
        
        // Tools
        tool_tools: "TOOLS",
        tool_eraser_title: "Eraser (E) - Makes pixels transparent",
        tool_restore_title: "Restore Brush (R) - Brings back original image",
        tool_undo_title: "Undo (Ctrl+Z)",
        tool_redo_title: "Redo (Ctrl+Y)",
        tool_size_title: "Brush Size",
        tool_hardness_title: "Brush Softness (Hardness)",
        tool_save_title: "Save Changes (Ctrl+S) - Applies mask to server",
        tool_apply: "💾 Apply",
        lbl_size: "Size",
        lbl_hard: "Hardness",
        
        // Alignment & Results
        btn_reset: "↺ Reset",
        btn_proceed_align: "➡️ Proceed to Alignment",
        panel_results: "📊 Results",
        head_results_info: "📊 Export Summary",
        lbl_exported: "Exported",
        lbl_busts: "busts",
        lbl_uniform_size: "Uniform size",
        lbl_format: "Format",
        lbl_location: "Saved to",
        hint_download: "Click Download to get ZIP with all files",
        hint_click_zoom: "Click to view full size"
    }
};
