import copy
import random
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, Locator, Page
import multiprocessing as mp
import time
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PWTimeoutError

# CONFIG (yalnız Chromium)
# =======================
STEALTH_WEBRTC_RELAY_ONLY = r"""
(() => {
  if (window.__rtc_patched__) return; window.__rtc_patched__ = true;
  const NativePC = window.RTCPeerConnection || window.webkitRTCPeerConnection;
  if (!NativePC) return;

  function forceRelay(cfg){
    cfg = cfg || {};
    const merged = Object.assign({}, cfg, { iceTransportPolicy: 'relay' });
    if (!merged.iceServers) merged.iceServers = []; // TURN sunucun yoksa boş
    return merged;
  }

  const RTC = function(config, constraints){
    return new NativePC(forceRelay(config), constraints);
  };
  RTC.prototype = NativePC.prototype;

  function isRelay(cand) {
    return typeof cand?.candidate === "string" && /\styp\srelay(\s|$)/.test(cand.candidate);
  }

  const _addIceCandidate = NativePC.prototype.addIceCandidate;
  RTC.prototype.addIceCandidate = function(candidate){
    try {
      if (candidate && candidate.candidate && !isRelay(candidate)) {
        return Promise.resolve();
      }
    } catch(e){}
    return _addIceCandidate.apply(this, arguments);
  };

  window.RTCPeerConnection = RTC;
  window.webkitRTCPeerConnection = RTC;
})();
"""
USER_AGENTS_LINUX = [
    # Chrome (Ubuntu / Debian tabanlı Linux’lar)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.6778.108 Safari/537.36",

    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.6723.92 Safari/537.36",

    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.6668.59 Safari/537.36",

    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.6613.84 Safari/537.36",

    # Firefox
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:131.0) "
    "Gecko/20100101 Firefox/131.0",

    "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) "
    "Gecko/20100101 Firefox/130.0",

    "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) "
    "Gecko/20100101 Firefox/129.0",

    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
    "Gecko/20100101 Firefox/128.0",

    # Opera (Chromium tabanlı)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.6778.108 Safari/537.36 "
    "OPR/116.0.5366.95",

    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.6668.59 Safari/537.36 "
    "OPR/114.0.5295.70",

    # Edge (Chromium tabanlı)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.6778.108 Safari/537.36 "
    "Edg/131.0.2903.51",

    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.6668.59 Safari/537.36 "
    "Edg/129.0.2792.65",
]
CONFIG = {
    "ENGINE": "chromium",             # sadece chromium
    "ENABLE_PROXY": False,
    "PROXY": "http://user:pass@host:port",
    "ENABLE_STATUS_BADGE": True,  # sağ alt köşede küçük bir bilgi kutusu göster

    # UA override kullanmıyoruz (doğal kalsın)
    "ENABLE_USER_AGENT": True,
    "USER_AGENT": random.choice(USER_AGENTS_LINUX),

    # Dil / Bölge
    "ENABLE_LOCALE": True,
    "LOCALE": "tr-TR",

    # Saat dilimi
    "ENABLE_TIMEZONE": True,
    "TIMEZONE": "Europe/Istanbul",

    # Gelişmiş Gizlilik Özellikleri (Resimden)
    "ENABLE_DNT": True,                # Do Not Track
    "ENABLE_WEBRTC_HARDEN": True,
    "ENABLE_GUM_DENY": True,          # Media Access Block
    "ENABLE_WEBGL_SPOOF": True,       # WebGL Data Spoofing
    "ENABLE_CANVAS_SPOOF": True,      # Canvas Fingerprinting Protection
    "ENABLE_AUDIO_SPOOF": True,       # Audio Context Spoofing
    "ENABLE_FONT_SPOOF": True,        # Font Detection Protection
    "ENABLE_BATTERY_SPOOF": True,     # Battery API Spoofing
    "ENABLE_TOUCH_SPOOF": True,       # Touch Support Spoofing
    "ENABLE_PLATFORM_SPOOF": True,    # Platform ID Spoofing
    "ENABLE_SCREEN_SPOOF": True,      # Screen Properties Spoofing
    "PLATFORM": "Linux x86_64",       # Platform override
    
    # Ekstra güvenlikler
    "ENABLE_WEBGL_JITTER": True,

    # Kalıcı profil
    "PERSISTENT_RANDOM_PROFILE": True,
    "DELETE_PROFILE_ON_EXIT": True,

    # Başlangıç URL'leri
    "START_URLS": ["https://browserleaks.com/canvas"],

    # --- EKRAN / ÇÖZÜNÜRLÜK ---
    # Tipik bir 1920x1080 100% ölçek (DPR=1) masaüstü
    "SCREEN_WIDTH": 1920,
    "SCREEN_HEIGHT": 1080,
    "DEVICE_SCALE_FACTOR": 0.75,      # 1.25/1.5 gibi yaparsan "Display scaling" hissi verir

    # GPU bilgisi loglansın mı?
    "LOG_GPU_INFO": True,
    "EXTENSIONS": [
        r"browserFingerPrintSpoofing",     # manifest.json burada
    ]
}
PDP_RX = re.compile(r"/[-\w]+-p-\d+")
PDP_SIGNALS = [
    '[data-testid="add-to-basket-button"]',
    'h1[data-testid="product-title"]',
    'button:has-text("Sepete Ekle")',
    'button:has-text("Sepete ekle")',
    "[data-testid*='gallery'] img:visible",
]
BROKEN_STUB = r"""
(() => {
  // "yok" gibi göstermek için getter ile gölgeleyip undefined döndür.
  const undef = (obj, prop) => {
    try {
      Object.defineProperty(obj, prop, {
        get() { return undefined; },
        set(_) {},
        configurable: true
      });
      try { delete obj[prop]; } catch(e) {}
    } catch(e) {}
  };

  // RTCPeerConnection ve varyantları
  undef(window, 'RTCPeerConnection');
  undef(window, 'webkitRTCPeerConnection');

  // Bazı ortamlarda global semboller
  undef(window, 'RTCDataChannel');
  undef(window, 'RTCIceCandidate');
  undef(window, 'RTCSessionDescription');
})();
"""
BTN_SEL = ".onboarding__default-renderer .onboarding__default-renderer-primary-button"
OVL_SEL = ".onboarding-tour__overlay"



# -----------------------
# Init JS (opsiyonel, şu an boş tutuyoruz)
# -----------------------
def build_init_js(cfg: dict) -> str:
    """
    cfg anahtarları (bool):
      ENABLE_DNT, ENABLE_GUM_DENY, ENABLE_STATUS_BADGE,
      ENABLE_WEBGL_SPOOF, ENABLE_CANVAS_SPOOF, ENABLE_AUDIO_SPOOF,
      ENABLE_FONT_SPOOF, ENABLE_BATTERY_SPOOF, ENABLE_TOUCH_SPOOF,
      ENABLE_PLATFORM_SPOOF, ENABLE_SCREEN_SPOOF
    """
    parts = []

    # ortak yardımcılar ve random fonksiyonlar
    parts.append(r"""
    (() => {
      if (window.__init_patched__) return;
      window.__init_patched__ = true;

      const define = Object.defineProperty;
      const toStr = Function.prototype.toString;

      function safeDefine(obj, prop, getter) {
        try { define(obj, prop, { get: getter, configurable: true }); } catch(e){}
      }

      // maskFunction: sarmalanmış fonksiyonun name/length'ini bozma
      function maskFunction(wrapped, original) {
        try {
          define(wrapped, "name",   { value: original.name,   configurable: true });
          define(wrapped, "length", { value: original.length, configurable: true });
          define(wrapped, "toString", { value: toStr.bind(original) });
        } catch(e){}
      }
      
      // Random değer üreticileri
      function getRandomInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
      }
      
      function getRandomFloat(min, max, decimals = 2) {
        return parseFloat((Math.random() * (max - min) + min).toFixed(decimals));
      }
    """.strip())

    if cfg.get("ENABLE_DNT"):
        parts.append(r"""
        try {
          safeDefine(navigator, 'doNotTrack', ()=>'1');
          if (window.doNotTrack === undefined) {
            safeDefine(window, 'doNotTrack', ()=> '1');
          }
        } catch(e) {}
        """)

    if cfg.get("ENABLE_GUM_DENY"):
        parts.append(r"""
        try {
          const md = navigator.mediaDevices;
          if (md && md.getUserMedia) {
            const _gum = md.getUserMedia.bind(md);
            md.getUserMedia = () => Promise.reject(new DOMException('Permission denied', 'NotAllowedError'));
            maskFunction(md.getUserMedia, _gum);
          }
          if (md && md.getDisplayMedia) {
            const _gdm = md.getDisplayMedia.bind(md);
            md.getDisplayMedia = () => Promise.reject(new DOMException('Permission denied', 'NotAllowedError'));
            maskFunction(md.getDisplayMedia, _gdm);
          }
        } catch(e) {}
        """)
        
    # Advanced Fingerprinting Protection
    if cfg.get("ENABLE_WEBGL_SPOOF"):
        parts.append(r"""
        // WebGL Spoofing
        try {
          const getContext = HTMLCanvasElement.prototype.getContext;
          HTMLCanvasElement.prototype.getContext = function(type, ...args) {
            const ctx = getContext.apply(this, [type, ...args]);
            if (type === 'webgl' || type === 'experimental-webgl' || type === 'webgl2') {
              const getParameter = ctx.getParameter;
              ctx.getParameter = function(parameter) {
                if (parameter === ctx.VENDOR) return 'Intel Inc.';
                if (parameter === ctx.RENDERER) return 'Intel(R) HD Graphics 630';
                if (parameter === ctx.VERSION) return 'WebGL 1.0 (OpenGL ES 2.0 Chromium)';
                if (parameter === ctx.SHADING_LANGUAGE_VERSION) return 'WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)';
                return getParameter.apply(this, arguments);
              };
              maskFunction(ctx.getParameter, getParameter);
            }
            return ctx;
          };
          maskFunction(HTMLCanvasElement.prototype.getContext, getContext);
        } catch(e) {}
        """)
        
    if cfg.get("ENABLE_CANVAS_SPOOF"):
        parts.append(r"""
        // Canvas Fingerprinting Protection
        try {
          const toDataURL = HTMLCanvasElement.prototype.toDataURL;
          const getImageData = CanvasRenderingContext2D.prototype.getImageData;
          
          HTMLCanvasElement.prototype.toDataURL = function(...args) {
            const originalData = toDataURL.apply(this, args);
            return originalData;
          };
          maskFunction(HTMLCanvasElement.prototype.toDataURL, toDataURL);
          
          CanvasRenderingContext2D.prototype.getImageData = function(...args) {
            const imageData = getImageData.apply(this, args);
            for (let i = 0; i < imageData.data.length; i += 4) {
              if (Math.random() < 0.001) {
                imageData.data[i] = Math.min(255, imageData.data[i] + getRandomInt(-2, 2));
              }
            }
            return imageData;
          };
          maskFunction(CanvasRenderingContext2D.prototype.getImageData, getImageData);
        } catch(e) {}
        """)
        
    if cfg.get("ENABLE_AUDIO_SPOOF"):
        parts.append(r"""
        // Audio Context Spoofing
        try {
          const AudioContext = window.AudioContext || window.webkitAudioContext;
          if (AudioContext) {
            const createAnalyser = AudioContext.prototype.createAnalyser;
            AudioContext.prototype.createAnalyser = function() {
              const analyser = createAnalyser.apply(this, arguments);
              const getFloatFrequencyData = analyser.getFloatFrequencyData;
              analyser.getFloatFrequencyData = function(array) {
                getFloatFrequencyData.apply(this, arguments);
                for (let i = 0; i < array.length; i++) {
                  array[i] += getRandomFloat(-0.001, 0.001, 6);
                }
              };
              maskFunction(analyser.getFloatFrequencyData, getFloatFrequencyData);
              return analyser;
            };
            maskFunction(AudioContext.prototype.createAnalyser, createAnalyser);
          }
        } catch(e) {}
        """)
        
    if cfg.get("ENABLE_FONT_SPOOF"):
        parts.append(r"""
        // Font Detection Protection
        try {
          const measureText = CanvasRenderingContext2D.prototype.measureText;
          CanvasRenderingContext2D.prototype.measureText = function(text) {
            const metrics = measureText.apply(this, arguments);
            const noise = getRandomFloat(-0.1, 0.1, 3);
            Object.defineProperty(metrics, 'width', {
              value: metrics.width + noise,
              writable: false
            });
            return metrics;
          };
          maskFunction(CanvasRenderingContext2D.prototype.measureText, measureText);
        } catch(e) {}
        """)
        
    if cfg.get("ENABLE_BATTERY_SPOOF"):
        parts.append(r"""
        // Battery API Spoofing
        try {
          if (navigator.getBattery) {
            const getBattery = navigator.getBattery;
            navigator.getBattery = function() {
              return Promise.resolve({
                charging: true,
                chargingTime: Infinity,
                dischargingTime: Infinity,
                level: getRandomFloat(0.1, 1.0, 2),
                addEventListener: () => {},
                removeEventListener: () => {}
              });
            };
            maskFunction(navigator.getBattery, getBattery);
          }
        } catch(e) {}
        """)
        
    if cfg.get("ENABLE_TOUCH_SPOOF"):
        parts.append(r"""
        // Touch Support Spoofing
        try {
          safeDefine(navigator, 'maxTouchPoints', () => 0);
          safeDefine(navigator, 'msMaxTouchPoints', () => 0);
          delete window.TouchEvent;
          delete window.ontouchstart;
        } catch(e) {}
        """)
        
    if cfg.get("ENABLE_PLATFORM_SPOOF"):
        platform = cfg.get("PLATFORM", "Linux x86_64")
        parts.append(f"""
        // Platform Spoofing
        try {{
          safeDefine(navigator, 'platform', () => '{platform}');
          safeDefine(navigator, 'oscpu', () => '{platform}');
        }} catch(e) {{}}
        """)
    
    if cfg.get("ENABLE_SCREEN_SPOOF"):
        parts.append(r"""
        // Screen Properties Spoofing
        try {
          const screenProps = {
            width: 1920,
            height: 1080,
            availWidth: 1920,
            availHeight: 1040,
            colorDepth: 24,
            pixelDepth: 24
          };
          
          Object.keys(screenProps).forEach(prop => {
            safeDefine(screen, prop, () => screenProps[prop]);
          });
        } catch(e) {}
        """)

    if cfg.get("ENABLE_STATUS_BADGE"):
        status_lines = [
            f"UA: {'custom' if cfg.get('ENABLE_USER_AGENT') else 'default'}",
            f"TZ: {cfg.get('TIMEZONE') or '(default)'}",
            f"Locale: {cfg.get('LOCALE') or '(default)'}",
            f"DNT: {'on' if cfg.get('ENABLE_DNT') else 'off'}",
            f"WebGL: {'spoofed' if cfg.get('ENABLE_WEBGL_SPOOF') else 'default'}",
            f"Canvas: {'spoofed' if cfg.get('ENABLE_CANVAS_SPOOF') else 'default'}",
            f"Audio: {'spoofed' if cfg.get('ENABLE_AUDIO_SPOOF') else 'default'}",
            f"Font: {'spoofed' if cfg.get('ENABLE_FONT_SPOOF') else 'default'}",
            f"Battery: {'spoofed' if cfg.get('ENABLE_BATTERY_SPOOF') else 'default'}",
            f"Touch: {'spoofed' if cfg.get('ENABLE_TOUCH_SPOOF') else 'default'}",
            f"Platform: {'spoofed' if cfg.get('ENABLE_PLATFORM_SPOOF') else 'default'}",
        ]
        status_txt_literal = repr("\n".join(status_lines))
        parts.append(fr"""
        try {{
          const txt = {status_txt_literal};
          const d = document.createElement('div');
          d.style.cssText='position:fixed;right:12px;bottom:12px;z-index:2147483647;background:#111;color:#fff;padding:10px 12px;border-radius:10px;font:12px/1.45 system-ui,Arial;opacity:.9;white-space:pre-wrap;box-shadow:0 4px 14px rgba(0,0,0,.25)';
          d.textContent = txt;
          document.documentElement.appendChild(d);
        }} catch(e){{}}
        """)

    # IIFE kapanışı
    parts.append("})();")

    return "\n".join(parts)
# -----------------------
# Yardımcılar
# -----------------------
def _sanity_check(page):
    """Basit görünürlük: webdriver ve canvas export"""
    return page.evaluate("""() => {
      const out = {};
      try { out.webdriver = navigator.webdriver; } catch(e){ out.webdriver = 'err'; }
      try {
        const c = document.createElement('canvas');
        const ctx = c.getContext('2d');
        out.canvas_ok = !!(c && ctx && typeof c.toDataURL === 'function');
        let exp = false;
        try { c.toDataURL(); exp = true; } catch(e){}
        out.canvas_export = exp;
      } catch(e){ out.canvas_ok = false; out.canvas_export = false; }
      return out;
    }""")
def _collect_gpu_info(page):
    """WebGL üzerinden GPU bilgilerini OKUR (değiştirmez)."""
    return page.evaluate(r"""
      () => {
        const res = { ok: false };
        try {
          const c = document.createElement('canvas');
          const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
          if (!gl) { res.ok = false; res.reason = "no-webgl"; return res; }

          const dbg = gl.getExtension('WEBGL_debug_renderer_info');
          const VENDOR = gl.VENDOR, RENDERER = gl.RENDERER, VERSION = gl.VERSION, SHADING = gl.SHADING_LANGUAGE_VERSION;

          res.ok = true;
          res.webgl = {
            vendor: gl.getParameter(VENDOR),
            renderer: gl.getParameter(RENDERER),
            version: gl.getParameter(VERSION),
            shading: gl.getParameter(SHADING),
          };
          if (dbg) {
            res.debug = {
              unmaskedVendor: gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL),
              unmaskedRenderer: gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL),
            };
          } else {
            res.debug = { unmaskedVendor: null, unmaskedRenderer: null };
          }
        } catch (e) {
          res.ok = False;
          res.error = String(e);
        }
        return res;
      }
    """)
def _open_chromium_context(pw, cfg, context_kwargs):
    launch_args = []
    w = int(cfg["SCREEN_WIDTH"]); h = int(cfg["SCREEN_HEIGHT"])
    launch_args += [f"--window-size={w},{h}"]

    ext_paths = [str(Path(p).resolve()) for p in cfg.get("EXTENSIONS", []) if p]
    if ext_paths:
        ext_arg = ",".join(ext_paths)
        launch_args += [
            f"--disable-extensions-except={ext_arg}",
            f"--load-extension={ext_arg}",
        ]

    if cfg.get("PERSISTENT_RANDOM_PROFILE", True):
        user_dir = Path(tempfile.mkdtemp(prefix="pw_profile_chromium_")) / uuid.uuid4().hex[:8]
        user_dir.mkdir(parents=True, exist_ok=True)
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(user_dir),
            headless=False,
            args=launch_args,
            viewport={"width": w, "height": h},
            screen={"width": w, "height": h},
            **context_kwargs,
        )
        # >>> ÖNEMLİ: persistent dalına da init script ekle
        ctx.add_init_script(BROKEN_STUB)
        return ctx.browser, ctx, user_dir
    else:
        br = pw.chromium.launch(headless=False, args=launch_args)
        ctx = br.new_context(
            viewport={"width": w, "height": h},
            screen={"width": w, "height": h},
            device_scale_factor=cfg["DEVICE_SCALE_FACTOR"],
            **context_kwargs,
        )
        ctx.add_init_script(BROKEN_STUB)
        return br, ctx, None
# -----------------------
# init
# -----------------------
def close_trendyol_popup_with_kadin(page: Page,timeout=30000):
    modal = page.locator(".gender-modal-section").first

    # Modal zaten yoksa başarılı say
    if not modal.count():
        return True

    # Ana ve alternatif hedefler
    targets = [
        modal.locator(".modal-action-button", has_text="Kadın").first,
        page.locator('.gender-card:has-text("Kadın") .modal-action-button').first,
        page.locator(
            'xpath=//div[contains(@class,"gender-modal-section")]//div[contains(@class,"modal-action-button")][normalize-space()="Kadın"]').first,
        page.get_by_text("Kadın", exact=True).first,  # son çare, eşsizse
    ]

    # Tıklama denemeleri: normal -> dispatch_event -> force
    clicked = False
    for t in targets:
        if not t.count():
            continue
        for attempt in (
                lambda: t.click(timeout=1200),
                lambda: t.dispatch_event("click"),
                lambda: t.click(force=True, timeout=1200),
        ):
            try:
                attempt()
                clicked = True
                break
            except Exception:
                continue
        if clicked:
            break

    # Post-condition: modal kapanmış mı?
    try:
        modal.wait_for(state="hidden", timeout=timeout)
        return True
    except TimeoutError:
        pass
    if not modal.count():  # detach olduysa
        return True

    # Buraya geldiysek kapanmadı → başarısız
    return False
def human_scroll_until(page: Page, selector: str, timeout: float = 180):
    """
    Küçük adımlarla aşağı kaydırır; hedef selector gerçekten viewport'a girene kadar bekler.
    Bulunamazsa TimeoutError fırlatır.
    """
    start = time.time()
    target = page.locator(selector).first
    
    # İlk önce sayfanın tamamen yüklendiğinden emin ol
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except:
        pass

    # Önce sayfada herhangi bir ürün var mı kontrol et
    product_selectors = [
        "[data-testid='product-card'] a",
        ".p-card-wrppr a", 
        ".product-item a",
        "a[href*='-p-']",
        "[class*='product'] a"
    ]
    
    products_found = False
    for sel in product_selectors:
        if page.locator(sel).count() > 0:
            products_found = True
            break
    
    if not products_found:
        raise TimeoutError(f"Sayfada hiçbir ürün bulunamadı")

    scroll_attempts = 0
    max_scroll_attempts = 15  # Daha fazla deneme
    continuous_scroll_count = 0
    max_continuous_scrolls = 300  # Çok daha fazla scroll (300 kez)
    
    print(f"[+] Hedef ürün aranıyor: {selector}")
    
    while time.time() - start < timeout and continuous_scroll_count < max_continuous_scrolls:
        # Hedef selector'ü kontrol et
        if target.count() > 0 and _is_in_viewport(page, selector):
            target.scroll_into_view_if_needed()
            print(f"[+] Hedef ürün bulundu! ({continuous_scroll_count} scroll ile)")
            return

        # Sayfa sonuna gelip gelmediğimizi kontrol et
        current_scroll = page.evaluate("() => window.scrollY")
        max_scroll = page.evaluate("() => document.body.scrollHeight - window.innerHeight")
        
        if current_scroll >= max_scroll:
            scroll_attempts += 1
            print(f"[!] Sayfa sonu gelindi ({scroll_attempts}/{max_scroll_attempts}), baştan aranıyor...")
            
            if scroll_attempts >= max_scroll_attempts:
                print(f"[!] {max_scroll_attempts} kez sayfa sonu gelindi")
                print(f"[+] Daha yoğun scroll ile tekrar denenecek...")
                scroll_attempts = 0  # Sıfırla ve devam et
            
            # Başa dön ve devam et
            page.evaluate("() => window.scrollTo(0, 0)")
            time.sleep(2)
            continue
            
        # Sürekli scroll yap - daha küçük adımlarla
        step = random.randint(200, 600)  # Daha küçük adımlar
        page.mouse.wheel(0, step)
        continuous_scroll_count += 1
        
        # Progress göster
        if continuous_scroll_count % 20 == 0:
            print(f"    → {continuous_scroll_count} scroll yapıldı, aranıyor...")

        # Daha hızlı scroll - İnsan gibi ama daha hızlı
        time.sleep(random.uniform(0.1, 0.4))  # Daha kısa bekleme
        if random.random() < 0.05:  # Daha az uzun bekleme
            time.sleep(random.uniform(0.5, 1.0))

    raise TimeoutError(f"{selector} gorunur viewport'a girmedi (timeout={timeout}s, {continuous_scroll_count} scroll)")
def human_swipe_gallery(page: Page, gallery_selector: str):
    """
    Bir galeriyi 1–5 kez rastgele insan gibi kaydırır.
    gallery_selector: galeri içindeki sağ ok butonunun locator'u
    """
    # kaç kere kaydırılacağı
    steps = random.randint(1, 5)
    print(f"[+] {steps} kere kaydırılacak")

    for _ in range(steps):
        # sağ ok butonuna tıkla
        page.locator(gallery_selector).last.click()

        # arada kısa doğal bekleme
        time.sleep(random.uniform(0.5, 1.8))
def human_write(locator: Locator, text: str):
    """Bir input locator'ına metni insan gibi yazar."""
    locator.click()
    time.sleep(random.uniform(0.2, 0.6))  # yazmaya başlamadan küçük bekleme

    for ch in text:
        # Karakter arası bekleme
        time.sleep(random.uniform(0.05, 0.18))

        # %5 ihtimalle yanlış basıp düzeltme simülasyonu
        if random.random() < 0.05:
            locator.type(ch + ch, delay=0)       # iki kere bas
            time.sleep(random.uniform(0.05, 0.15))
            locator.press("Backspace")           # düzelt
        else:
            locator.type(ch, delay=0)

        # %10 ihtimalle düşünür gibi biraz uzun bekleme
        if random.random() < 0.1:
            time.sleep(random.uniform(0.3, 0.8))

    time.sleep(random.uniform(0.1, 0.3))  # yazdıktan sonra minik duraklama
def _is_in_viewport(page: Page, selector: str) -> bool:
    loc = page.locator(selector).first
    box = loc.bounding_box()
    if not box:
        return False
    vp = page.viewport_size or {}
    # Viewport yüksekliğini JS'ten kesin al (özellikle responsive modda)
    inner_h = page.evaluate("() => window.innerHeight") or vp.get("height", 0)
    # Ekranla kesişiyor mu?
    return (box["y"] < inner_h) and (box["y"] + box["height"] > 0)

def accept_cookies_if_any(page: Page):
    # Trendyol cookie butonları değişebiliyor; yaygın metinler:
    CANDIDATES = ["Kabul Et", "Tümünü Kabul Et", "Kapat", "Anladım"]
    for txt in CANDIDATES:
        try:
            page.get_by_role("button", name=re.compile(fr"^{txt}$", re.I)).first.click(timeout=1000)
            print(f"[+] Cookie: '{txt}' tıklandı.")
            break
        except Exception:
            continue
def _wait_pdp_signals(p, timeout=30000):
    last = None
    per = max(3000, timeout // max(1, len(PDP_SIGNALS)))
    for sel in PDP_SIGNALS:
        try:
            p.locator(sel).first.wait_for(state="visible", timeout=per)
            return
        except PWTimeoutError as e:
            last = e
    if last:
        raise last
def click_to_pdp(page, product_span_sel: str, timeout=30000):
    """
    Ürün başlığı/ismi görünen öğeden PDP'e gider.
    Yeni sekme mi aynı sekme mi, otomatik karar verir.
    """
    # 0) Elemanı bul, görünen yap
    loc = page.locator(product_span_sel).first
    try:
        loc.wait_for(state="visible", timeout=timeout)
    except Exception:
        # Eğer ilk locator bulunamazsa, genel ürün kartı selector'ını dene
        loc = page.locator("[data-testid='product-card'] a").first
        loc.wait_for(state="visible", timeout=timeout)

    # 1) En yakın <a> atasını hedef al
    link = loc.locator("xpath=ancestor-or-self::a[1]")
    if link.count() == 0:
        link = loc  # son çare: direkt span'a tıkla

    # target/href topla (hemen önce al, sonra tıklayacağız)
    target = (link.get_attribute("target") or "").lower()
    href = link.get_attribute("href") or ""

    # 2) Akışı seç ve tıkla
    if target == "_blank":
        # YENİ SEKME
        with page.context.expect_page(timeout=timeout) as pop:
            link.click(force=True, timeout=timeout)
        newp = pop.value
        newp.wait_for_load_state("domcontentloaded", timeout=timeout)
        try:
            _wait_pdp_signals(newp, timeout=timeout)
        except PWTimeoutError:
            # URL fallback
            try:
                newp.wait_for_function(
                    "() => /-p-\\d+/.test(location.pathname) || /product|p\\?/.test(location.href)",
                    timeout=8000
                )
            except PWTimeoutError:
                pass
            _wait_pdp_signals(newp, timeout=timeout)
        return newp
    else:
        # AYNI SEKME
        before = page.url
        # Not: SPA ise expect_navigation yakalanmayabilir → yine de dene
        try:
            with page.expect_navigation(timeout=timeout):
                link.click(force=True, timeout=timeout)
        except PWTimeoutError:
            # SPA olabilir; yine devam
            link.click(force=True, timeout=2000)  # tek tık kaçtıysa bir daha dene (idempotent link için)
        # DOM yüklensin
        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except PWTimeoutError:
            pass

        # PDP sinyali bekle
        try:
            _wait_pdp_signals(page, timeout=timeout)
        except PWTimeoutError:
            # URL fallback
            try:
                page.wait_for_function(
                    "() => /-p-\\d+/.test(location.pathname) || /product|p\\?/.test(location.href)",
                    timeout=8000
                )
            except PWTimeoutError:
                if page.url == before and not href:
                    raise RuntimeError("Tıklama PDP'e götürmedi; URL değişmedi ve sinyal yok.")
            _wait_pdp_signals(page, timeout=timeout)
        return page
def click_anladim_trusted(page: Page, timeout_ms: int = 8000) -> bool:
    # 1) Buton DOM'a gelsin
    try:
        page.wait_for_selector(BTN_SEL, state="attached", timeout=timeout_ms)
    except Exception:
        return False

    # 2) Overlay'i devre dışı bırak (tamamen görünmez ve tıklanamaz yap)
    try:
        page.evaluate(f"""
        () => {{
          document.querySelectorAll('{OVL_SEL}').forEach(ov => {{
            ov.style.setProperty('display','none','important');
            ov.style.setProperty('pointer-events','none','important');
            ov.style.setProperty('opacity','0','important');
          }});
        }}
        """)
    except Exception:
        pass

    btn = page.locator(BTN_SEL).first

    # 3) Görünecek hale getir
    try:
        btn.scroll_into_view_if_needed(timeout=1200)
    except Exception:
        pass
    page.wait_for_timeout(100)

    # 4) Basit tıklamalar
    try:
        btn.click(timeout=1200)
        return True
    except Exception:
        try:
            btn.click(timeout=1200, force=True) # hit-test atlatarak
            return True
        except Exception:
            pass

    # 5) Trusted mouse click: koordinatla tıkla (mousedown→mouseup→click zinciri)
    try:
        box = btn.bounding_box()
        if not box:
            # Bazen Playwright bbox vermez; JS ile al
            box = page.evaluate(f"""
            () => {{
              const el = document.querySelector("{BTN_SEL}");
              if (!el) return null;
              const r = el.getBoundingClientRect();
              return {{ x: r.left + r.width/2, y: r.top + r.height/2, width: r.width, height: r.height }};
            }}
            """)
        if box:
            # Sayfa scroll ofsetini ekle (mouse koordinatları viewport bazlıdır; Playwright bunu kendi halleder)
            x = box["x"] + (box.get("width", 0) or 0) / 2
            y = box["y"] + (box.get("height", 0) or 0) / 2
            page.mouse.move(x, y)
            page.wait_for_timeout(50)
            page.mouse.down()
            page.wait_for_timeout(30)
            page.mouse.up()
            return True
    except Exception:
        pass

    # 6) Son çare: JS MouseEvent (untrusted) – bazen yine işe yarar
    try:
        ok = page.evaluate(f"""
        () => {{
          const b = document.querySelector("{BTN_SEL}");
          if (!b) return false;
          const ev = new MouseEvent('click', {{ bubbles:true, cancelable:true, view:window }});
          return b.dispatchEvent(ev);
        }}
        """)
        if ok:
            return True
    except Exception:
        pass
    print("btn visible? :", page.locator(BTN_SEL).first.is_visible())
    print("overlay exists?:", page.evaluate(f"()=>!!document.querySelector('{OVL_SEL}')"))

    return False
def click_random_right_arrow(page, min_clicks=3, max_clicks=6):
    btn = page.locator("button._carouselNavigationButton_d6bc593 >> i.i-right-pointer")
    # üstteki locator sadece <i>’yi bulur, en yakın button’a çıkalım:
    btn = btn.locator("xpath=ancestor::button[1]")

    if not btn.is_visible():
        print("[!] Sağ ok butonu görünür değil")
        return

    n = random.randint(min_clicks, max_clicks)
    print(f"[+] Sağ oka {n} kez tıklanacak")

    for i in range(n):
        btn.click()
        print(f"    → {i+1}. tık")
        time.sleep(random.uniform(0.5, 1.5))  # insan gibi bekle
def human_scroll_down_and_up(page: Page, min_steps=3, max_steps=7):
    """
    İnsan gibi aşağı kaydırır, sonra en yukarı step-step çıkar.
    """
    steps = random.randint(min_steps, max_steps)
    print(f"[+] Aşağıya {steps} adım scroll yapılacak")

    # aşağı doğru kaydır
    for i in range(steps):
        step = random.randint(300, 800)  # küçük adımlar
        page.mouse.wheel(0, step)
        print(f"    → {i+1}. scroll: {step}px aşağı")
        time.sleep(random.uniform(0.3, 0.8))  # bekleme

    # aşağıda biraz takılsın
    time.sleep(random.uniform(1.0, 2.0))

    # toplam scroll yüksekliğini bul
    total_scroll = page.evaluate("() => window.scrollY")
    print(f"[+] Şu an aşağıda ~{total_scroll}px")

    # yukarı step-step çık
    while total_scroll > 0:
        step = random.randint(250, 600)  # yukarı kayma adımı
        total_scroll = max(0, total_scroll - step)
        page.mouse.wheel(0, -step)
        print(f"    ↑ {step}px yukarı")
        time.sleep(random.uniform(0.3, 0.7))

    print("[+] En yukarı çıkıldı")
    time.sleep(random.uniform(1.0, 2.0))
def click_add_to_cart(page: Page, timeout=8000):
    """
    'Sepete Ekle' butonuna insan gibi tıklar.
    """
    try:
        btn = page.locator("#pdp-page-layout").get_by_test_id("add-to-cart-button")
        btn.first.wait_for(state="visible", timeout=8000)

        time.sleep(random.uniform(0.8, 1.6))  # insan gibi gecikme
        btn.first.click()
        print("[+] PDP'deki 'Sepete Ekle' butonuna tıklandı")

        return True
    except Exception as e:
        print(f"[!] 'Sepete Ekle' butonu tıklanamadı: {e}")
        return False


def add_product_engagement_actions(pdp: Page):
    """
    Ürünü öne çıkarmak için ek etkileşim aksiyonları
    """
    try:
        print("[+] Ürün etkileşim aksiyonları başlatılıyor...")
        
        # 1. Ürün resimlerini detaylı incele
        try:
            product_images = pdp.locator("[data-testid*='gallery'] img, .product-image img").all()
            if product_images:
                for i, img in enumerate(product_images[:3]):  # ilk 3 resmi incele
                    try:
                        img.scroll_into_view_if_needed()
                        time.sleep(random.uniform(1.5, 3.0))
                        print(f"    → {i+1}. ürün resmi incelendi")
                    except:
                        pass
        except Exception as e:
            print(f"[!] Resim inceleme hatası: {e}")
            
        # 2. Ürün detaylarını oku
        try:
            details_sections = [
                "[data-testid='product-detail']",
                ".product-detail-section",
                ".product-description",
                "[class*='detail']"
            ]
            
            for selector in details_sections:
                detail_element = pdp.locator(selector).first
                if detail_element.count() > 0:
                    detail_element.scroll_into_view_if_needed()
                    time.sleep(random.uniform(2.0, 4.0))
                    print(f"    → Ürün detayları okundu")
                    break
        except Exception as e:
            print(f"[!] Detay okuma hatası: {e}")
            
        # 3. Yorumları kontrol et (varsa)
        try:
            reviews_selectors = [
                "[data-testid*='review']",
                ".reviews-section",
                "[class*='comment']",
                "[class*='review']"
            ]
            
            for selector in reviews_selectors:
                reviews = pdp.locator(selector).first
                if reviews.count() > 0:
                    reviews.scroll_into_view_if_needed()
                    time.sleep(random.uniform(2.5, 4.5))
                    print(f"    → Yorumlar bölümü kontrol edildi")
                    break
        except Exception as e:
            print(f"[!] Yorum kontrol hatası: {e}")
            
        # 4. Benzer ürünleri görüntüle (varsa)
        try:
            similar_products = pdp.locator("[class*='similar'], [class*='recommendation'], [data-testid*='recommendation']").first
            if similar_products.count() > 0:
                similar_products.scroll_into_view_if_needed()
                time.sleep(random.uniform(1.5, 3.0))
                print(f"    → Benzer ürünler görüntülendi")
        except Exception as e:
            print(f"[!] Benzer ürün hatası: {e}")
            
        # 5. Fiyat bölümünü incele
        try:
            price_selectors = [
                "[data-testid*='price']",
                ".price-section",
                "[class*='price']"
            ]
            
            for selector in price_selectors:
                price_element = pdp.locator(selector).first
                if price_element.count() > 0:
                    price_element.scroll_into_view_if_needed()
                    time.sleep(random.uniform(1.0, 2.0))
                    print(f"    → Fiyat bilgisi incelendi")
                    break
        except Exception as e:
            print(f"[!] Fiyat inceleme hatası: {e}")
            
        print("[+] Ürün etkileşim aksiyonları tamamlandı")
        
    except Exception as e:
        print(f"[!] Etkileşim aksiyonları hatası: {e}")

def simulate_user_interest(pdp: Page):
    """
    Kullanıcı ilgisini simüle eden davranışlar
    """
    try:
        print("[+] Kullanıcı ilgisi simülasyonu başlatılıyor...")
        
        # Sayfada biraz daha uzun kal
        extended_time = random.uniform(8.0, 15.0)
        print(f"    → Sayfada {extended_time:.1f} saniye kalınacak")
        
        # Bu süre boyunca küçük hareketler yap
        for i in range(int(extended_time // 3)):
            # Rastgele küçük scroll hareketleri
            scroll_amount = random.randint(50, 200)
            direction = random.choice([-1, 1])
            pdp.mouse.wheel(0, scroll_amount * direction)
            time.sleep(random.uniform(2.0, 4.0))
            
            # Ara sıra mouse hareket ettir
            if random.random() < 0.3:
                x = random.randint(200, 800)
                y = random.randint(200, 600)
                pdp.mouse.move(x, y)
                time.sleep(random.uniform(0.5, 1.0))
                
        print("[+] Kullanıcı ilgisi simülasyonu tamamlandı")
        
    except Exception as e:
        print(f"[!] İlgi simülasyonu hatası: {e}")



basarili = 0
def trendyol_start(cfg, kw, target_product_id):
    extra_headers = {}
    context_kwargs = {"extra_http_headers": extra_headers or None}
    if cfg.get("ENABLE_LOCALE"):
        context_kwargs["locale"] = cfg.get("LOCALE")
        extra_headers["Accept-Language"] = cfg.get("LOCALE").replace('_','-') + ",en;q=0.8"
    if cfg.get("ENABLE_TIMEZONE"):
        context_kwargs["timezone_id"] = cfg.get("TIMEZONE")
    if cfg.get("ENABLE_PROXY"):
        context_kwargs["proxy"] = {"server": cfg.get("PROXY")}
    if cfg.get("ENABLE_USER_AGENT") and cfg.get("USER_AGENT"):
        context_kwargs["user_agent"] = cfg["USER_AGENT"]

    init_js = build_init_js(cfg)

    CYCLE_SLEEP = (6, 14)   # her turun arasına rastgele 6-14 sn
    RECREATE_EVERY = 2      # her 2 turda bir context/browser’ı tazele
    cycle = 0

    # Sayaçlar
    basarili = 0
    basarisiz = 0

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        while True:
            # --- context/browser aç ---
            browser, context, user_dir = _open_chromium_context(pw, cfg, context_kwargs=context_kwargs)

            # init script’ler
            NO_NEW_TABS = r"""(() => { const _open = window.open; window.open = function(url){ if(url){ location.href=url; return window;} return _open.apply(this, arguments); }; document.addEventListener('click', (e)=>{ const a = e.target && e.target.closest && e.target.closest('a[target="_blank"]'); if(a && a.href){ e.preventDefault(); e.stopPropagation(); try{a.removeAttribute('target');}catch(_){} location.href=a.href; } }, true); })();"""
            context.add_init_script(NO_NEW_TABS)
            context.add_init_script(init_js)
            context.add_init_script(STEALTH_WEBRTC_RELAY_ONLY)


            try:
                # --- döngü: context kapanana kadar N tur çalıştır ---
                for _ in range(RECREATE_EVERY):
                    cycle += 1
                    print(f"\n=== CYCLE {cycle} ===")

                    ok = False
                    try:
                        # Context'in hala açık olup olmadığını kontrol et
                        try:
                            # Context'e yeni sayfa açmaya çalışarak test et
                            test_page = context.new_page()
                            test_page.close()
                            check = run_scenario_trendyol(context, kw, target_product_id)
                            ok = bool(check)
                        except Exception as ctx_error:
                            if "closed" in str(ctx_error).lower():
                                print(f"[cycle {cycle}] Context bağlantısı kesilmiş: {ctx_error}")
                                break
                            else:
                                raise ctx_error
                    except Exception as e:
                        print(f"[cycle {cycle}] HATA: {e}")
                        # Eğer context kapatılmışsa döngüden çık
                        if "closed" in str(e).lower():
                            print(f"[cycle {cycle}] Context/Browser kapanmış, yeniden başlatılacak")
                            break

                    # Sonuçları say ve yazdır
                    if ok:
                        basarili += 1
                        durum = "BAŞARILI"
                    else:
                        basarisiz += 1
                        durum = "BAŞARISIZ"

                    toplam = basarili + basarisiz
                    print(f"[cycle {cycle}] durum: {durum}")
                    print(f"[cycle {cycle}] skor (başarılı/başarısız): {basarili}/{basarisiz}")
                    print(f"[cycle {cycle}] oran  (başarılı/toplam):   {basarili}/{toplam}")

                    # araya rastgele bekleme
                    sl = random.uniform(*CYCLE_SLEEP)
                    print(f"[cycle {cycle}] bekleme: {sl:.1f}s")
                    time.sleep(sl)
            finally:
                # context’i kapat ve (isteğe bağlı) profili sil
                try: context.close()
                except: pass
                try:
                    if browser: browser.close()
                except: pass
                if cfg.get("PERSISTENT_RANDOM_PROFILE", True) and cfg.get("DELETE_PROFILE_ON_EXIT") and user_dir:
                    try: shutil.rmtree(Path(user_dir).parent)
                    except: pass

def run_scenario_trendyol(context,kw,target_product_id):
    # her tur için yeni bir page aç
    p = context.new_page()
    # page zaten açılmış olmalı

    try:
        print(f"[+] Trendyol'a gidiliyor...")
        p.goto("https://trendyol.com/", timeout=30000)
        p.wait_for_load_state("domcontentloaded", timeout=30000)

        time.sleep(random.uniform(2, 4))
        
        print(f"[+] Popup kapatılıyor...")
        ok = close_trendyol_popup_with_kadin(p)
        if not ok:
            print("[!] Kadın popup'ı kapatılamadı, devam ediliyor...")
        
        time.sleep(random.uniform(1, 2))

        print(f"[+] Arama yapılıyor: '{kw}'")
        try:
            box = p.get_by_placeholder("Aradığınız ürün, kategori veya markayı yazınız")
            if not box.is_visible():
                # Alternatif arama kutusu
                box = p.locator("input[placeholder*='Aradığınız']").first
            human_write(box, kw)
            p.keyboard.press("Enter")
        except Exception as e:
            print(f"[!] Arama kutusu bulunamadı: {e}")
            return False
            
        time.sleep(random.uniform(5, 8))
        
        # Sayfa yüklenmesini bekle
        try:
            p.wait_for_load_state("networkidle", timeout=15000)
        except:
            p.wait_for_load_state("domcontentloaded", timeout=10000)
        
        print(f"[+] Sayfa ölçeklendiriliyor...")
        p.evaluate("""
                (() => {
                  const scale = 0.75;
                  const wrap = document.createElement('div');
                  // Body'deki tüm çocukları wrap içine taşı
                  while (document.body.firstChild) wrap.appendChild(document.body.firstChild);
                  document.body.appendChild(wrap);

                  // Ölçekle ve orijine sabitle
                  wrap.style.transform = `scale(${scale})`;
                  wrap.style.transformOrigin = '0 0';

                  // Kayma/scroll bozulmasın diye genişliği ölçeğe göre telafi et
                  wrap.style.width = `calc(100% / ${scale})`;
                  wrap.style.height = `calc(100% / ${scale})`;
                  wrap.style.boxSizing = 'border-box';
                })();
                """)
        # Hedef ürün bilgileri
        pdp = None
        product_found = False
        
        # Kullanıcının girdiği ürün ID'sini kullan
        print(f"[+] Hedef ürün ID'si aranıyor: {target_product_id}")
        
        try:
            print(f"[+] Hedef ürün ID'si aranıyor: {target_product_id} ")
            print(f"[+] Sürekli scroll ile ürün aranacak...")
            human_scroll_until(p, f'a[href*="{target_product_id}"]')
            pdp = click_to_pdp(p, f'a[href*="{target_product_id}"]')
            product_found = True
            print(f"[+] Hedef ürün bulundu ve PDP'ye gidildi: {target_product_id}")
        except TimeoutError:
            print(f"[!] Hedef ürün ID '{target_product_id}' bulunamadı")
            print(f"[!] Ürün bulunamadığı için işlem sonlandırılıyor")
            return False
        
        if not product_found or pdp is None:
            print("[!] Ürün bulunamadı veya PDP'ye gidilemedi")
            return False

        print(f"[+] Ürün detay sayfasında, işlemler başlıyor...")
        
        # Sayfa kapanıp kapanmadığını kontrol et
        try:
            pdp.url  # Sayfanın hala açık olup olmadığını test et
        except Exception:
            print("[!] PDP sayfası kapanmış, işlem iptal ediliyor")
            return False
            
        time.sleep(random.uniform(2, 4))
        
        print(f"[+] Popup'ı kapatılıyor...")
        try:
            ok = click_anladim_trusted(pdp)
            if ok:
                print("[+] Anladım popup'ı başarıyla kapatıldı")
            else:
                print("[!] Anladım popup'ı kapatılamadı, devam ediliyor...")
        except Exception as e:
            print(f"[!] Popup kapatma hatası: {e}")

        print(f"[+] Galeri geziliyor...")
        try:
            # Sayfa hala açık mı kontrol et
            if not pdp.is_closed():
                click_random_right_arrow(pdp)
            else:
                print("[!] Sayfa kapanmış, galeri gezilemedi")
                return False
        except Exception as e:
            print(f"[!] Galeri gezme hatası: {e}")
            
        time.sleep(random.uniform(1, 2))
        
        print(f"[+] Sayfa geziliyor...")
        try:
            # Sayfa hala açık mı kontrol et
            if not pdp.is_closed():
                human_scroll_down_and_up(pdp)
            else:
                print("[!] Sayfa kapanmış, scroll yapılamadı")
                return False
        except Exception as e:
            print(f"[!] Sayfa gezme hatası: {e}")
            
        time.sleep(random.uniform(1, 2))
        
        print(f"[+] Sepete ekleniyor...")
        try:
            # Sayfa hala açık mı kontrol et
            if not pdp.is_closed():
                # Önce detaylı ürün incelemesi yap
                add_product_engagement_actions(pdp)
                time.sleep(random.uniform(1, 2))
                
                # Kullanıcı ilgisini simüle et
                simulate_user_interest(pdp)
                time.sleep(random.uniform(1, 2))
                
                # Sepete ekle
                cart_success = click_add_to_cart(pdp)
                if cart_success:
                    print("[+] Ürün başarıyla sepete eklendi!")
                else:
                    print("[!] Sepete ekleme başarısız, ama devam ediliyor...")
            else:
                print("[!] Sayfa kapanmış, sepete eklenemedi")
                return False
        except Exception as e:
            print(f"[!] Sepete ekleme hatası: {e}")

        print("[+] İşlem tamam, 5 saniye bekleyip çıkılıyor...")
        time.sleep(5)
        return True
    finally:
        # RAM/handle sızıntısını önlemek için mutlaka kapat
        try: p.close()
        except: pass



def get_user_input():
    """Kullanıcıdan arama terimi ve ürün ID'sini alır"""
    print("\n=== TRENDYOl BOT ====")
    print("Bu bot Trendyol'da belirttiğiniz ürünü arayacak ve sepete ekleyecek.\n")
    
    # Arama terimi sor
    while True:
        search_term = input("Ne aramak istersiniz? (örnek: ayakkabı, şal, çanta): ").strip()
        if search_term:
            break
        print("[!] Lütfen geçerli bir arama terimi girin.")
    
    # Ürün ID'si sor
    while True:
        product_id = input("\nHedef ürün ID'sini girin (Trendyol URL'den): ").strip()
        if product_id and product_id.isdigit():
            break
        print("[!] Lütfen geçerli bir ürün ID'si girin (sadece rakamlar).")
    
    print(f"\n[+] Arama terimi: {search_term}")
    print(f"[+] Hedef ürün ID: {product_id}")
    print(f"[+] Bot başlatılıyor...\n")
    
    return search_term, product_id

if __name__ == "__main__":
    try:
        # Kullanıcıdan bilgileri al
        search_term, product_id = get_user_input()
        
        # Botu başlat
        trendyol_start(CONFIG, search_term, product_id)
    except KeyboardInterrupt:
        print("\n[!] Program kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"\n[!] Program hatası: {e}")
