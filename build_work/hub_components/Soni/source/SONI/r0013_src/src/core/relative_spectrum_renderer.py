from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QRectF, Qt


@dataclass(slots=True)
class RelativeSpectrumRenderResult:
    image_item: pg.ImageItem | None
    frequency_mhz: np.ndarray
    time_s: np.ndarray
    current_spectra: list[tuple[str, np.ndarray, np.ndarray]]


class RelativeSpectrumRenderer:
    """One rendering engine shared by the embedded chart and popup.

    The heat map contains every decoded FFT bin. Coloured lines are the current
    frame spectra for the selected hydrophone channels; they are not ridge or
    peak-frequency traces.
    """

    LUT = np.array(
        [[0, 0, 20, 255], [0, 50, 150, 255], [0, 205, 255, 255],
         [255, 235, 0, 255], [255, 80, 0, 255], [255, 255, 255, 255]],
        dtype=np.ubyte,
    )

    @staticmethod
    def _relative(values: Iterable[float]) -> np.ndarray:
        data = np.abs(np.nan_to_num(np.asarray(list(values), dtype=float)))
        if not data.size:
            return data
        baseline = float(np.nanpercentile(data, 10))
        high = float(np.nanpercentile(data, 99.5))
        span = max(high - baseline, 1e-12)
        return np.clip((data - baseline) / span * 4.0, 0.0, 4.0)

    def render(self, plot, channels: dict[str, list], selected: list[str], frame_index: int,
               replay_count: int, colors: dict[str, str], main_frequency_hz: float | None,
               title: str = "") -> RelativeSpectrumRenderResult:
        plot.clear()
        plot.showGrid(x=True, y=True, alpha=.15)
        plot.setLabel("left", "Frequency", units="MHz")
        plot.setLabel("bottom", "Replay time", units="sec")
        if title:
            plot.setTitle(title)

        matrices=[]
        common_freq=None
        current=[]
        max_rows=0
        for ch in selected:
            frames=channels.get(ch, [])
            rows=[]; freq_axis=None
            for frame in frames:
                f=np.asarray(frame.frequency, float)/1e6
                a=self._relative(frame.amplitude)
                mask=(f>=.2)&(f<=.8)
                if mask.any():
                    rows.append(a[mask]); freq_axis=f[mask]
            if not rows or freq_axis is None:
                continue
            width=min(len(freq_axis), min(len(r) for r in rows))
            matrix=np.vstack([r[:width] for r in rows])
            matrices.append(matrix)
            common_freq=freq_axis[:width]
            max_rows=max(max_rows, matrix.shape[0])
            idx=0 if len(frames)==1 else int(round(np.clip(frame_index,0,max(replay_count-1,0))*(len(frames)-1)/max(replay_count-1,1)))
            frame=frames[idx]
            f=np.asarray(frame.frequency,float)/1e6
            a=self._relative(frame.amplitude)
            mask=(f>=.2)&(f<=.8)
            current.append((ch,f[mask],a[mask]))

        if not matrices or common_freq is None:
            return RelativeSpectrumRenderResult(None,np.array([]),np.array([]),[])

        cols=min(m.shape[1] for m in matrices)
        combined=np.full((max_rows,cols),np.nan)
        for matrix in matrices:
            padded=np.full((max_rows,cols),np.nan)
            padded[:matrix.shape[0],:cols]=matrix[:,:cols]
            combined=np.fmax(combined,padded)
        image=combined.T
        duration=max(.001,float(max(replay_count-1,1))*4.0)
        f0=float(common_freq[0]); f1=float(common_freq[cols-1])
        item=pg.ImageItem(axisOrder="row-major")
        item.setImage(image,autoLevels=False,levels=(0.0,4.0))
        item.setLookupTable(pg.ColorMap(np.linspace(0,1,len(self.LUT)),self.LUT).getLookupTable(0,1,256))
        item.setRect(QRectF(0,f0,duration,max(1e-6,f1-f0)))
        plot.addItem(item)

        cursor_x=float(np.clip(frame_index,0,max(replay_count-1,0)))*4.0
        plot.addItem(pg.InfiniteLine(pos=cursor_x,angle=90,movable=False,pen=pg.mkPen("w",width=1.3)))
        if main_frequency_hz:
            main=float(main_frequency_hz)/1e6
            for value,label in ((main/2,"½ Main"),(main,"Main")):
                if .2 <= value <= .8:
                    line=pg.InfiniteLine(pos=value,angle=0,movable=False,pen=pg.mkPen("#ffcc00",width=1,style=Qt.PenStyle.DashLine))
                    plot.addItem(line)
        plot.setXRange(0,duration,padding=0)
        plot.setYRange(.2,.8,padding=0)

        # Current FFT overlay: map amplitude to a narrow time-width at the current cursor.
        overlay_width=max(duration*.10,4.0)
        for ch,f,a in current:
            if not len(f): continue
            x=cursor_x + (a/4.0-.5)*overlay_width
            plot.plot(x,f,pen=pg.mkPen(colors.get(ch,"#ffffff"),width=2.0),name=ch)
        return RelativeSpectrumRenderResult(item,common_freq[:cols],np.linspace(0,duration,max_rows),current)
