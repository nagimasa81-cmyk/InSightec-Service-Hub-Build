# RC2-R0008 Direct Live Render Binding

- Replaces signal-only arrow/slider rendering with a deterministic direct final render.
- Anatomy/Thermal thumbnails use itemPressed/itemActivated and immediately display their exact payload.
- Navigation always exits Planning mode and renders the requested MR acquisition frame.
- Runtime frame label exposes mode, MR index, temperature index, and render serial.
- ROI remains 3 x 3 pixels.
