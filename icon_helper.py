import win32ui
import win32gui
import win32con
import win32api
from PIL import Image
import os

# Cache to store icons we've already found
_ICON_CACHE = {}
_PATH_CACHE = {}

def get_app_icon(app_name, size=32):
    """
    Extract icon from application executable (with caching)
    
    :param app_name: Application name (e.g., 'chrome.exe')
    :param size: Icon size in pixels
    :return: PIL Image or None
    """
    # Check cache first
    cache_key = f"{app_name}_{size}"
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]
    
    try:
        # Check if we've already found the path
        if app_name not in _PATH_CACHE:
            exe_path = find_executable_path(app_name)
            _PATH_CACHE[app_name] = exe_path
        else:
            exe_path = _PATH_CACHE[app_name]
        
        if not exe_path:
            icon = get_default_icon(size)
            _ICON_CACHE[cache_key] = icon
            return icon
        
        # Extract icon
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)
        
        large, small = win32gui.ExtractIconEx(exe_path, 0)
        
        if not large:
            icon = get_default_icon(size)
            _ICON_CACHE[cache_key] = icon
            return icon
        
        hicon = large[0]
        
        # Convert to bitmap
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
        hdc = hdc.CreateCompatibleDC()
        
        hdc.SelectObject(hbmp)
        hdc.DrawIcon((0, 0), hicon)
        
        # Convert to PIL Image
        bmpstr = hbmp.GetBitmapBits(True)
        img = Image.frombuffer(
            'RGB',
            (ico_x, ico_y),
            bmpstr, 'raw', 'BGRX', 0, 1
        )
        
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Cleanup
        win32gui.DestroyIcon(hicon)
        
        # Cache it
        _ICON_CACHE[cache_key] = img
        
        return img
        
    except Exception as e:
        print(f"Error extracting icon for {app_name}: {e}")
        icon = get_default_icon(size)
        _ICON_CACHE[cache_key] = icon
        return icon


def find_executable_path(app_name):
    """
    Find executable path (optimized with common locations first)
    
    :param app_name: Application name
    :return: Full path or None
    """
    # Common application paths (check these first - much faster!)
    common_paths = {
        'chrome.exe': r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        'Code.exe': r"C:\Program Files\Microsoft VS Code\Code.exe",
        'WindowsTerminal.exe': r"C:\Program Files\WindowsApps\Microsoft.WindowsTerminal_*\WindowsTerminal.exe",
        'Photoshop.exe': r"C:\Program Files\Adobe\Adobe Photoshop*\Photoshop.exe",
        'firefox.exe': r"C:\Program Files\Mozilla Firefox\firefox.exe",
        'Discord.exe': os.path.expanduser(r"~\AppData\Local\Discord\app-*\Discord.exe"),
    }
    
    # Check common path first
    if app_name in common_paths:
        import glob
        matches = glob.glob(common_paths[app_name])
        if matches:
            return matches[0]
    
    # Fall back to searching
    search_paths = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"C:\Windows\System32",
        os.path.expanduser("~\\AppData\\Local"),
    ]
    
    for base_path in search_paths:
        for root, dirs, files in os.walk(base_path):
            if app_name in files:
                return os.path.join(root, app_name)
            
            # Don't search too deep
            if root.count(os.sep) - base_path.count(os.sep) > 3:
                del dirs[:]
    
    return None


def get_default_icon(size=32, color='#808080'):
    """
    Create a default icon when app icon can't be found
    
    :param size: Icon size
    :return: PIL Image
    """
    from PIL import ImageDraw

    # Convert hex to RGB tuple
    color = color.lstrip('#')
    r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))

    # Create icon w/ theme colour
    img = Image.new('RGBA', (size, size), (r, g, b, 2555))
    draw = ImageDraw.Draw(img)
    
    margin = size // 4

    # Lighter fill colour (add 40 to each RGB component, max 255)
    fill_r = min(r + 40, 255)
    fill_g = min(g + 40, 255)
    fill_b = min(b + 40, 255)
    
    # Darker outline colour (subtract 20 from each RGB component, min 0)
    outline_r = max(r - 20, 0)
    outline_g = max(g - 20, 0)
    outline_b = max(b - 20, 0)

    draw.rectangle(
        [margin, margin, size - margin, size - margin],
        fill=(255, 255, 255, 200),
        outline=(139, 90, 125, 255),
        width=2
    )
    
    return img