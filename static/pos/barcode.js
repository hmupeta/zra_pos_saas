// Global HID keyboard-emulation barcode scanner.
// Fires a 'barcode-scanned' window event when a scan is detected.
(function () {
  let buffer = '';
  let lastKey = 0;

  document.addEventListener('keydown', (e) => {
    const t = e.target;
    const isFormField = ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName);
    if (isFormField && t.dataset.scanner !== 'true') return;

    const now = Date.now();
    if (now - lastKey > 100) buffer = '';
    lastKey = now;

    if (e.key === 'Enter') {
      const code = buffer.trim();
      buffer = '';
      if (code.length >= 4) {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent('barcode-scanned', { detail: { code } }));
      }
    } else if (/^[a-zA-Z0-9\-_]$/.test(e.key)) {
      buffer += e.key;
    }
  });
})();

function printReceipt(text) {
  const esc = String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const win = window.open('', '_blank', 'width=400,height=650');
  if (!win) { alert('Allow popups to print receipts'); return; }
  win.document.write(`
    <html><head><title>Receipt</title>
    <style>
      body { font-family: 'Courier New', monospace; font-size: 12px; margin: 8px; }
      pre { white-space: pre-wrap; word-wrap: break-word; margin: 0; }
      @media print { body { margin: 0; } }
    </style></head><body>
    <pre>${esc}</pre>
    <script>window.onload=()=>{window.print();setTimeout(()=>window.close(),100);}</script>
    </body></html>
  `);
  win.document.close();
}
