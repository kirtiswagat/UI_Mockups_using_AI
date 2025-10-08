# UI Mockups — AI Powered MVP (Streamlit + OpenAI + Figma Plugin)

An MVP that lets a user upload a requirements document, generates AI mockup images, previews them in Streamlit, and then sends those mockups to Figma using a small Figma plugin.

## What’s inside

- **Streamlit app** (`app/`) — upload doc → extract requirements → prompt → generate mockups → preview → export bundle for Figma.
- **Figma plugin** (`plugin/`) — paste the bundle (JSON). It creates frames in the current Figma file, filling them with your images.
- **No backend DB** — simple and lightweight. You can add S3 or any storage later.

## Quick start

### 1) Setup
```bash
python -V  # Python 3.10+ recommended
pip install -r requirements.txt
cp .env.example .env  # add your OpenAI key
```

Edit `.env` and set:
```
OPENAI_API_KEY=sk-...your-key...
APP_BASE_URL=http://localhost:8501
```

### 2) Run Streamlit
```bash
streamlit run app/app.py
```
Open the browser link shown by Streamlit.

### 3) Use the app
- Upload a **TXT/MD/DOCX/PDF** with UI requirements.
- Click **Generate Mockups** to create 2–3 mockup PNGs.
- Scroll to **Send to Figma** — copy the JSON bundle (it contains **data URLs** of the images).

### 4) Install the Figma Plugin
In Figma:
- **Plugins → Development → New Plugin… → Link existing** and select the `plugin/manifest.json` in this repo.
- Open any Figma file → **Plugins → Development → UI Mockups Importer (MVP)**.
- Paste the JSON bundle into the plugin and click **Import Images**.
- The plugin creates frames and fills them with your mockups.

> **Note:** The plugin supports both `data` (base64 data URL) and `url` (https) sources. For production, prefer HTTPS URLs (e.g., presigned S3).

## Project structure

```
ui-mockups-mvp/
├─ app/
│  ├─ app.py                # Streamlit app
│  └─ utils/
│     ├─ file_readers.py    # TXT/DOCX/PDF readers
│     └─ prompt.py          # Prompt builder
├─ plugin/
│  ├─ manifest.json
│  ├─ ui.html
│  ├─ code.ts               # TypeScript source
│  └─ code.js               # Built JS (precompiled for convenience)
├─ .env.example
├─ requirements.txt
├─ LICENSE
└─ README.md
```

## OpenAI notes

- This MVP uses the **Images API** (model: `gpt-image-1`) to generate PNG mockups.
- You can change image size (`1024x1024`, `1024x1536`, etc.) and the number of images.
- For multi-screen flows, first ask a text model to produce a **structured list of screens**, then generate per-screen images.

## Figma notes

- Creating nodes/frames requires the **Figma Plugin API**. The plugin here reads your bundle and creates frames with image fills.
- Later, add OAuth + REST for file listing or comments (not needed for this MVP).

## Next steps (nice upgrades)

- Replace data URLs with **HTTPS URLs** (S3 presigned) for larger images.
- Add “Regenerate this screen” buttons and a gallery grid.
- Export a **copy deck JSON** alongside images for handoff.
- Add a tiny backend for OAuth with Figma and persistent sessions.

## License

MIT
