EVEZ 3D RELIEF LAB

INTERACTIVE VIEWER
Open evez_3d_relief_lab.html in a modern browser with WebGL 2 support. It is self-contained and does not load a 3D engine from the internet. Drag to orbit; wheel or pinch to zoom; right-drag or Shift-drag to pan. Preset buttons provide front, side, top, and back views. Photo, shaded relief, edge-contour, wire-mesh, raking-light, and relief-exaggeration controls are available. Tap reference images to inspect the source views.

PORTABLE MESHES
- dark_interactive_relief.glb
- pale_interactive_relief.glb
These open in GLB/glTF-compatible 3D viewers.

GEOMETRY STATUS
These are interactive photograph-derived relief models, not calibrated full-object photogrammetry scans. The visible front is textured from the supplied source photograph. Depth is inferred from brightness, local contrast, and a silhouette-distance envelope. The back and thickness are neutral synthetic geometry because they are not fully measured in the supplied images. The browser viewer uses orthographic projection to avoid adding perspective during inspection, but cannot reverse lens or perspective distortion already present in the source photographs. Dimensions are normalized and are not suitable for metric measurements.

TO CAPTURE A TRUE 3D SURFACE
For a measured full-object reconstruction, photograph the specimen with sharp focus and diffuse fixed lighting, include a scale bar, and capture overlapping views around the entire object at multiple elevations (including the far side and top/bottom where accessible). Aim for 70–80% overlap between consecutive images, avoid blur and changing focus, and keep the specimen stationary relative to the background or rotate it slowly against a static camera. The current files lack complete calibrated coverage, so a faithful metric surface cannot yet be asserted.
