// UI Mockups Importer (MVP)
// Supports images via `data` (base64 data URL) or `url` (https).

figma.showUI(__html__, { width: 420, height: 320 });

async function createFrameFromBytes(bytes: Uint8Array, name: string, x: number, y: number) {
  const img = figma.createImage(bytes);
  const frame = figma.createFrame();
  frame.name = name || 'Mockup';
  frame.resize(1024, 1024);
  frame.x = x;
  frame.y = y;
  frame.fills = [{ type: 'IMAGE', imageHash: img.hash, scaleMode: 'FILL' }];
  figma.currentPage.appendChild(frame);
}

async function fetchAsBytes(url: string): Promise<Uint8Array> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const ab = await res.arrayBuffer();
  return new Uint8Array(ab);
}

function dataUrlToBytes(dataUrl: string): Uint8Array {
  // data:image/png;base64,....
  const commaIdx = dataUrl.indexOf(',');
  const b64 = commaIdx >= 0 ? dataUrl.substring(commaIdx + 1) : dataUrl;
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

figma.ui.onmessage = async (msg) => {
  if (msg.type !== 'import') return;
  try {
    const data = JSON.parse(msg.raw || "{}");
    const arr: any[] = data.images || [];
    let x = 0, y = 0;

    for (const item of arr) {
      if (item.data && typeof item.data === 'string' && item.data.startsWith('data:image/')) {
        const bytes = dataUrlToBytes(item.data);
        await createFrameFromBytes(bytes, item.name || 'Mockup', x, y);
        x += 1120;
        continue;
      }
      if (item.url && typeof item.url === 'string') {
        const bytes = await fetchAsBytes(item.url);
        await createFrameFromBytes(bytes, item.name || 'Mockup', x, y);
        x += 1120;
        continue;
      }
      figma.notify('Skipping an item without `data` or `url`');
    }
    figma.closePlugin('Imported mockups.');
  } catch (e: any) {
    figma.notify('Import failed: ' + e.message);
  }
};
