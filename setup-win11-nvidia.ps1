# Run example:
#   .\setup-win11-nvidia.ps1
# or choose a different PyTorch CUDA wheel index:
#   .\setup-win11-nvidia.ps1 -TorchIndexUrl "https://download.pytorch.org/whl/cu121"

param(
  [string]$VenvDir = ".venv",
  [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu121",
  [switch]$InstallCudaToolkit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Has-Command([string]$Name) {
  return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Has-Command "python")) {
  throw "Python not found in PATH. Install Python 3.10+ and reopen PowerShell."
}

# 1) VC++ runtime (needed by ONNX Runtime on Windows)
if (Has-Command "winget") {
  winget install -e --id Microsoft.VCRedist.2015+.x64 --accept-package-agreements --accept-source-agreements | Out-Host
} else {
  Write-Warning "winget not found. Install VC++ runtime manually: Microsoft.VCRedist.2015+.x64"
}

# 2) Optional: system-wide CUDA Toolkit
if ($InstallCudaToolkit) {
  if (Has-Command "winget") {
    winget install -e --id Nvidia.CUDA --accept-package-agreements --accept-source-agreements | Out-Host
  } else {
    Write-Warning "winget not found. Install CUDA Toolkit manually."
  }
}

# 3) Create venv
if (-not (Test-Path $VenvDir)) {
  python -m venv $VenvDir
}

# 4) Activate venv
$activate = Join-Path $VenvDir "Scripts\Activate.ps1"
& $activate

# 5) Upgrade pip tooling
python -m pip install --upgrade pip setuptools wheel

# 6) Make sure CPU onnxruntime isn't installed (can cause confusion)
python -m pip uninstall -y onnxruntime | Out-Null

# 7) Install CUDA-enabled PyTorch (provides CUDA/cuDNN DLLs inside the env)
python -m pip install --upgrade torch torchvision --index-url $TorchIndexUrl

# 8) Install project requirements
python -m pip install -r requirements.txt

# 9) Quick verification
python -c "import onnxruntime as ort; print('ORT:', ort.__version__); print('ORT providers:', ort.get_available_providers())"
python -c "import torch; print('Torch:', torch.__version__); print('Torch CUDA:', torch.version.cuda); print('torch.cuda.is_available():', torch.cuda.is_available())"
Write-Host "Done. If ORT providers does NOT contain CUDAExecutionProvider, paste the two lines above here."
