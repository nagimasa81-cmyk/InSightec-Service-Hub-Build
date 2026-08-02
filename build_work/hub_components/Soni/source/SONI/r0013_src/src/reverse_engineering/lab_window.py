from __future__ import annotations

import csv
import json
import math
import shutil
import tempfile
import zipfile
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QSpinBox, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from src.common.theme import DARK_STYLESHEET
from src.reverse_engineering.binary_probe import BinaryProbe, NumericCandidate
from src.reverse_engineering.hydrophone_lab import HydrophoneReverseEngineeringLab
from src.reverse_engineering.cavitation_timeline import CavitationTimelineAnalyzer


NUMPY_DTYPES = {
    "Float32 LE": "<f4", "Float32 BE": ">f4", "Float64 LE": "<f8", "Float64 BE": ">f8",
    "Int16 LE": "<i2", "Int16 BE": ">i2", "UInt16 LE": "<u2", "UInt16 BE": ">u2",
    "Int32 LE": "<i4", "Int32 BE": ">i4", "UInt8": "u1",
}


class AnalyzeWorker(QThread):
    progress = Signal(int, str)
    completed = Signal(object, object)
    failed = Signal(str)

    def __init__(self, root: Path):
        super().__init__(); self.root = root

    def run(self) -> None:
        try:
            self.progress.emit(5, "Discovering hydrophone files…")
            report = HydrophoneReverseEngineeringLab().analyze(self.root)
            self.progress.emit(100, "Analysis complete")
            self.completed.emit(report, self.root / "Hydrophone_RE_Report")
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class HydrophoneLabWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Hydrophone Reverse Engineering Lab")
        self.resize(1500, 920)
        self.setAcceptDrops(True)
        self.probe = BinaryProbe()
        self.root: Path | None = None
        self.temp_dir: Path | None = None
        self.current_file: Path | None = None
        self.current_profile = None
        self.current_values = np.array([], dtype=float)
        self.report = None
        self.worker: AnalyzeWorker | None = None
        self._build_ui()
        self.setStyleSheet(DARK_STYLESHEET)

    def _build_ui(self) -> None:
        central = QWidget(); self.setCentralWidget(central)
        outer = QVBoxLayout(central); outer.setContentsMargins(8,8,8,8)
        toolbar = QHBoxLayout()
        self.path_edit = QLineEdit(); self.path_edit.setPlaceholderText("Drop an ANx ZIP, folder, or DMP file here")
        for text, slot in (("Open ZIP/Folder/File", self.choose_source), ("Analyze All", self.analyze_all), ("Export Session", self.export_session)):
            b=QPushButton(text); b.clicked.connect(slot); toolbar.addWidget(b)
        toolbar.insertWidget(0, self.path_edit, 1); outer.addLayout(toolbar)
        self.progress=QProgressBar(); self.progress.setRange(0,100); self.progress.hide(); outer.addWidget(self.progress)

        split=QSplitter(Qt.Horizontal); outer.addWidget(split,1)
        self.tree=QTreeWidget(); self.tree.setHeaderLabels(["Hydrophone files", "Size"]); self.tree.itemSelectionChanged.connect(self._tree_selected); split.addWidget(self.tree)
        self.tabs=QTabWidget(); split.addWidget(self.tabs); split.setSizes([330,1170])
        self._make_binary_tab(); self._make_decoder_tab(); self._make_fft_tab(); self._make_structure_tab(); self._make_correlation_tab(); self._make_cavitation_tab(); self._make_report_tab()
        self.statusBar().showMessage("Ready — drop an export ZIP or folder")

    def _make_binary_tab(self):
        w=QWidget(); l=QVBoxLayout(w)
        bar=QHBoxLayout(); self.hex_offset=QSpinBox(); self.hex_offset.setMaximum(2_000_000_000); self.hex_offset.setPrefix("Offset ")
        self.hex_length=QSpinBox(); self.hex_length.setRange(64,65536); self.hex_length.setValue(4096); self.hex_length.setPrefix("Bytes ")
        b=QPushButton("Refresh"); b.clicked.connect(self.refresh_hex)
        bar.addWidget(self.hex_offset); bar.addWidget(self.hex_length); bar.addWidget(b); bar.addStretch(); l.addLayout(bar)
        self.hex_view=QTextEdit(); self.hex_view.setReadOnly(True); self.hex_view.setLineWrapMode(QTextEdit.NoWrap); l.addWidget(self.hex_view)
        self.tabs.addTab(w,"Binary Explorer")

    def _make_decoder_tab(self):
        w=QWidget(); l=QVBoxLayout(w)
        form=QHBoxLayout(); self.dtype_combo=QComboBox(); self.dtype_combo.addItems(NUMPY_DTYPES)
        self.decode_offset=QSpinBox(); self.decode_offset.setMaximum(2_000_000_000)
        self.decode_count=QSpinBox(); self.decode_count.setRange(16,2_000_000); self.decode_count.setValue(2048)
        self.remove_dc=QCheckBox("Remove DC"); self.remove_dc.setChecked(True)
        b=QPushButton("Decode / Preview"); b.clicked.connect(self.decode_current)
        for label,widget in (("Type",self.dtype_combo),("Offset",self.decode_offset),("Count",self.decode_count)):
            form.addWidget(QLabel(label)); form.addWidget(widget)
        form.addWidget(self.remove_dc); form.addWidget(b); form.addStretch(); l.addLayout(form)
        self.decode_plot=pg.PlotWidget(); self.decode_plot.showGrid(x=True,y=True,alpha=.25); l.addWidget(self.decode_plot,1)
        self.stats=QLabel("No candidate loaded"); self.stats.setTextInteractionFlags(Qt.TextSelectableByMouse); l.addWidget(self.stats)
        self.tabs.addTab(w,"Interactive Decoder")

    def _make_fft_tab(self):
        w=QWidget(); l=QVBoxLayout(w); bar=QHBoxLayout()
        self.sample_rate=QLineEdit("2000000"); self.window_combo=QComboBox(); self.window_combo.addItems(["Hann","Hamming","Blackman","None"])
        self.scale_combo=QComboBox(); self.scale_combo.addItems(["dB","Linear","PSD"])
        self.main_freq=QLineEdit("650000")
        b=QPushButton("Update FFT"); b.clicked.connect(self.update_fft)
        for label,widget in (("Sample rate Hz",self.sample_rate),("Window",self.window_combo),("Scale",self.scale_combo),("Main Hz",self.main_freq)):
            bar.addWidget(QLabel(label)); bar.addWidget(widget)
        bar.addWidget(b); l.addLayout(bar)
        self.fft_plot=pg.PlotWidget(); self.fft_plot.showGrid(x=True,y=True,alpha=.25); l.addWidget(self.fft_plot,1)
        self.band_table=QTableWidget(0,3); self.band_table.setHorizontalHeaderLabels(["Band","Range (Hz)","Energy"]); self.band_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); l.addWidget(self.band_table)
        self.tabs.addTab(w,"FFT / Frequency Analyzer")

    def _make_structure_tab(self):
        w=QWidget(); l=QVBoxLayout(w)
        self.candidate_table=QTableWidget(0,10); self.candidate_table.setHorizontalHeaderLabels(["Rank","Type","Offset","Count","Score","Finite","Non-zero","Non-negative","Dynamic","Smooth"])
        self.candidate_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.candidate_table.itemDoubleClicked.connect(self._candidate_double_clicked); l.addWidget(self.candidate_table,2)
        self.structure_text=QTextEdit(); self.structure_text.setReadOnly(True); l.addWidget(self.structure_text,1)
        self.tabs.addTab(w,"Structure / Candidate Ranking")

    def _make_correlation_tab(self):
        w=QWidget(); l=QVBoxLayout(w); bar=QHBoxLayout()
        self.telemetry_file=QLineEdit(); b1=QPushButton("Select telemetry CSV/TXT"); b1.clicked.connect(self.choose_telemetry)
        self.telemetry_column=QLineEdit("score"); self.max_lag=QSpinBox(); self.max_lag.setRange(0,10000); self.max_lag.setValue(500)
        b2=QPushButton("Correlate current candidate"); b2.clicked.connect(self.correlate)
        bar.addWidget(self.telemetry_file,1); bar.addWidget(b1); bar.addWidget(QLabel("Column")); bar.addWidget(self.telemetry_column); bar.addWidget(QLabel("Max lag")); bar.addWidget(self.max_lag); bar.addWidget(b2); l.addLayout(bar)
        self.corr_plot=pg.PlotWidget(); self.corr_plot.showGrid(x=True,y=True,alpha=.25); l.addWidget(self.corr_plot,1)
        self.corr_result=QLabel("Select a telemetry file or generated telemetry_summary.csv"); l.addWidget(self.corr_result)
        self.tabs.addTab(w,"Score / Time Correlation")

    def _make_cavitation_tab(self):
        w=QWidget(); l=QVBoxLayout(w)
        bar=QHBoxLayout()
        self.cav_sonication=QSpinBox(); self.cav_sonication.setRange(1,999); self.cav_sonication.setValue(5)
        run=QPushButton("Analyze Cavitation Timeline"); run.clicked.connect(self.analyze_cavitation_timeline)
        export=QPushButton("Export Timeline"); export.clicked.connect(self.export_cavitation_timeline)
        bar.addWidget(QLabel("Sonication")); bar.addWidget(self.cav_sonication); bar.addWidget(run); bar.addWidget(export); bar.addStretch(); l.addLayout(bar)
        self.cav_plot=pg.PlotWidget(); self.cav_plot.showGrid(x=True,y=True,alpha=.25); self.cav_plot.setLabel("bottom","Common elapsed time",units="s"); self.cav_plot.setLabel("left","Power / Score",units="%")
        self.cav_plot.addLegend(); l.addWidget(self.cav_plot,1)
        self.cav_events=QTableWidget(0,4); self.cav_events.setHorizontalHeaderLabels(["Time (s)","Category","Source","Message"]); self.cav_events.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch); l.addWidget(self.cav_events,1)
        self.cav_findings=QTextEdit(); self.cav_findings.setReadOnly(True); self.cav_findings.setMaximumHeight(120); l.addWidget(self.cav_findings)
        self.cav_timeline=None
        self.tabs.addTab(w,"Cavitation Event Timeline")

    def analyze_cavitation_timeline(self):
        if not self.root:
            QMessageBox.information(self,"No source","Open or drop a source first."); return
        try:
            timeline=CavitationTimelineAnalyzer().analyze(self.root,self.cav_sonication.value())
            self.cav_timeline=timeline
            self.cav_plot.clear(); self.cav_plot.addLegend()
            t=np.asarray(timeline.time_s,float); p=np.asarray(timeline.power_percent,float); score=np.asarray(timeline.score_percent,float)
            self.cav_plot.plot(t,p,pen=pg.mkPen(width=2.5),name="Power %",connect="finite")
            self.cav_plot.plot(t,score,pen=pg.mkPen(width=2.5),name="Score %",connect="finite")
            category_levels={"cavitation":95.0,"modulation":82.0,"stop":70.0,"safety":58.0}
            for event in timeline.events:
                level=category_levels.get(event.category,50.0)
                line=pg.InfiniteLine(pos=event.elapsed_s,angle=90,pen=pg.mkPen(style=Qt.DashLine)); line.setToolTip(f"{event.category}: {event.message}"); self.cav_plot.addItem(line)
                marker=pg.ScatterPlotItem([event.elapsed_s],[level],size=8,name=None); marker.setToolTip(event.message); self.cav_plot.addItem(marker)
            self.cav_events.setRowCount(len(timeline.events))
            for r,event in enumerate(timeline.events):
                for c,value in enumerate((f"{event.elapsed_s:.3f}",event.category,event.source,event.message)):
                    self.cav_events.setItem(r,c,QTableWidgetItem(str(value)))
            self.cav_findings.setPlainText("\n".join(timeline.findings))
            self.statusBar().showMessage(f"Sonication {timeline.sonication_number}: common timeline {timeline.duration_s:.3f}s, {len(timeline.events)} events")
        except Exception as exc:
            QMessageBox.warning(self,"Timeline analysis error",str(exc))

    def export_cavitation_timeline(self):
        if self.cav_timeline is None:
            QMessageBox.information(self,"No timeline","Analyze a sonication first."); return
        folder=QFileDialog.getExistingDirectory(self,"Select timeline export folder")
        if not folder: return
        CavitationTimelineAnalyzer.export(self.cav_timeline,Path(folder))
        self.statusBar().showMessage(f"Timeline exported to {folder}")

    def _make_report_tab(self):
        w=QWidget(); l=QVBoxLayout(w); self.report_text=QTextEdit(); self.report_text.setReadOnly(True); l.addWidget(self.report_text); self.tabs.addTab(w,"Evidence Report")

    def dragEnterEvent(self,e:QDragEnterEvent):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self,e:QDropEvent):
        urls=e.mimeData().urls()
        if urls: self.load_source(Path(urls[0].toLocalFile()))

    def choose_source(self):
        p=QFileDialog.getExistingDirectory(self,"Select extracted ANx or Sonication folder")
        if not p:
            p,_=QFileDialog.getOpenFileName(self,"Select ZIP or hydrophone file","","Supported (*.zip *.dmp *.txt *.log);;All files (*)")
        if p: self.load_source(Path(p))

    def load_source(self,path:Path):
        try:
            if self.temp_dir: shutil.rmtree(self.temp_dir,ignore_errors=True); self.temp_dir=None
            if path.suffix.lower()==".zip":
                self.temp_dir=Path(tempfile.mkdtemp(prefix="hre_lab_"));
                with zipfile.ZipFile(path) as z: z.extractall(self.temp_dir)
                self.root=self.temp_dir
            else: self.root=path if path.is_dir() else path.parent
            self.path_edit.setText(str(path)); self.populate_tree(path if path.is_file() and path.suffix.lower()!='.zip' else self.root)
            self.statusBar().showMessage(f"Loaded {path}")
        except Exception as exc: QMessageBox.critical(self,"Load error",str(exc))

    def populate_tree(self,root:Path):
        self.tree.clear(); files=[root] if root.is_file() else [p for p in root.rglob('*') if p.is_file() and (p.suffix.lower() in {'.dmp','.txt','.log','.ini'})]
        files=sorted(files,key=lambda p:str(p).lower())
        nodes={}
        for p in files:
            low=p.name.lower()
            if not any(k in low for k in ('spectrummsg','acquisition','reflection','cavitation','brain','.ini')): continue
            family='SpectrumMsg' if 'spectrummsg' in low else 'Acquisition' if 'acquisition' in low else 'Reflection' if 'reflection' in low else 'Cavitation' if 'cavitation' in low else 'Configuration'
            parent=nodes.get(family)
            if parent is None: parent=QTreeWidgetItem([family,""]); self.tree.addTopLevelItem(parent); nodes[family]=parent
            item=QTreeWidgetItem([p.name,f"{p.stat().st_size:,}"]); item.setData(0,Qt.UserRole,str(p)); parent.addChild(item)
        self.tree.expandAll()

    def _tree_selected(self):
        items=self.tree.selectedItems();
        if not items: return
        p=items[0].data(0,Qt.UserRole)
        if not p: return
        path=Path(p); self.current_file=path
        if path.suffix.lower()=='.dmp': self.profile_file(path)
        else: self.current_profile=None; self.hex_view.setPlainText(path.read_text(errors='replace')[:200000])

    def profile_file(self,path:Path):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.current_profile=self.probe.profile(path); self.hex_offset.setMaximum(max(0,path.stat().st_size-1)); self.decode_offset.setMaximum(max(0,path.stat().st_size-1)); self.refresh_hex(); self.show_candidates();
            if self.current_profile.numeric_candidates:
                c=self.current_profile.numeric_candidates[0]; self._apply_candidate(c)
            self.structure_text.setPlainText(json.dumps(self.current_profile.to_dict(),indent=2,ensure_ascii=False))
        finally: QApplication.restoreOverrideCursor()

    def refresh_hex(self):
        if not self.current_file: return
        start=self.hex_offset.value(); data=self.current_file.read_bytes()[start:start+self.hex_length.value()]
        lines=[]
        for i in range(0,len(data),16):
            chunk=data[i:i+16]; hs=' '.join(f'{x:02X}' for x in chunk); asc=''.join(chr(x) if 32<=x<127 else '.' for x in chunk)
            lines.append(f'{start+i:08X}  {hs:<47}  {asc}')
        self.hex_view.setPlainText('\n'.join(lines))

    def show_candidates(self):
        cs=self.current_profile.numeric_candidates if self.current_profile else []; self.candidate_table.setRowCount(len(cs))
        for r,c in enumerate(cs):
            vals=[r+1,c.dtype,c.offset,c.count,c.score,c.finite_ratio,c.nonzero_ratio,c.nonnegative_ratio,c.dynamic_ratio,c.smoothness]
            for col,v in enumerate(vals): self.candidate_table.setItem(r,col,QTableWidgetItem(str(v)))

    def _candidate_double_clicked(self,item):
        if self.current_profile: self._apply_candidate(self.current_profile.numeric_candidates[item.row()]); self.tabs.setCurrentIndex(1)

    def _apply_candidate(self,c:NumericCandidate):
        label=next((k for k,v in NUMPY_DTYPES.items() if v==c.dtype),None)
        if label: self.dtype_combo.setCurrentText(label)
        self.decode_offset.setValue(c.offset); self.decode_count.setValue(c.count); self.decode_current()

    def decode_current(self):
        if not self.current_file: return
        dtype=np.dtype(NUMPY_DTYPES[self.dtype_combo.currentText()]); offset=self.decode_offset.value(); count=self.decode_count.value()
        try:
            data=self.current_file.read_bytes(); usable=max(0,(len(data)-offset)//dtype.itemsize); count=min(count,usable)
            arr=np.frombuffer(data,dtype=dtype,count=count,offset=offset).astype(float)
            arr=np.nan_to_num(arr,nan=0,posinf=0,neginf=0)
            if self.remove_dc.isChecked() and arr.size: arr=arr-np.mean(arr)
            self.current_values=arr; self.decode_plot.clear(); self.decode_plot.plot(arr)
            self.stats.setText(f"n={arr.size:,}  min={arr.min() if arr.size else 0:.6g}  max={arr.max() if arr.size else 0:.6g}  mean={arr.mean() if arr.size else 0:.6g}  std={arr.std() if arr.size else 0:.6g}")
            self.update_fft()
        except Exception as exc: QMessageBox.warning(self,"Decode error",str(exc))

    def update_fft(self):
        x=self.current_values
        if x.size<2: return
        try: fs=float(self.sample_rate.text()); main=float(self.main_freq.text())
        except ValueError: return
        win=self.window_combo.currentText(); w=np.ones(x.size) if win=='None' else np.hanning(x.size) if win=='Hann' else np.hamming(x.size) if win=='Hamming' else np.blackman(x.size)
        spec=np.fft.rfft(x*w); freq=np.fft.rfftfreq(x.size,1/fs); power=np.abs(spec)**2/max(1,x.size)
        scale=self.scale_combo.currentText(); y=10*np.log10(np.maximum(power,1e-30)) if scale=='dB' else power/fs if scale=='PSD' else np.sqrt(power)
        self.fft_plot.clear(); self.fft_plot.plot(freq,y)
        for f in (main/2,main,main*1.5,main*2):
            if 0<=f<=freq[-1]: self.fft_plot.addItem(pg.InfiniteLine(pos=f,angle=90,pen=pg.mkPen(style=Qt.DashLine)))
        bands=[('Subharmonic',(0.45*main,0.55*main)),('Main',(0.9*main,1.1*main)),('Ultraharmonic',(1.4*main,1.6*main)),('Broadband',(0.2*main,2.2*main))]
        self.band_table.setRowCount(len(bands))
        for r,(name,(lo,hi)) in enumerate(bands):
            mask=(freq>=lo)&(freq<=hi); energy=float(np.trapz(power[mask],freq[mask])) if np.count_nonzero(mask)>1 else 0.0
            for c,v in enumerate((name,f'{lo:.0f}–{hi:.0f}',f'{energy:.6g}')): self.band_table.setItem(r,c,QTableWidgetItem(v))

    def analyze_all(self):
        if not self.root: QMessageBox.information(self,"No source","Open or drop a source first."); return
        self.progress.show(); self.progress.setValue(0); self.worker=AnalyzeWorker(self.root); self.worker.progress.connect(lambda p,s:(self.progress.setValue(p),self.statusBar().showMessage(s))); self.worker.completed.connect(self._analysis_done); self.worker.failed.connect(self._analysis_failed); self.worker.start()

    def _analysis_done(self,report,out):
        self.report=report; self.progress.hide(); self.report_text.setPlainText(json.dumps(report.to_dict(),indent=2,ensure_ascii=False)); self.tabs.setCurrentWidget(self.report_text.parentWidget()); self.statusBar().showMessage(f"Report written to {out}")
        generated=Path(out)/'telemetry_summary.csv'
        if generated.exists(): self.telemetry_file.setText(str(generated))

    def _analysis_failed(self,msg): self.progress.hide(); QMessageBox.critical(self,"Analysis failed",msg)

    def choose_telemetry(self):
        p,_=QFileDialog.getOpenFileName(self,"Select telemetry","","CSV/TXT/LOG (*.csv *.txt *.log);;All files (*)")
        if p: self.telemetry_file.setText(p)

    def _read_numeric_column(self,path:Path,needle:str)->np.ndarray:
        if path.suffix.lower()=='.csv':
            with path.open(encoding='utf-8-sig',errors='replace') as f:
                rows=list(csv.DictReader(f)); keys=rows[0].keys() if rows else []
                key=next((k for k in keys if needle.lower() in k.lower()),None)
                if not key: raise ValueError(f"Column containing '{needle}' not found")
                vals=[]
                for row in rows:
                    try: vals.append(float(row[key]))
                    except (ValueError,TypeError): pass
                return np.asarray(vals)
        text=path.read_text(errors='replace'); vals=[]
        import re
        rx=re.compile(rf'{re.escape(needle)}[^-+0-9]*([-+]?\d+(?:\.\d+)?)',re.I)
        for m in rx.finditer(text): vals.append(float(m.group(1)))
        return np.asarray(vals)

    def correlate(self):
        if self.current_values.size<4: QMessageBox.information(self,"No candidate","Decode a candidate first."); return
        try:
            y=self._read_numeric_column(Path(self.telemetry_file.text()),self.telemetry_column.text())
            x=np.abs(self.current_values); n=min(len(x),len(y));
            if n<4: raise ValueError("Not enough overlapping samples")
            x=np.interp(np.linspace(0,len(x)-1,n),np.arange(len(x)),x); y=y[:n]
            x=(x-x.mean())/(x.std() or 1); y=(y-y.mean())/(y.std() or 1)
            maxlag=min(self.max_lag.value(),n-2); lags=np.arange(-maxlag,maxlag+1); corrs=[]
            for lag in lags:
                a=x[-lag:] if lag<0 else x[:n-lag] if lag>0 else x
                b=y[:n+lag] if lag<0 else y[lag:] if lag>0 else y
                corrs.append(float(np.mean(a*b)))
            corrs=np.asarray(corrs); idx=int(np.argmax(np.abs(corrs))); self.corr_plot.clear(); self.corr_plot.plot(lags,corrs); self.corr_result.setText(f"Best Pearson-like normalized correlation: {corrs[idx]:.5f} at lag {lags[idx]} samples (n={n})")
        except Exception as exc: QMessageBox.warning(self,"Correlation error",str(exc))

    def export_session(self):
        if not self.current_file: QMessageBox.information(self,"Nothing to export","Select and decode a file first."); return
        folder=QFileDialog.getExistingDirectory(self,"Select export folder")
        if not folder: return
        out=Path(folder); out.mkdir(parents=True,exist_ok=True)
        np.savetxt(out/'decoded_candidate.csv',self.current_values,delimiter=',',header='value',comments='')
        config={'source':str(self.current_file),'dtype':NUMPY_DTYPES[self.dtype_combo.currentText()],'offset':self.decode_offset.value(),'count':self.decode_count.value(),'sample_rate_hz':self.sample_rate.text(),'main_frequency_hz':self.main_freq.text()}
        (out/'decoder_configuration.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
        self.decode_plot.grab().save(str(out/'waveform.png')); self.fft_plot.grab().save(str(out/'fft.png'))
        QMessageBox.information(self,"Export complete",str(out))


def run_lab() -> int:
    import sys
    app=QApplication.instance() or QApplication(sys.argv); app.setApplicationName("Hydrophone Reverse Engineering Lab"); app.setStyleSheet(DARK_STYLESHEET)
    win=HydrophoneLabWindow(); win.show(); return app.exec()
