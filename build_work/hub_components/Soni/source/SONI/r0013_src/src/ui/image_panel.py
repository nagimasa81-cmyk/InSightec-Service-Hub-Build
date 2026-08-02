from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal, QPointF, Qt, QTimer
from PySide6.QtWidgets import QGroupBox, QVBoxLayout


class InteractivePlotWidget(pg.PlotWidget):
    wlwwDragged = Signal(float, float)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._right_start = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._right_start = event.position()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._right_start is not None:
            delta = event.position() - self._right_start
            self._right_start = event.position()
            self.wlwwDragged.emit(float(delta.x()), float(delta.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self._right_start is not None:
            self._right_start = None
            event.accept()
            return
        super().mouseReleaseEvent(event)


class ImagePanel(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.view = InteractivePlotWidget(); self.view.setAspectLocked(True); self.view.invertY(True)
        self.view.hideAxis("left"); self.view.hideAxis("bottom")
        self.image = pg.ImageItem(axisOrder="row-major"); self.view.addItem(self.image)
        layout = QVBoxLayout(self); layout.setContentsMargins(2,4,2,2); layout.addWidget(self.view)

    def set_image(self, array, levels=None, lut=None, hotspot=None, hotspot_text=None):
        if array is None: self.image.clear(); return
        self.image.setImage(np.asarray(array), autoLevels=levels is None, levels=levels)
        self.image.setLookupTable(lut); self.view.autoRange(padding=0.01)


class OverlayPanel(QGroupBox):
    cursorMoved = Signal(float, float)
    viewStateChanged = Signal()
    levelsChanged = Signal(float, float)

    def __init__(self, title="Magnitude + Temperature Overlay", parent=None):
        super().__init__(title, parent)
        self.view = InteractivePlotWidget(); self.view.setAspectLocked(True); self.view.invertY(True)
        self.view.hideAxis("left"); self.view.hideAxis("bottom"); self.view.setMouseEnabled(x=True,y=True)
        self.magnitude_item = pg.ImageItem(axisOrder="row-major")
        self.temperature_item = pg.ImageItem(axisOrder="row-major")
        self.view.addItem(self.magnitude_item); self.view.addItem(self.temperature_item)
        self.cursor_target = pg.TargetItem(movable=True,size=18,symbol="+",pen=pg.mkPen("#00d9ff",width=2),hoverPen=pg.mkPen("#ffffff",width=2))
        self.cursor_target.setVisible(False); self.view.addItem(self.cursor_target)
        self.cursor_target.sigPositionChanged.connect(self._target_dragged)
        self.cursor_label = pg.TextItem(anchor=(0,0),color="#f5f5f5",fill=pg.mkBrush(0,0,0,185)); self.cursor_label.setVisible(False); self.view.addItem(self.cursor_label)
        self.hover_label = pg.TextItem(anchor=(0.5,0), color="#ffffff", fill=pg.mkBrush(0,0,0,205)); self.hover_label.setZValue(80); self.hover_label.hide(); self.view.addItem(self.hover_label)
        self._hover_temperature = None
        self._hover_proxy = pg.SignalProxy(self.view.scene().sigMouseMoved, rateLimit=45, slot=self._hover_moved)
        # The 20-pixel target circle is display-only.  The 3 x 3 pixel square
        # is the actual temperature calculation voxel/ROI.
        self.target_circle = pg.EllipseROI((0,0),(20,20),movable=False,pen=pg.mkPen("#00a8ff",width=2.5))
        self.target_circle.setAcceptedMouseButtons(Qt.MouseButton.NoButton); self.target_circle.setVisible(False); self.view.addItem(self.target_circle)
        self.roi_box = pg.RectROI((0,0),(3,3),movable=False,pen=pg.mkPen("#00e5ff",width=2.0))
        self.roi_box.setAcceptedMouseButtons(Qt.MouseButton.NoButton); self.roi_box.setVisible(False); self.view.addItem(self.roi_box)
        self._shape=None; self._updating_target=False
        self._wlww_drag_start=None; self._wlww_start_levels=None
        self.view.scene().sigMouseClicked.connect(self._clicked)
        self.view.wlwwDragged.connect(self._wlww_dragged)
        self.view.plotItem.vb.sigRangeChanged.connect(lambda *_: self.viewStateChanged.emit())
        layout=QVBoxLayout(self); layout.setContentsMargins(2,4,2,2); layout.addWidget(self.view)

    def _display_to_data_y(self, y):
        # ViewBox.invertY(True) gives conventional raster display: row 0 at top.
        return float(y)
    def _data_to_display_y(self, y):
        return float(y)


    def _wlww_dragged(self, dx, dy):
        levels = self.magnitude_item.getLevels()
        if levels is None:
            return
        low, high = map(float, levels)
        width = max(1e-6, high-low)
        center = (high+low)/2.0
        width = max(1e-6, width * (1.0 + dx/250.0))
        center = center - dy * width/300.0
        new_levels=(center-width/2.0, center+width/2.0)
        self.magnitude_item.setLevels(new_levels)
        self.levelsChanged.emit(float(new_levels[0]), float(new_levels[1]))

    def view_range(self):
        return self.view.plotItem.vb.viewRange()

    def set_view_range(self, ranges):
        try:
            self.view.setXRange(*ranges[0], padding=0)
            self.view.setYRange(*ranges[1], padding=0)
        except Exception:
            pass

    def _clicked(self,event):
        if self._shape is None or event.button()!=Qt.MouseButton.LeftButton: return
        point=self.view.plotItem.vb.mapSceneToView(event.scenePos())
        x=float(np.clip(point.x(),0,self._shape[1]-1)); yd=float(np.clip(point.y(),0,self._shape[0]-1))
        self.cursorMoved.emit(x,self._display_to_data_y(yd))

    def _target_dragged(self):
        if self._updating_target or self._shape is None: return
        pos=self.cursor_target.pos(); x=float(np.clip(pos.x(),0,self._shape[1]-1)); yd=float(np.clip(pos.y(),0,self._shape[0]-1))
        self.cursorMoved.emit(x,self._display_to_data_y(yd))

    def set_cursor(self,x,y,text=""):
        yd=self._data_to_display_y(y); self._updating_target=True; self.cursor_target.setPos(QPointF(x,yd)); self._updating_target=False
        self.cursor_label.setPos(x+4,yd+5); self.cursor_label.setText(text); self.cursor_target.setVisible(True); self.cursor_label.setVisible(bool(text))

    def set_hover_temperature(self, array):
        self._hover_temperature = None if array is None else np.asarray(array, float)
        if self._hover_temperature is None:
            self.hover_label.hide()

    def _hover_moved(self, event):
        scene_pos = event[0] if isinstance(event, (tuple, list)) else event
        arr = self._hover_temperature
        if arr is None or self._shape is None or not self.view.sceneBoundingRect().contains(scene_pos):
            self.hover_label.hide(); return
        point = self.view.plotItem.vb.mapSceneToView(scene_pos)
        x = int(round(point.x())); y = int(round(self._display_to_data_y(point.y())))
        if x < 0 or y < 0 or y >= arr.shape[0] or x >= arr.shape[1]:
            self.hover_label.hide(); return
        value = arr[y, x]
        if not np.isfinite(value):
            self.hover_label.hide(); return
        # Place below the pointer; clamp near image borders so the label remains visible.
        px = float(np.clip(point.x(), 8, max(8, arr.shape[1]-8)))
        py = float(np.clip(point.y()+8, 0, max(0, arr.shape[0]-4)))
        self.hover_label.setText(f"{value:.1f} °C")
        self.hover_label.setPos(px, py)
        self.hover_label.show()

    def set_roi(self,center_x,center_y,radius=None,width=None,height=None):
        if center_x is None or center_y is None:
            self.target_circle.setVisible(False); self.roi_box.setVisible(False); return
        # Geometry is intentionally pixel-based until reliable spacing metadata
        # is decoded.  The target circle is 20 pixels and display-only.
        circle_w=20.0; circle_h=20.0
        yd=self._data_to_display_y(center_y)
        self.target_circle.setPos((center_x-circle_w/2.0,yd-circle_h/2.0),update=False)
        self.target_circle.setSize((circle_w,circle_h),update=False); self.target_circle.setVisible(True)
        square_w=max(1.0,float(width or 3.0)); square_h=max(1.0,float(height or 3.0))
        self.roi_box.setPos((center_x-square_w/2.0,yd-square_h/2.0),update=False)
        self.roi_box.setSize((square_w,square_h),update=False); self.roi_box.setVisible(True)

    def fit_image(self): self.view.autoRange(padding=0.01)

    def magnitude_levels(self):
        levels=self.magnitude_item.getLevels()
        return tuple(map(float,levels)) if levels is not None else None

    def set_magnitude_levels(self, levels):
        if levels is not None:
            try:
                self.magnitude_item.setLevels(tuple(map(float, levels)))
            except Exception:
                pass

    def set_overlay(self,magnitude,temperature,magnitude_levels=None,temperature_levels=None,temperature_lut=None,opacity=0.55,hotspot=None,hotspot_text=None,temperature_threshold=None,fit=False):
        if magnitude is None: self.magnitude_item.clear()
        else:
            mag=np.asarray(magnitude); self._shape=mag.shape[:2]; self.magnitude_item.setLookupTable(None)
            self.magnitude_item.setImage(mag,autoLevels=magnitude_levels is None,levels=magnitude_levels)
        if temperature is None: self.temperature_item.clear()
        else:
            temp=np.asarray(temperature); self._shape=temp.shape[:2]; shown=temp if temperature_threshold is None else np.where(temp>=temperature_threshold,temp,np.nan)
            self.temperature_item.setImage(shown,autoLevels=temperature_levels is None,levels=temperature_levels)
            self.temperature_item.setLookupTable(temperature_lut); self.temperature_item.setOpacity(max(0.0,min(1.0,opacity)))
        if fit: self.fit_image()
