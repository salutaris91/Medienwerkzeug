import re
import os

# 1. Update style.css
css_file = "style.css"
with open(css_file, "r") as f:
    css = f.read()

# Replace colors
css = re.sub(r'--primary: #[0-9a-fA-F]+;', '--primary: #00f2fe;', css)
css = re.sub(r'--accent: #[0-9a-fA-F]+;', '--accent: #4facfe;', css)
css = re.sub(r'--accent-glow: rgba\(.*?\);', '--accent-glow: rgba(79, 172, 254, 0.3);', css)
css = re.sub(r'--accent-gradient: linear-gradient\(.*?\);', '--accent-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);', css)

# Make the New Youtube Video button green/teal like in the mockup
if ".btn-primary" in css and ".btn-primary {" not in css:
    pass # we'll just append it

with open(css_file, "w") as f:
    f.write(css)

# 2. Update index.html
html_file = "index.html"
with open(html_file, "r") as f:
    html = f.read()

# Remove tools from sidebar
html = re.sub(r'<div class="sidebar-section tools-section".*?</div>\s*</div>\s*</div>', '', html, flags=re.DOTALL)

# Add 4th card to mode selector
mode_selector_match = re.search(r'<div id="folder-mode-selector" style="[^"]*grid-template-columns:\s*repeat\(3,\s*1fr\)[^"]*">', html)
if mode_selector_match:
    html = html.replace("repeat(3, 1fr)", "repeat(4, 1fr)")
    
doku_card = '''<div class="mode-card" id="mode-doku">
                        <div class="mode-icon">🎥</div>
                        <h3>Doku</h3>
                        <p>Als Dokumentation verarbeiten</p>
                    </div>'''
tools_card = '''<div class="mode-card" id="mode-doku">
                        <div class="mode-icon">🎥</div>
                        <h3>Doku</h3>
                        <p>Als Dokumentation verarbeiten</p>
                    </div>
                    <div class="mode-card" id="mode-tools">
                        <div class="mode-icon">🛠️</div>
                        <h3>Werkzeuge</h3>
                        <p>Manuelle Ordner-Optionen</p>
                    </div>'''
html = html.replace(doku_card, tools_card)

# Add context-tools panel
context_series = '''</div>
            </div>

            <!-- STATE: YOUTUBE -->'''

context_tools = '''</div>
                
                <!-- CONTEXT: TOOLS -->
                <div id="context-tools" class="context-panel hidden card" style="animation: fadeUp 0.4s ease-out;">
                    <h3>Manuelle Werkzeuge</h3>
                    <p class="text-muted" style="margin-top:5px; margin-bottom:20px;">Führe spezielle Aktionen direkt in diesem Ordner aus:</p>
                    
                    <div class="tools-grid" style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                        <button class="btn btn-secondary" id="tool-btn-pull-files" style="padding:15px; text-align:left; display:flex; gap:15px; align-items:center;">
                            <span style="font-size:24px;">📁</span> <div><strong>Dateien hochziehen</strong><br><small class="text-muted">Unterordner auflösen</small></div>
                        </button>
                        <button class="btn btn-secondary" id="tool-btn-clean" style="padding:15px; text-align:left; display:flex; gap:15px; align-items:center;">
                            <span style="font-size:24px;">🧹</span> <div><strong>Ordner bereinigen</strong><br><small class="text-muted">Trash entfernen</small></div>
                        </button>
                        <button class="btn btn-secondary" id="tool-btn-convert" style="padding:15px; text-align:left; display:flex; gap:15px; align-items:center;">
                            <span style="font-size:24px;">🎥</span> <div><strong>H.265 Batch-Konvertierung</strong><br><small class="text-muted">Videos komprimieren</small></div>
                        </button>
                        <button class="btn btn-secondary" id="tool-btn-nfo-agent" style="padding:15px; text-align:left; display:flex; gap:15px; align-items:center;">
                            <span style="font-size:24px;">📝</span> <div><strong>NFO Agent</strong><br><small class="text-muted">Metadaten generieren</small></div>
                        </button>
                        <button class="btn btn-secondary" id="tool-btn-manual-sync" style="padding:15px; text-align:left; display:flex; gap:15px; align-items:center;">
                            <span style="font-size:24px;">☁️</span> <div><strong>Manuelles Syncing</strong><br><small class="text-muted">Auf NAS kopieren</small></div>
                        </button>
                        <div class="fsk-tool-container" style="display:flex; gap:10px;">
                            <button class="btn btn-secondary" id="tool-btn-nfo-batch" style="padding:15px; text-align:left; flex:1; display:flex; gap:15px; align-items:center;">
                                <span style="font-size:24px;">🏷️</span> <div><strong>FSK Batch</strong><br><small class="text-muted">Altersfreigabe setzen</small></div>
                            </button>
                            <input type="number" id="tool-fsk-value" value="16" min="0" max="18" style="width: 70px; background:var(--bg-base); color:var(--text-main); border:1px solid var(--border-glass); border-radius:var(--radius-md); text-align:center; font-size:18px;">
                        </div>
                    </div>
                </div>
            </div>

            <!-- STATE: YOUTUBE -->'''
html = html.replace(context_series, context_tools)

with open(html_file, "w") as f:
    f.write(html)

# 3. Update app.js
js_file = "app.js"
with open(js_file, "r") as f:
    js = f.read()

js = js.replace('const modes = ["movie", "series", "doku"];', 'const modes = ["movie", "series", "doku", "tools"];')
js = js.replace('let ctxTarget = mode === "doku" ? "context-movie" : `context-${mode}`;', 'let ctxTarget = mode === "doku" ? "context-movie" : `context-${mode}`;')

with open(js_file, "w") as f:
    f.write(js)

print("Done")
