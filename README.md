# Trendyol Bot - Automated Product Search and Cart Addition

## 📋 Overview

This project contains two automated bots that interact with Trendyol.com to search for specific products and add them to the shopping cart. The bots simulate real human behavior to avoid detection and provide realistic user interactions.

## 🚀 Features

### Core Functionality
- **Interactive Product Search**: Ask user for search terms and target product IDs
- **Automated Navigation**: Navigate through Trendyol's website automatically
- **Human-like Behavior**: Simulate realistic user interactions including:
  - Natural scrolling patterns
  - Random mouse movements
  - Realistic typing speed with occasional typos
  - Variable wait times between actions
- **Product Detection**: Find specific products by ID in search results
- **Cart Addition**: Automatically add found products to shopping cart

### Anti-Detection Features
- **Browser Fingerprinting Protection**: 
  - WebGL spoofing
  - Canvas fingerprinting protection
  - Audio context spoofing
  - Font detection protection
  - Battery API spoofing
  - Touch support spoofing
- **Privacy Features**:
  - Do Not Track enabled
  - Media access blocking
  - WebRTC hardening
- **Realistic Browser Simulation**:
  - Linux user agents
  - Turkish locale (tr-TR)
  - Europe/Istanbul timezone
  - Custom screen resolution

## 📁 Project Structure

```
bot/
├── main.py          # Main bot implementation
├── bot2.py          # Enhanced bot with additional features
├── README.md        # This documentation file
└── requirements.txt # Python dependencies (to be created)
```

## 🛠 Installation

### Prerequisites
- Python 3.8 or higher
- Windows operating system
- Internet connection

### Setup Steps

1. **Clone or download the project**
   ```bash
   cd c:\Users\DENİZ\Desktop\bot
   ```

2. **Install Python dependencies**
   ```bash
   pip install playwright
   playwright install chromium
   ```

3. **Install additional required packages**
   ```bash
   pip install pathlib uuid
   ```

## 🎮 Usage

### Running the Bot

1. **Choose your bot version:**
   - `main.py` - Basic version with core functionality
   - `bot2.py` - Enhanced version with advanced user interactions

2. **Start the bot:**
   ```bash
   python bot2.py
   ```
   or
   ```bash
   python main.py
   ```

3. **Follow the interactive prompts:**

   ```
   === TRENDYOl BOT ====
   Bu bot Trendyol'da belirttiğiniz ürünü arayacak ve sepete ekleyecek.

   Ne aramak istersiniz? (örnek: ayakkabı, şal, çanta): ayakkabı

   Hedef ürün ID'sini girin (Trendyol URL'den): 123456789

   [+] Arama terimi: ayakkabı
   [+] Hedef ürün ID: 123456789
   [+] Bot başlatılıyor...
   ```

### Finding Product IDs

To find a product ID from Trendyol:
1. Go to the product page on Trendyol
2. Look at the URL: `https://www.trendyol.com/brand/product-name-p-123456789`
3. The number after `-p-` is your product ID (123456789)

## ⚙️ Configuration

### Bot Settings

The bot behavior can be customized by modifying the `CONFIG` dictionary in the files:

```python
CONFIG = {
    "ENGINE": "chromium",                    # Browser engine
    "ENABLE_USER_AGENT": True,              # Use custom user agent
    "LOCALE": "tr-TR",                      # Turkish locale
    "TIMEZONE": "Europe/Istanbul",          # Istanbul timezone
    "SCREEN_WIDTH": 1920,                   # Screen resolution
    "SCREEN_HEIGHT": 1080,
    "DEVICE_SCALE_FACTOR": 0.75,           # Display scaling
    # ... other privacy and anti-detection settings
}
```

### Cycle Settings

- `CYCLE_SLEEP`: Wait time between cycles (6-14 seconds)
- `RECREATE_EVERY`: How often to recreate browser context (every 2 cycles)

## 🔄 How It Works

### 1. Browser Initialization
- Launches Chromium browser with anti-detection measures
- Sets up Turkish locale and Istanbul timezone
- Applies fingerprinting protection scripts

### 2. Trendyol Navigation
- Navigates to trendyol.com
- Handles gender selection popup (selects "Kadın")
- Accepts cookies if prompted

### 3. Product Search
- Enters user-specified search term
- Waits for search results to load
- Scales page for better visibility

### 4. Product Finding
- Scrolls through search results intelligently
- Looks for specific product ID in URLs
- Uses human-like scrolling patterns

### 5. Product Interaction
- Clicks on target product to open product page
- Handles popup dialogs
- Browses product gallery
- Scrolls through product details
- Simulates realistic user interest

### 6. Cart Addition
- Adds product to shopping cart
- Performs additional engagement actions
- Completes the cycle

## 🎯 Bot Versions Comparison

| Feature | main.py | bot2.py |
|---------|---------|---------|
| Basic Search & Cart | ✅ | ✅ |
| Anti-Detection | ✅ | ✅ |
| Human-like Behavior | ✅ | ✅ |
| Advanced User Interaction | ❌ | ✅ |
| Realistic Timing | ❌ | ✅ |
| Product Engagement | ❌ | ✅ |
| Algorithm Optimization | ❌ | ✅ |
| Extended User Interest | ❌ | ✅ |

## 📊 Success Tracking

The bot tracks and displays:
- Successful cycles
- Failed cycles
- Success rate percentage
- Real-time status updates

Example output:
```
[cycle 5] durum: BAŞARILI
[cycle 5] skor (başarılı/başarısız): 4/1
[cycle 5] oran  (başarılı/toplam):   4/5
```

## ⚠️ Important Notes

### Legal and Ethical Use
- This bot is for educational and testing purposes
- Ensure compliance with Trendyol's Terms of Service
- Use responsibly and avoid excessive requests
- Respect website resources and bandwidth

### Limitations
- Requires stable internet connection
- May need adjustments if Trendyol updates their website
- Success rate depends on network conditions and website changes

### Troubleshooting
- If bot fails consistently, check product ID validity
- Ensure target product is available and in stock
- Check internet connection stability
- Verify Trendyol website accessibility

## 🔧 Technical Details

### Dependencies
- `playwright`: Web automation framework
- `pathlib`: File path handling
- `uuid`: Unique identifier generation
- `random`: Random number generation for human-like behavior
- `time`: Timing and delays
- `re`: Regular expressions for pattern matching

### Browser Features
- Persistent user profiles (temporary)
- Custom extensions support
- WebRTC blocking
- Fingerprinting protection
- Stealth mode operation

## 📈 Performance

### Optimization Features
- Intelligent scrolling algorithms
- Adaptive wait times
- Resource cleanup after each cycle
- Memory management for long-running sessions

### Success Factors
- Realistic human behavior simulation
- Anti-detection measures
- Robust error handling
- Flexible target product finding

## 🆘 Support

If you encounter issues:
1. Check the console output for error messages
2. Verify product ID format (numbers only)
3. Ensure stable internet connection
4. Try running with a different product ID
5. Check if Trendyol website is accessible

## 📄 License

This project is for educational purposes. Please use responsibly and in accordance with applicable terms of service and local laws.

---

**Note**: This bot simulates real user behavior and should be used ethically and responsibly. Always respect website terms of service and rate limiting.
