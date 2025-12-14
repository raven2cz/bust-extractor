# Bust Extractor Pro v2.0

Professional web-based application for extracting character portraits (busts) from sprite sheets with AI-powered background removal, interactive mask editing, and animation-ready export.

![Version](https://img.shields.io/badge/version-2.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ Features

### 🎨 Advanced Background Removal
- **BiRefNet** - State-of-the-art AI model with excellent edge detection
- **Difference Matting** - Perfect extraction using white + black background pair
- **Color-based** - Classic chroma keying for solid color backgrounds
- **ISNet Anime** - Optimized for anime/cartoon style images
- **U2Net** - Fast general-purpose model

### 🔧 Professional Editing Tools
- **Hybrid Validator** - Automatically fixes AI artifacts (holes in hair, incomplete removal)
- **Interactive Mask Editor** - Eraser and Restore brushes with adjustable size/hardness
- **Undo/Redo History** - Full history support (Ctrl+Z / Ctrl+Y)
- **Alpha Matting** - Smooth, natural edge transitions
- **Feathering** - Configurable edge softening
- **Despill** - Remove color bleeding from green/blue screens
- **Color Decontamination** - Clean up edge color artifacts

### 📐 Alignment & Animation Support
- **Real-time Alignment Preview** - Position busts with live overlay visualization
- **Per-bust Offset Control** - Fine-tune X/Y position for each character
- **Uniform Sizing** - All busts exported at consistent dimensions
- **Sprite Sheet Generation** - Single-file animation strip ready for game engines

### 🌐 Modern Web Interface
- **Drag & Drop Upload** - Easy file import
- **Tabbed Workflow** - Original → Processed → Mask → Detection → Alignment → Results
- **Pan & Zoom** - Navigate large images with mouse wheel and drag
- **Bilingual UI** - English and Czech language support
- **Dark Theme** - Easy on the eyes

## 📁 Project Structure

```
bust-extractor-pro/
├── run.py                    # Application launcher
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
├── README.md                # This file
│
├── backend/
│   └── server.py            # FastAPI backend (2000+ lines, fully documented)
│       ├── BackgroundRemover    # AI/color-based background removal
│       ├── EdgeRefiner          # Mask refinement & post-processing
│       ├── BustSegmenter        # Connected component analysis
│       ├── BustExtractor        # Cropping & sprite sheet generation
│       └── API Endpoints        # RESTful API (11 endpoints)
│
├── frontend/
│   ├── index.html           # Main HTML structure (~600 lines)
│   ├── css/
│   │   └── styles.css       # All styling (~900 lines, CSS variables)
│   └── js/
│       ├── app.js           # Application logic (~2800 lines, JSDoc)
│       └── locales.js       # Internationalization (EN/CZ)
│
├── uploads/                 # Temporary upload storage (auto-created)
└── outputs/                 # Extracted files (auto-created)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- NVIDIA GPU recommended for AI models (CPU fallback available)

### Installation

```bash
# Clone or download the project
cd bust-extractor-pro

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Start with launcher (opens browser automatically)
python run.py

# Or run server directly
cd backend
python server.py
```

Navigate to `http://localhost:8000` in your browser.

## 📖 Workflow Guide

### Step 1: Upload Image
- Drag and drop your sprite sheet onto the upload zone
- Or click to browse and select a file
- Supported formats: PNG, JPG, WebP

### Step 2: Remove Background
1. **Select Method:**
   - Use **BiRefNet** for best quality on most images
   - Use **Difference Matting** if you have both white and black background versions
   - Use **Color-based** for simple solid color backgrounds

2. **Configure Options:**
   - Enable **Hybrid Validator** to fix common AI mistakes
   - Adjust **Tolerance** for color-based detection
   - Enable **Alpha Matting** for smoother edges
   - Configure **Feathering** for soft edge transitions

3. Click **🚀 START PROCESSING**

### Step 3: Edit Mask (Optional)
- Switch to **Mask** tab to see the extraction mask
- Use **Eraser (E)** to remove unwanted areas
- Use **Restore (R)** to bring back accidentally removed parts
- **Undo (Ctrl+Z)** / **Redo (Ctrl+Y)** as needed
- Click **💾 Apply** to save changes

### Step 4: Detect Busts
- Switch to **Detection** tab
- Adjust **Min. size** threshold if needed
- Click **🔍 Detect Busts**
- Review detected regions with colored bounding boxes

### Step 5: Align Busts
- Click **➡️ Proceed to Alignment**
- Select a bust from the right panel
- Use **Offset X/Y** sliders to fine-tune position
- All busts shown semi-transparent for reference

### Step 6: Export
1. Configure export settings (padding, dimensions, format)
2. Click **✂️ Extract**
3. Review results in **Results** tab
4. Click **📥 Download ZIP** to save all files

## ⚙️ API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve web interface |
| `/api/upload` | POST | Upload sprite sheet |
| `/api/remove-background` | POST | Process background removal |
| `/api/update-mask` | POST | Save edited mask |
| `/api/detect-busts` | POST | Detect bust regions |
| `/api/update-bust` | POST | Update single bust |
| `/api/update-all-busts` | POST | Batch update busts |
| `/api/preview-alignment` | POST | Generate alignment preview |
| `/api/extract` | POST | Extract and export busts |
| `/api/download-all` | POST | Download ZIP archive |

## 🎮 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| E | Eraser tool |
| R | Restore tool |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+S | Save mask |
| Space + Drag | Pan view |
| Mouse Wheel | Zoom |

## 🛠️ Requirements

### Core Dependencies
```
fastapi>=0.109.0
uvicorn>=0.27.0
pillow>=10.2.0
numpy>=1.26.0
scipy>=1.12.0
opencv-python>=4.9.0
python-multipart>=0.0.6
aiofiles>=23.2.1
```

### AI Model Dependencies
```
rembg>=2.0.50
onnxruntime-gpu>=1.17.0  # GPU (recommended)
# or: onnxruntime>=1.17.0  # CPU fallback
```

## 🐛 Troubleshooting

### "CUDA out of memory"
- Reduce image size before upload
- Use CPU-based models (Color-based, U2Net)

### "Model not found"
- Ensure rembg is installed: `pip install rembg`
- Models download automatically on first use

### "Slow processing"
- Enable GPU: `pip install onnxruntime-gpu`
- Use smaller images for testing

### "Holes in extraction"
- Enable Hybrid Validator
- Increase Tolerance value
- Use Restore brush to fix manually

## 📄 License

MIT License - Free for commercial and personal use.

## 👤 Author

**raven2cz**

## 🙏 Acknowledgments

- [rembg](https://github.com/danielgatis/rembg) - AI background removal
- [BiRefNet](https://github.com/ZhengPeng7/BiRefNet) - Bilateral Reference Network
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework

---

**Bust Extractor Pro v2.0** - Professional character portrait extraction for game developers, animators, and digital artists. 🎨
