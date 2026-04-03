# Demo GIF Creation Instructions

To create a compelling demo GIF for Lazarus Protocol, follow these steps:

## 🎬 Recommended Tools

### Linux
- **Peek**: Simple screen recorder for GIFs
  ```bash
  sudo apt install peek
  ```
- **Kooha**: GTK-based screen recorder
  ```bash
  flatpak install flathub io.github.seadve.Kooha
  ```

### Windows
- **ScreenToGif**: Excellent free tool with editor
  Download from: https://www.screentogif.com/

### macOS
- **Giphy Capture**: Free from Mac App Store
- **LICEcap**: Lightweight screen recorder

## 📏 Technical Specifications

- **Resolution**: 1200×675px (16:9 aspect ratio)
- **Duration**: 8-12 seconds total
- **Framerate**: 15 FPS
- **File Size**: Under 5MB ideally
- **Format**: GIF with optimized palette

## 🎯 Demo Content Flow

Capture this sequence in under 12 seconds:

1. **Setup (2s)**: Show `lazarus init` command with interactive prompts
2. **Encryption (2s)**: Show file being encrypted (progress bar/visual)
3. **Monitoring (2s)**: Show `lazarus agent start` and status check
4. **Check-in (2s)**: Show `lazarus ping` command working
5. **Alerts (2s)**: Show email/Telegram notification arriving
6. **Delivery (2s)**: Show beneficiary receiving decryption kit

## 🎨 Visual Style

- **Terminal Theme**: Use a clean, modern terminal theme (like One Dark)
- **Font**: Monospace font (Fira Code, JetBrains Mono)
- **Highlighting**: Use color to show important commands/output
- **Transitions**: Smooth transitions between scenes

## ⚙️ Optimization

After recording, optimize the GIF:

```bash
# Install gifsicle
sudo apt install gifsicle

# Optimize GIF (reduces file size by 60-80%)
gifsicle -O3 demo.gif -o demo-optimized.gif

# Further optimization with lossy compression
gifsicle -O3 --lossy=80 demo.gif -o demo-compressed.gif
```

## 🖼️ Alternative: Screenshot Montage

If screen recording is challenging, create a montage of:

1. Setup wizard screenshot
2. Encryption process screenshot
3. Agent status screenshot
4. Alert notification screenshot
5. Delivery confirmation screenshot

Use a tool like **GIMP** or **Canva** to arrange them with captions.

## 📝 Script for Voiceover (Optional)

If adding voiceover, use this script:

> "Lazarus Protocol: Set up your digital legacy in seconds. Encrypt your crypto secrets, set your check-in schedule, and rest easy knowing your assets will reach your loved ones - even if you can't."

## 🚀 Publishing

- Upload optimized GIF to `/assets/demo.gif`
- Update README.md with correct path
- Test on multiple devices (mobile + desktop)
- Consider creating a shorter version (5s) for social media