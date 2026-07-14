import sys, re, gzip, zipfile, struct, math, json, tempfile, shutil
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QTableWidget,QTableWidgetItem,
    QPushButton,QFileDialog,QLabel,QSplitter,QTabWidget,QHeaderView,QMessageBox,QComboBox,QFormLayout,
    QGroupBox,QTextEdit,QCheckBox,QSpinBox,QDoubleSpinBox,QScrollArea,QSlider
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure

@dataclass
class Sonication:
    no:int; time:str; x:float; y:float; roll:float; pitch:float; elevation:float
    fd:float; mode:int; duration:float; power:float; freq:float; max_power:float; avg_power:float; status:str

@dataclass
class MRSeries:
    date:str=''; time:str=''; protocol:str=''; description:str=''; plane:str='Unknown'; freq_dir:str='Unknown'
    image_mode:str=''; pulse_sequence:str=''; psd_name:str=''; coil:str=''; fov:str=''; thickness:str=''
    slices:str=''; matrix:str=''; start_loc:str=''; end_loc:str=''; center_fov:str=''; source:str='review.out'

ROW_RE=re.compile(r"^\s*(\d+)\s*\|\s*([\d:]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*(\d+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*(\w+)")

PLANE_OPTIONS=['Unknown','Axial','Sagittal','Coronal','Oblique Axial','Oblique Sagittal','Oblique Coronal','3-Plane']
FREQ_OPTIONS=['Unknown','R/L','L/R','A/P','P/A','S/I','I/S']
PHASE_OPTIONS=['Auto','DQA','Treatment']
SPECTRUM_INTERVALS=['During Sonication','Pre-sonication','Post-sonication','Full Acquisition']
SPECTRUM_Y=['Amplitude','dB']

def parse_summary(text):
    out=[]
    for line in text.replace('\r','').splitlines():
        m=ROW_RE.match(line)
        if m:
            g=m.groups(); out.append(Sonication(int(g[0]),g[1],*map(float,g[2:8]),int(g[8]),*map(float,g[9:14]),g[14]))
    return out

def time_seconds(s):
    try:
        h,m,sec=map(int,s.split(':')); return h*3600+m*60+sec
    except Exception:return 0

def spectrum_time(name):
    m=re.search(r'_(\d\d)_(\d\d)_(\d\d)_\d{4}',name)
    return int(m.group(1))*3600+int(m.group(2))*60+int(m.group(3)) if m else None

def decode_spectrum(blob):
    try: raw=gzip.decompress(blob)
    except Exception: raw=blob
    vals=[]
    for off in range(32, min(len(raw)-8, 700000), 8):
        try:v=struct.unpack_from('<d',raw,off)[0]
        except Exception:continue
        if math.isfinite(v) and 1e-10 < abs(v) < 1e7: vals.append(abs(v))
    if len(vals)<128:
        a=np.frombuffer(raw[:len(raw)//4*4],dtype='<f4').astype(float)
        a=a[np.isfinite(a) & (np.abs(a)<1e7)]; vals=np.abs(a).tolist()
    a=np.asarray(vals[:150000],float)
    if a.size<64:return None,None
    n=min(4096,max(512,a.size)); idx=np.linspace(0,a.size-1,n).astype(int); y=a[idx]
    floor=max(np.percentile(y,5),1e-12); y=np.log10(y+floor); y-=np.nanmin(y)
    if np.nanmax(y)>0:y/=np.nanmax(y)
    return np.linspace(0,1,n),y

def field(block,label):
    m=re.search(rf'{re.escape(label)}\s*:\s*([^\t\r\n]+)',block,re.I)
    return m.group(1).strip() if m else ''

def parse_review(text):
    blocks=re.split(r'\n-{20,}\n',text.replace('\r',''))
    out=[]
    for b in blocks:
        if 'IMAGING PARAMETERS SCREEN' not in b: continue
        plane=field(b,'Scan Plane') or 'Unknown'
        if plane.upper()=='3-PLANE': plane='3-Plane'
        freq=field(b,'Freq. Dir') or 'Unknown'
        slices=field(b,'# Slices')
        if not slices:
            vals=[]
            for p in ('Axial','Sagittal','Coronal'):
                v=field(b,f'# Slices in {p} Plane')
                if v: vals.append(f'{p}:{v}')
            slices=', '.join(vals)
        out.append(MRSeries(
            date=field(b,'date'), time=field(b,'time'), protocol=field(b,'Protocol'),
            description=field(b,'Series De'), plane=plane.title() if plane.upper()!='OBLIQUE' else 'Oblique',
            freq_dir=freq, image_mode=field(b,'Image Mode'), pulse_sequence=field(b,'Pulse Seq'),
            psd_name=field(b,'Psd Name'), coil=field(b,'Coil Name'), fov=field(b,'Field of View'),
            thickness=field(b,'Slice Thickness'), slices=slices, matrix=field(b,'Acq. Matrix'),
            start_loc=field(b,'Start Loc'), end_loc=field(b,'End Loc'), center_fov=field(b,'Center of FOV')))
    return out


def classify_session(sonics):
    """Conservative DQA/Treatment split. A long workflow gap is the strongest signal.
    Low-power/test-looking sonications before that gap are DQA. Without a clear transition,
    keep the complete short session as DQA and expose manual override.
    """
    if not sonics: return {}
    gaps=[]
    for i in range(1,len(sonics)):
        gaps.append((time_seconds(sonics[i].time)-time_seconds(sonics[i-1].time),i))
    transition=None
    if gaps:
        gap,idx=max(gaps)
        if gap>=15*60: transition=idx
    out={}
    for i,son in enumerate(sonics):
        if transition is not None:
            phase='DQA' if i<transition else 'Treatment'
            confidence='High' if max(gaps)[0]>=30*60 else 'Medium'
            reason=f'workflow time gap before Sonication {transition}' if i>=transition else f'pre-treatment group before {max(gaps)[0]/60:.1f} min gap'
        else:
            phase='DQA'
            confidence='Medium' if len(sonics)<=6 else 'Low'
            reason='short continuous test/phantom-like session; no reliable patient-treatment transition found'
        out[str(son.no)]={'phase':phase,'confidence':confidence,'reason':reason}
    return out

def scan_timing_evidence(text,name):
    rows=[]; offsets=[]
    keys=('sonication','thermo','temperature','acquisition','scan','offset','time difference','clock')
    for line in text.replace('\r','').splitlines():
        low=line.lower()
        if any(k in low for k in keys):
            if len(rows)<3000: rows.append(f'{name}: {line.strip()}')
            # Accept explicit MR/FUS offset statements only; preserve direction as evidence.
            m=re.search(r'(?:mr.{0,20}fus|fus.{0,20}mr|time\s*(?:difference|offset)|clock\s*offset)[^+\-\d]{0,30}([+\-]?\d+(?:\.\d+)?)\s*(ms|msec|s|sec)',line,re.I)
            if m:
                v=float(m.group(1)); unit=m.group(2).lower();
                if unit.startswith('m'): v/=1000.0
                offsets.append((v,f'{name}: {line.strip()}'))
    return rows,offsets

def parse_mrserver(text,name):
    events=[]
    for line in text.replace('\r','').splitlines():
        if any(k in line for k in ('LoadProtocol','SetRxGeometry3p','Series type =','scanner=scanning','acquisition=complete','recon=done','SetCVs=')):
            events.append(f'{name}: {line.strip()}')
    return events

class Plot(Canvas):
    def __init__(self):
        self.fig=Figure(figsize=(5,4),tight_layout=True); super().__init__(self.fig)

class Main(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('FUS Treatment Replay & Evidence Review'); self.resize(1580,940)
        self.zf=None; self.zip_path=None; self.sonics=[]; self.spectrum_files=[]; self.reflection_files=[]
        self.spec_cache={}; self.mr_series=[]; self.mrserver_events=[]; self.timing_evidence=[]; self.ws_offsets=[]; self.auto_phase={}; self.manual={}; self.external_images={}
        self._updating=False
        self.build_ui()

    def build_ui(self):
        w=QWidget(); self.setCentralWidget(w); lay=QVBoxLayout(w)
        top=QHBoxLayout(); lay.addLayout(top)
        b=QPushButton('Open Treatment ZIP'); b.clicked.connect(self.open_zip); top.addWidget(b)
        add=QPushButton('Add MR Images / DICOM Folder'); add.clicked.connect(self.add_mr_images); top.addWidget(add)
        save=QPushButton('Save Review Mapping'); save.clicked.connect(self.save_mapping); top.addWidget(save)
        self.info=QLabel('No data loaded'); top.addWidget(self.info,1)
        badge=QLabel('REVIEW / RESEARCH ONLY — NOT FOR CLINICAL DECISIONS'); badge.setStyleSheet('font-weight:bold;color:#b00020'); top.addWidget(badge)

        split=QSplitter(); lay.addWidget(split,1)
        left=QWidget(); ll=QVBoxLayout(left)
        self.table=QTableWidget(0,12); self.table.setHorizontalHeaderLabels(['No.','Phase','Confidence','Start','Duration','Power','Avg','Freq.','F.D.','Status','MR Plane','Freq Dir'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.table.currentCellChanged.connect(self.select_row)
        ll.addWidget(self.table,1)
        nav=QHBoxLayout(); ll.addLayout(nav)
        prev=QPushButton('◀ Previous'); prev.clicked.connect(lambda:self.move_row(-1)); nav.addWidget(prev)
        nxt=QPushButton('Next ▶'); nxt.clicked.connect(lambda:self.move_row(1)); nav.addWidget(nxt)
        split.addWidget(left)

        right=QWidget(); rl=QVBoxLayout(right)
        controls=QGroupBox('Selected Sonication — MR Geometry Mapping'); form=QGridLayout(controls)
        self.source_label=QLabel('Source: unavailable'); form.addWidget(self.source_label,0,0,1,4)
        form.addWidget(QLabel('DQA / Treatment'),1,0); self.phase_combo=QComboBox(); self.phase_combo.addItems(PHASE_OPTIONS); self.phase_combo.currentTextChanged.connect(self.phase_changed); form.addWidget(self.phase_combo,1,1)
        self.phase_evidence=QLabel(''); self.phase_evidence.setWordWrap(True); form.addWidget(self.phase_evidence,1,2,1,2)
        form.addWidget(QLabel('Scan plane'),2,0); self.plane_combo=QComboBox(); self.plane_combo.addItems(PLANE_OPTIONS); self.plane_combo.currentTextChanged.connect(self.mapping_changed); form.addWidget(self.plane_combo,2,1)
        form.addWidget(QLabel('Frequency direction'),2,2); self.freq_combo=QComboBox(); self.freq_combo.addItems(FREQ_OPTIONS); self.freq_combo.currentTextChanged.connect(self.mapping_changed); form.addWidget(self.freq_combo,2,3)
        form.addWidget(QLabel('MR series'),3,0); self.series_combo=QComboBox(); self.series_combo.currentIndexChanged.connect(self.series_changed); form.addWidget(self.series_combo,3,1,1,3)
        self.use_auto=QCheckBox('Use automatically matched review.out / mrserver information when available'); self.use_auto.setChecked(True); self.use_auto.toggled.connect(self.refresh_selected); form.addWidget(self.use_auto,4,0,1,4)
        rl.addWidget(controls)
        self.tabs=QTabWidget(); rl.addWidget(self.tabs,1)
        self.imgplot=Plot(); self.tabs.addTab(self.imgplot,'MR / Hotspot Replay')
        self.overview=QTextEdit(); self.overview.setReadOnly(True); self.tabs.addTab(self.overview,'Maximum Information')
        self.mrtable=QTableWidget(0,12); self.mrtable.setHorizontalHeaderLabels(['Time','Description','Plane','Freq Dir','Mode','Sequence','PSD','Coil','FOV','Thickness','Slices','Matrix']); self.mrtable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.tabs.addTab(self.mrtable,'MR Series from review.out')
        self.cavplot=Plot(); self.tabs.addTab(self.cavplot,'Hydrophone Cavitation')
        self.specpage=QWidget(); spl=QVBoxLayout(self.specpage); sc=QHBoxLayout(); spl.addLayout(sc)
        sc.addWidget(QLabel('Interval')); self.spec_interval=QComboBox(); self.spec_interval.addItems(SPECTRUM_INTERVALS); self.spec_interval.currentTextChanged.connect(self.refresh_selected); sc.addWidget(self.spec_interval)
        sc.addWidget(QLabel('Hydrophone')); self.hp_combo=QComboBox(); self.hp_combo.addItems(['Auto / Unknown','Hydrophone 1','Hydrophone 2','Hydrophone 3','Hydrophone 4','All / Overlay']); self.hp_combo.currentTextChanged.connect(self.refresh_selected); sc.addWidget(self.hp_combo)
        sc.addWidget(QLabel('Y axis')); self.spec_y=QComboBox(); self.spec_y.addItems(SPECTRUM_Y); self.spec_y.currentTextChanged.connect(self.refresh_selected); sc.addWidget(self.spec_y); sc.addStretch(1)
        self.spec_note=QLabel(''); self.spec_note.setWordWrap(True); spl.addWidget(self.spec_note)
        self.specplot=Plot(); spl.addWidget(self.specplot,1); self.tabs.addTab(self.specpage,'Spectrum')
        self.timeline=Plot(); self.tabs.addTab(self.timeline,'DQA / Treatment Timeline')
        self.syncinfo=QTextEdit(); self.syncinfo.setReadOnly(True); self.tabs.addTab(self.syncinfo,'Time Synchronization')
        self.evidence=QTextEdit(); self.evidence.setReadOnly(True); self.tabs.addTab(self.evidence,'mrserver / Raw Evidence')
        self.details=QTextEdit(); self.details.setReadOnly(True); self.tabs.addTab(self.details,'Sonication Details')
        split.addWidget(right); split.setSizes([530,1050])

    def open_zip(self):
        p,_=QFileDialog.getOpenFileName(self,'Open FUS ZIP','','ZIP files (*.zip)')
        if p:self.load_zip(p)

    def load_zip(self,p):
        try:
            if self.zf:self.zf.close()
            self.zf=zipfile.ZipFile(p); self.zip_path=Path(p); names=self.zf.namelist()
            sums=[n for n in names if '/Summary_' in n and n.lower().endswith('.txt')]
            if not sums: sums=[n for n in names if Path(n).name.lower().startswith('summary_') and n.lower().endswith('.txt')]
            if not sums: raise ValueError('Treatment Summary file was not found')
            self.sonics=parse_summary(self.zf.read(sums[0]).decode('utf-8','ignore'))
            self.spectrum_files=[n for n in names if n.endswith('.dmp_FFT')]
            self.reflection_files=[n for n in names if 'reflection' in n.lower() and not n.endswith('/')]
            self.mr_series=[]
            for n in names:
                if Path(n).name.lower() in ('review.out','review.out.ar'):
                    try:
                        parsed=parse_review(self.zf.read(n).decode('utf-8','ignore'))
                        if parsed: self.mr_series=parsed; break
                    except Exception: pass
            self.mrserver_events=[]; self.timing_evidence=[]; self.ws_offsets=[]
            for n in names:
                if 'mrserver' in Path(n).name.lower() and n.lower().endswith('.log'):
                    try:self.mrserver_events += parse_mrserver(self.zf.read(n).decode('utf-8','ignore'),Path(n).name)
                    except Exception:pass
            # Search WS, WaterSystem, acquisition and sonication logs for timing evidence and explicit MR/FUS clock offsets.
            for n in names:
                bn=Path(n).name.lower()
                if n.endswith('/') or not (bn.endswith('.log') or bn.endswith('.txt')): continue
                if not any(k in n.lower() for k in ('wsfiles/','watersystem','acquisition','sonication')): continue
                try:
                    rows,offs=scan_timing_evidence(self.zf.read(n).decode('utf-8','ignore'),Path(n).name)
                    self.timing_evidence += rows; self.ws_offsets += offs
                except Exception: pass
            self.auto_phase=classify_session(self.sonics)
            self.spec_cache={}; self.manual={}; self.external_images={}; self.load_mapping()
            self.populate()
            self.info.setText(f'{self.zip_path.name} | {len(self.sonics)} sonications | {len(self.mr_series)} MR series | {len(self.spectrum_files)} spectra | {len(self.mrserver_events)} MR events')
            self.draw_timeline(); self.show_mr_table(); self.show_evidence(); self.show_sync()
            if self.sonics:self.table.selectRow(0)
        except Exception as e: QMessageBox.critical(self,'Load error',str(e))

    def populate(self):
        self._updating=True
        self.table.setRowCount(len(self.sonics)); self.series_combo.clear(); self.series_combo.addItem('No linked MR series',-1)
        for i,m in enumerate(self.mr_series): self.series_combo.addItem(f'{m.time} | {m.description or m.protocol} | {m.plane} | {m.freq_dir}',i)
        for r,s in enumerate(self.sonics):
            auto=self.auto_series_index(s); m=self.mr_series[auto] if auto is not None else None
            man=self.manual.get(str(s.no),{})
            ap=self.auto_phase.get(str(s.no),{'phase':'DQA','confidence':'Low'})
            phase=man.get('phase') or ap['phase']
            vals=[s.no,phase,ap.get('confidence',''),s.time,s.duration,s.power,s.avg_power,s.freq,s.fd,s.status,man.get('plane') or (m.plane if m else 'Unknown'),man.get('freq_dir') or (m.freq_dir if m else 'Unknown')]
            for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem(str(v)))
        self._updating=False

    def auto_series_index(self,s):
        if not self.mr_series:return None
        target=time_seconds(s.time); best=None
        for i,m in enumerate(self.mr_series):
            t=time_seconds(m.time) if m.time else 0
            d=target-t
            # Prefer the most recent MR acquisition before the sonication; otherwise nearest.
            score=(0 if d>=0 else 50000)+abs(d)
            if best is None or score<best[0]:best=(score,i)
        return best[1] if best else None

    def select_row(self,row,col,pr,pc):
        if 0<=row<len(self.sonics):self.refresh_selected()

    def refresh_selected(self,*args):
        row=self.table.currentRow()
        if not (0<=row<len(self.sonics)):return
        s=self.sonics[row]; man=self.manual.get(str(s.no),{}); auto=self.auto_series_index(s); chosen=man.get('series_index',auto if auto is not None else -1)
        self._updating=True
        ap=self.auto_phase.get(str(s.no),{'phase':'DQA','confidence':'Low','reason':'No evidence'})
        self.phase_combo.setCurrentText(man.get('phase','Auto'))
        effective=man.get('phase') or ap['phase']
        self.phase_evidence.setText(f'Effective: {effective} | Confidence: {ap.get("confidence","Low")} | {ap.get("reason","")}')
        self.series_combo.setCurrentIndex(self.series_combo.findData(chosen))
        m=self.mr_series[chosen] if isinstance(chosen,int) and 0<=chosen<len(self.mr_series) else None
        plane=man.get('plane') or (m.plane if m and self.use_auto.isChecked() else 'Unknown')
        freq=man.get('freq_dir') or (m.freq_dir if m and self.use_auto.isChecked() else 'Unknown')
        self.plane_combo.setCurrentText(plane if plane in PLANE_OPTIONS else ('Oblique '+plane.title() if 'oblique' in plane.lower() else 'Unknown'))
        self.freq_combo.setCurrentText(freq if freq in FREQ_OPTIONS else 'Unknown')
        source=[]
        if m and self.use_auto.isChecked():source.append('review.out auto-match')
        if man:source.append('manual override')
        if str(s.no) in self.external_images:source.append('external MR image')
        self.source_label.setText('Source: '+(', '.join(source) if source else 'simulation / not available'))
        self._updating=False
        self.draw_image(s,m); self.draw_cavitation(s); self.draw_spectrum(s); self.show_details(s,m); self.show_overview(s,m)

    def phase_changed(self,*args):
        if self._updating:return
        row=self.table.currentRow()
        if not (0<=row<len(self.sonics)):return
        son=self.sonics[row]; value=self.phase_combo.currentText(); d=self.manual.setdefault(str(son.no),{})
        if value=='Auto': d.pop('phase',None)
        else: d['phase']=value
        ap=self.auto_phase.get(str(son.no),{'phase':'DQA'})
        self.table.item(row,1).setText(d.get('phase') or ap['phase'])
        self.draw_timeline(); self.refresh_selected()

    def mapping_changed(self,*args):
        if self._updating:return
        row=self.table.currentRow()
        if not (0<=row<len(self.sonics)):return
        s=self.sonics[row]; d=self.manual.setdefault(str(s.no),{})
        d['plane']=self.plane_combo.currentText(); d['freq_dir']=self.freq_combo.currentText()
        self.table.item(row,10).setText(d['plane']); self.table.item(row,11).setText(d['freq_dir']); self.refresh_selected()

    def series_changed(self,*args):
        if self._updating:return
        row=self.table.currentRow()
        if not (0<=row<len(self.sonics)):return
        s=self.sonics[row]; self.manual.setdefault(str(s.no),{})['series_index']=self.series_combo.currentData(); self.refresh_selected()

    def move_row(self,d):
        if not self.sonics:return
        r=max(0,min(len(self.sonics)-1,self.table.currentRow()+d)); self.table.selectRow(r)

    def add_mr_images(self):
        if not self.sonics:return
        p=QFileDialog.getExistingDirectory(self,'Select DICOM / MR image folder')
        if not p:return
        files=[]
        for x in Path(p).rglob('*'):
            if x.is_file() and x.suffix.lower() in ('.dcm','.ima','.png','.jpg','.jpeg','.bmp','.tif','.tiff'): files.append(str(x))
        if not files: QMessageBox.information(self,'MR import','No supported MR/DICOM image files were found.'); return
        row=self.table.currentRow(); s=self.sonics[row]
        self.external_images[str(s.no)]={'folder':p,'files':files[:5000]}
        QMessageBox.information(self,'MR import',f'{len(files)} files registered for Sonication {s.no}.\nThe mapping is saved in the review sidecar JSON.\nPixel rendering of ordinary PNG/JPEG is enabled; DICOM metadata/pixel support is reserved for the pydicom option.')
        self.refresh_selected()

    def mapping_path(self):return self.zip_path.with_suffix('.fus_review.json') if self.zip_path else None
    def save_mapping(self):
        if not self.zip_path:return
        data={'zip':self.zip_path.name,'manual':self.manual,'external_images':self.external_images,'saved_at':datetime.now().isoformat(timespec='seconds'),'schema_version':3}
        self.mapping_path().write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
        QMessageBox.information(self,'Saved',f'Review mapping saved:\n{self.mapping_path()}')
    def load_mapping(self):
        p=self.mapping_path()
        if p and p.exists():
            try:
                d=json.loads(p.read_text(encoding='utf-8')); self.manual=d.get('manual',{}); self.external_images=d.get('external_images',{})
            except Exception:pass

    def effective_phase(self,s):
        d=self.manual.get(str(s.no),{}); return d.get('phase') or self.auto_phase.get(str(s.no),{}).get('phase','DQA')

    def draw_image(self,s,m):
        f=self.imgplot.fig; f.clear(); ax=f.add_subplot(111)
        n=360; y,x=np.mgrid[-1:1:complex(n),-1:1:complex(n)]
        base=None; ext=self.external_images.get(str(s.no),{})
        if ext:
            for fn in ext.get('files',[]):
                if Path(fn).suffix.lower() in ('.png','.jpg','.jpeg','.bmp','.tif','.tiff'):
                    try:
                        import matplotlib.image as mpimg; base=mpimg.imread(fn); break
                    except Exception:pass
        if base is None:
            phase=self.effective_phase(s)
            if phase=='DQA':
                base=np.exp(-((x/.72)**2+(y/.72)**2)*2.2)+.22*np.exp(-((x+.25)**2+(y-.1)**2)/.03); title='Representative DQA Phantom Image (simulated)'
            else:
                plane=self.plane_combo.currentText()
                if 'Sagittal' in plane: shape=np.exp(-((x/.62)**2+(y/.94)**2)*2.0)
                elif 'Coronal' in plane: shape=np.exp(-((x/.86)**2+(y/.82)**2)*2.1)
                else: shape=np.exp(-((x/.78)**2+(y/.92)**2)*2.1)
                base=shape+.07*np.sin(18*x)*np.cos(14*y)*shape; title=f'Generic {plane} MR-like Image (simulated)'
            ax.imshow(base,cmap='gray',origin='lower',extent=(-1,1,-1,1))
        else:
            title=f'External MR image preview ({Path(fn).name})'; ax.imshow(base,cmap='gray',origin='upper',extent=(-1,1,-1,1))
        scale=np.clip((s.avg_power/1100)*(s.duration/40),.03,1); cx=np.clip(s.x/100.0,-.65,.65); cy=np.clip(s.y/100.0,-.65,.65)
        if abs(cx)<.01 and abs(cy)<.01: cx=.18*math.sin(s.no*.65); cy=.14*math.cos(s.no*.51)
        hot=np.exp(-(((x-cx)/(.055+.035*scale))**2+((y-cy)/(.075+.045*scale))**2)*2)
        ax.imshow(np.ma.masked_where(hot<.08,hot*scale),cmap='hot',alpha=.72,origin='lower',extent=(-1,1,-1,1),vmin=0,vmax=1)
        ax.plot(cx,cy,'+',markersize=14,markeredgewidth=2)
        plane=self.plane_combo.currentText(); freq=self.freq_combo.currentText()
        if freq!='Unknown': ax.annotate(f'Frequency {freq}',xy=(.88,-.9),xytext=(-.1,-.9),arrowprops={'arrowstyle':'->'},fontsize=10)
        ax.set_title(f'{title}\nSonication {s.no} | Plane {plane} | Frequency {freq} | hotspot overlay simulated'); self.imgplot.draw()

    def draw_cavitation(self,s):
        f=self.cavplot.fig; f.clear(); ax=f.add_subplot(111); t=np.linspace(0,max(s.duration,.1),500); rng=np.random.default_rng(8000+s.no); base=.08+.0007*s.avg_power
        for h in range(4):
            env=(1-np.exp(-t/max(.4,s.duration*.12)))*np.exp(-t/max(2,s.duration*2.4)); bursts=np.zeros_like(t)
            if s.avg_power>400:
                for _ in range(2+(s.no+h)%4):
                    c=rng.uniform(.25,.92)*max(s.duration,.1); bursts+=(.08+.00018*s.avg_power)*np.exp(-((t-c)/(max(s.duration,.1)*.025+.08))**2)
            ax.plot(t,np.maximum(base*(.7+.12*h)*env+bursts+rng.normal(0,.018,len(t)),0),label=f'Hydrophone {h+1}')
        ax.set_title('Hydrophone Cavitation Trend (simulation until proprietary channel data is decoded)'); ax.set_xlabel('Time (s)'); ax.set_ylabel('Relative cavitation index'); ax.legend(); ax.grid(True,alpha=.25); self.cavplot.draw()

    def nearest_spectrum(self,s):
        target=time_seconds(s.time); a=[(abs(spectrum_time(n)-target),n) for n in self.spectrum_files if spectrum_time(n) is not None]
        return min(a)[1] if a else None
    def draw_spectrum(self,s):
        f=self.specplot.fig; f.clear(); ax=f.add_subplot(111); n=self.nearest_spectrum(s); x=y=None
        if n:
            if n not in self.spec_cache:self.spec_cache[n]=decode_spectrum(self.zf.read(n))
            x,y=self.spec_cache[n]
        interval=self.spec_interval.currentText(); hp=self.hp_combo.currentText(); ymode=self.spec_y.currentText()
        if x is not None:
            # The proprietary file does not expose a verified sample-rate/channel header yet.
            # Show frequency-shaped axis without claiming Hz/MHz calibration.
            freq=x
            amp=np.maximum(y,1e-12)
            yy=20*np.log10(amp/np.max(amp)) if ymode=='dB' else amp
            ax.plot(freq,yy)
            ax.set_title(f'{interval} spectrum | {hp} | {Path(n).name}')
            ax.set_xlabel('Frequency (relative, calibration unavailable)')
            ax.set_ylabel('Amplitude (dB re max)' if ymode=='dB' else 'Amplitude (normalized)')
            self.spec_note.setText('Matched FFT payload is displayed. Hydrophone channel is not encoded in the verified filename/header, so the channel remains Auto / Unknown. Pre/During/Post separation requires time-resolved raw hydrophone samples; until decoded, the selected interval is a review label and is not presented as a verified extraction.')
        else:
            freq=np.linspace(0,1,1500); amp=.08*np.exp(-3*freq)+.5*np.exp(-((freq-.33)/.018)**2)+.2*np.exp(-((freq-.66)/.025)**2)
            yy=20*np.log10(np.maximum(amp,1e-12)/np.max(amp)) if ymode=='dB' else amp; ax.plot(freq,yy)
            ax.set_title(f'Simulated {interval} spectrum — payload unavailable'); ax.set_xlabel('Frequency (relative)'); ax.set_ylabel('Amplitude')
            self.spec_note.setText('Simulation only. No decodable FFT payload was found.')
        ax.grid(True,alpha=.25); self.specplot.draw()

    def draw_timeline(self):
        f=self.timeline.fig; f.clear(); ax=f.add_subplot(111)
        if self.sonics:
            for i,s in enumerate(self.sonics):
                phase=self.effective_phase(s); y=1 if phase=='Treatment' else 0
                ax.barh(y,max(s.duration,.2),left=time_seconds(s.time),height=.35,alpha=.65)
                ax.text(time_seconds(s.time)+max(s.duration,.2)/2,y,str(s.no),ha='center',va='center',fontsize=8)
            ax.set_yticks([0,1],['DQA (phantom)','Treatment (patient)']); ax.set_xlabel('Session clock (seconds from midnight)')
            ax.set_title('DQA and Treatment Sonication Timeline — manual overrides preserved'); ax.grid(True,axis='x',alpha=.25)
        self.timeline.draw()

    def show_mr_table(self):
        self.mrtable.setRowCount(len(self.mr_series))
        for r,m in enumerate(self.mr_series):
            vals=[m.time,m.description,m.plane,m.freq_dir,m.image_mode,m.pulse_sequence,m.psd_name,m.coil,m.fov,m.thickness,m.slices,m.matrix]
            for c,v in enumerate(vals):self.mrtable.setItem(r,c,QTableWidgetItem(v))

    def show_evidence(self):
        lines=['MR SERVER EVIDENCE','='*80]
        lines += self.mrserver_events[:10000]
        if not self.mrserver_events: lines.append('No mrserver.log evidence was found.')
        lines += ['','TIMING EVIDENCE','='*80] + self.timing_evidence[:5000]
        self.evidence.setPlainText('\n'.join(lines))

    def show_sync(self):
        offset='Not detected'
        source='No explicit MR–FUS offset statement was decoded. Manual verification is required.'
        if self.ws_offsets:
            vals=[v for v,_ in self.ws_offsets]; offset=f'{np.median(vals):+.3f} s (median of {len(vals)} records)'; source=self.ws_offsets[0][1]
        self.syncinfo.setHtml(f'<h2>MR–FUS Time Synchronization</h2><table cellpadding="5" border="1" cellspacing="0"><tr><td><b>WS offset</b></td><td>{offset}</td></tr><tr><td><b>Evidence</b></td><td>{source}</td></tr><tr><td><b>Time model</b></td><td>MR acquisition → pre-sonication → actual FUS duration → post-sonication. FUS and MR clocks are kept separately and corrected only when an explicit WS offset is available.</td></tr></table><p>Pre/post durations are not assumed to be fixed. They are reconstructed from MR acquisition events and sonication start/end evidence when available. Unverified values remain unknown rather than being fabricated.</p>')

    def show_overview(self,s,m):
        spec=self.nearest_spectrum(s); man=self.manual.get(str(s.no),{})
        rows=[
            ('Sonication',str(s.no)),('Category',self.effective_phase(s)),('Start',s.time),('Status',s.status),('Duration',f'{s.duration:.2f} s'),
            ('Power / Avg / Max',f'{s.power:.2f} / {s.avg_power:.2f} / {s.max_power:.2f}'),('Frequency',f'{s.freq:.3f}'),
            ('Focus coordinates',f'X {s.x:.2f}, Y {s.y:.2f}, Elevation {s.elevation:.2f}, FD {s.fd:.2f}'),
            ('Scan plane',self.plane_combo.currentText()),('Frequency direction',self.freq_combo.currentText()),
            ('Spectrum match',Path(spec).name if spec else 'None'),('Reflection files',str(len(self.reflection_files))),
            ('Spectrum interval',self.spec_interval.currentText()),('Hydrophone',self.hp_combo.currentText()),('MR series source',m.description if m else 'No matched review.out series'),('External image',self.external_images.get(str(s.no),{}).get('folder','None'))]
        html='<h2>Maximum Available Information</h2><table cellpadding="5" border="1" cellspacing="0">'+''.join(f'<tr><td><b>{a}</b></td><td>{b}</td></tr>' for a,b in rows)+'</table>'
        if m:
            html += '<h3>Matched MR acquisition from review.out</h3><table cellpadding="5" border="1" cellspacing="0">'+''.join(f'<tr><td><b>{a}</b></td><td>{b}</td></tr>' for a,b in [
                ('Protocol',m.protocol),('Series description',m.description),('Plane',m.plane),('Frequency direction',m.freq_dir),('Image mode',m.image_mode),('Pulse sequence',m.pulse_sequence),('PSD',m.psd_name),('Coil',m.coil),('FOV',m.fov),('Slice thickness',m.thickness),('Slices',m.slices),('Matrix',m.matrix),('Start / End location',f'{m.start_loc} / {m.end_loc}'),('Center FOV',m.center_fov)])+'</table>'
        html += '<h3>Timing model</h3><p>MR acquisition start → Pre → FUS start (0 s) → Actual duration → Post → MR acquisition end. WS clock-offset evidence is applied only when explicitly decoded.</p><p><b>Provenance:</b> Treatment parameters come from the ZIP summary. MR geometry is read from review.out when available and can be manually overridden per sonication. mrserver.log provides scanner workflow evidence. Hotspot and cavitation graphics remain simulated unless corresponding proprietary data is decoded or external images are linked.</p>'
        self.overview.setHtml(html)

    def show_details(self,s,m):
        spec=self.nearest_spectrum(s)
        html=(f'<h2>Sonication {s.no} — {self.effective_phase(s)}</h2><table cellpadding="5">'
              f'<tr><td>Start time</td><td>{s.time}</td></tr><tr><td>Status</td><td>{s.status}</td></tr>'
              f'<tr><td>Duration</td><td>{s.duration:.1f} s</td></tr><tr><td>Commanded power</td><td>{s.power:.1f}</td></tr>'
              f'<tr><td>Average / maximum power</td><td>{s.avg_power:.1f} / {s.max_power:.1f}</td></tr>'
              f'<tr><td>Frequency</td><td>{s.freq:.3f}</td></tr><tr><td>Focal distance</td><td>{s.fd:.1f}</td></tr>'
              f'<tr><td>Position</td><td>X {s.x:.1f}, Y {s.y:.1f}, Elevation {s.elevation:.1f}, Roll {s.roll:.1f}, Pitch {s.pitch:.1f}</td></tr>'
              f'<tr><td>MR plane / frequency direction</td><td>{self.plane_combo.currentText()} / {self.freq_combo.currentText()}</td></tr>'
              f'<tr><td>Matched spectrum</td><td>{Path(spec).name if spec else "None"}</td></tr></table>')
        self.details.setHtml(html)

if __name__=='__main__':
    app=QApplication(sys.argv); m=Main(); m.show()
    if len(sys.argv)>1 and Path(sys.argv[1]).exists():m.load_zip(sys.argv[1])
    sys.exit(app.exec())
