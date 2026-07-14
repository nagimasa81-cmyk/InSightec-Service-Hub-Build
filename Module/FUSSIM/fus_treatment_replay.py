import sys, re, gzip, zipfile, struct, math
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QTableWidget,QTableWidgetItem,QPushButton,QFileDialog,QLabel,QSplitter,QTabWidget,QHeaderView,QMessageBox
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure

@dataclass
class Sonication:
    no:int; time:str; x:float; y:float; roll:float; pitch:float; elevation:float
    fd:float; mode:int; duration:float; power:float; freq:float; max_power:float; avg_power:float; status:str

ROW_RE=re.compile(r"^\s*(\d+)\s*\|\s*([\d:]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*(\d+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*(\w+)")

def parse_summary(text):
    out=[]
    for line in text.replace('\r','').splitlines():
        m=ROW_RE.match(line)
        if m:
            g=m.groups(); out.append(Sonication(int(g[0]),g[1],*map(float,g[2:8]),int(g[8]),*map(float,g[9:14]),g[14]))
    return out

def time_seconds(s):
    h,m,sec=map(int,s.split(':')); return h*3600+m*60+sec

def spectrum_time(name):
    m=re.search(r'_(\d\d)_(\d\d)_(\d\d)_\d{4}',name)
    return int(m.group(1))*3600+int(m.group(2))*60+int(m.group(3)) if m else None

def decode_spectrum(blob):
    try: raw=gzip.decompress(blob)
    except Exception: raw=blob
    vals=[]
    for off in range(32, min(len(raw)-8, 500000), 8):
        v=struct.unpack_from('<d',raw,off)[0]
        if math.isfinite(v) and 1e-10 < abs(v) < 1e6: vals.append(abs(v))
    if len(vals)<128:
        a=np.frombuffer(raw[:len(raw)//4*4],dtype='<f4').astype(float)
        a=a[np.isfinite(a) & (np.abs(a)<1e6)]
        vals=np.abs(a).tolist()
    a=np.asarray(vals[:100000],float)
    if a.size<64: return None,None
    n=2048; idx=np.linspace(0,a.size-1,n).astype(int); y=a[idx]
    y=np.log10(y+np.percentile(y,5)+1e-12); y-=np.nanmin(y)
    if np.nanmax(y)>0:y/=np.nanmax(y)
    return np.linspace(0,1,n),y

class Plot(Canvas):
    def __init__(self):
        self.fig=Figure(figsize=(5,4),tight_layout=True); super().__init__(self.fig)

class Main(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('FUS Treatment Replay Prototype'); self.resize(1500,900)
        self.zf=None; self.sonics=[]; self.spectrum_files=[]; self.spec_cache={}
        w=QWidget(); self.setCentralWidget(w); lay=QVBoxLayout(w)
        top=QHBoxLayout(); lay.addLayout(top)
        b=QPushButton('Open Treatment ZIP'); b.clicked.connect(self.open_zip); top.addWidget(b)
        self.info=QLabel('No data loaded'); top.addWidget(self.info,1)
        badge=QLabel('SIMULATION / REVIEW ONLY — NOT FOR CLINICAL USE'); badge.setStyleSheet('font-weight:bold;color:#b00020'); top.addWidget(badge)
        split=QSplitter(); lay.addWidget(split,1)
        self.table=QTableWidget(0,8); self.table.setHorizontalHeaderLabels(['No.','Start','Duration','Power','Avg Power','Frequency','F.D.','Status'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.table.currentCellChanged.connect(self.select_row); split.addWidget(self.table)
        self.tabs=QTabWidget(); split.addWidget(self.tabs); split.setSizes([500,1000])
        self.imgplot=Plot(); self.tabs.addTab(self.imgplot,'MR / Hotspot Replay')
        self.cavplot=Plot(); self.tabs.addTab(self.cavplot,'Hydrophone Cavitation')
        self.specplot=Plot(); self.tabs.addTab(self.specplot,'Spectrum')
        self.timeline=Plot(); self.tabs.addTab(self.timeline,'Treatment Timeline')
        self.details=QLabel(); self.details.setTextInteractionFlags(Qt.TextSelectableByMouse); self.details.setAlignment(Qt.AlignTop); self.details.setMargin(12); self.tabs.addTab(self.details,'Sonication Details')
    def open_zip(self):
        p,_=QFileDialog.getOpenFileName(self,'Open FUS ZIP','','ZIP files (*.zip)')
        if p:self.load_zip(p)
    def load_zip(self,p):
        try:
            if self.zf:self.zf.close()
            self.zf=zipfile.ZipFile(p); names=self.zf.namelist()
            sums=[n for n in names if '/Summary_' in n and n.lower().endswith('.txt')]
            if not sums: raise ValueError('Treatment Summary file was not found')
            self.sonics=parse_summary(self.zf.read(sums[0]).decode('utf-8','ignore'))
            self.spectrum_files=[n for n in names if n.endswith('.dmp_FFT')]; self.spec_cache={}
            self.table.setRowCount(len(self.sonics))
            for r,s in enumerate(self.sonics):
                for c,v in enumerate([s.no,s.time,s.duration,s.power,s.avg_power,s.freq,s.fd,s.status]): self.table.setItem(r,c,QTableWidgetItem(str(v)))
            self.info.setText(f'{Path(p).name}  |  {len(self.sonics)} sonications  |  {len(self.spectrum_files)} spectrum files')
            self.draw_timeline()
            if self.sonics:self.table.selectRow(0)
        except Exception as e: QMessageBox.critical(self,'Load error',str(e))
    def select_row(self,row,col,pr,pc):
        if 0<=row<len(self.sonics):
            s=self.sonics[row]; self.draw_image(s); self.draw_cavitation(s); self.draw_spectrum(s); self.show_details(s)
    def draw_image(self,s):
        f=self.imgplot.fig; f.clear(); ax=f.add_subplot(111)
        n=320; y,x=np.mgrid[-1:1:complex(n),-1:1:complex(n)]
        if s.no<5:
            base=np.exp(-((x/.72)**2+(y/.72)**2)*2.2)+.22*np.exp(-((x+.25)**2+(y-.1)**2)/.03); title='Representative Phantom Image (simulated)'
        else:
            brain=np.exp(-((x/.78)**2+(y/.92)**2)*2.1); base=brain+.08*np.sin(18*x)*np.cos(14*y)*brain; title='Generic Axial MR-like Image (simulated; no patient MRI)'
        scale=np.clip((s.avg_power/1100)*(s.duration/40),.03,1); cx=.18*math.sin(s.no*.65); cy=.14*math.cos(s.no*.51)
        hot=np.exp(-(((x-cx)/(.055+.035*scale))**2+((y-cy)/(.075+.045*scale))**2)*2)
        ax.imshow(base,cmap='gray',origin='lower',extent=(-1,1,-1,1)); ax.imshow(np.ma.masked_where(hot<.08,hot*scale),cmap='hot',alpha=.72,origin='lower',extent=(-1,1,-1,1),vmin=0,vmax=1)
        ax.plot(cx,cy,'+',markersize=14,markeredgewidth=2); ax.set_title(f'{title}\nSonication {s.no} — hotspot overlay is simulated'); self.imgplot.draw()
    def draw_cavitation(self,s):
        f=self.cavplot.fig; f.clear(); ax=f.add_subplot(111); t=np.linspace(0,s.duration,500); rng=np.random.default_rng(8000+s.no); base=.08+.0007*s.avg_power
        for h in range(4):
            env=(1-np.exp(-t/max(.4,s.duration*.12)))*np.exp(-t/max(2,s.duration*2.4)); bursts=np.zeros_like(t)
            if s.avg_power>400:
                for _ in range(2+(s.no+h)%4):
                    c=rng.uniform(.25,.92)*s.duration; bursts+=(.08+.00018*s.avg_power)*np.exp(-((t-c)/(s.duration*.025+.08))**2)
            ax.plot(t,np.maximum(base*(.7+.12*h)*env+bursts+rng.normal(0,.018,len(t)),0),label=f'Hydrophone {h+1}')
        ax.set_title('Hydrophone Cavitation Trend (derived simulation)'); ax.set_xlabel('Time (s)'); ax.set_ylabel('Relative cavitation index'); ax.legend(); ax.grid(True,alpha=.25); self.cavplot.draw()
    def nearest_spectrum(self,s):
        target=time_seconds(s.time); a=[(abs(spectrum_time(n)-target),n) for n in self.spectrum_files if spectrum_time(n) is not None]
        return min(a)[1] if a else None
    def draw_spectrum(self,s):
        f=self.specplot.fig; f.clear(); ax=f.add_subplot(111); n=self.nearest_spectrum(s); x=y=None
        if n:
            if n not in self.spec_cache:self.spec_cache[n]=decode_spectrum(self.zf.read(n))
            x,y=self.spec_cache[n]
        if x is not None:
            ax.plot(x,y); ax.set_title(f'Actual proprietary FFT payload preview\n{Path(n).name}'); ax.set_xlabel('Relative frequency bin (uncalibrated)'); ax.set_ylabel('Normalized log magnitude')
        else:
            x=np.linspace(0,1,1500); y=.08*np.exp(-3*x)+.5*np.exp(-((x-.33)/.018)**2)+.2*np.exp(-((x-.66)/.025)**2); ax.plot(x,y); ax.set_title('Simulated spectrum — payload could not be decoded')
        ax.grid(True,alpha=.25); self.specplot.draw()
    def draw_timeline(self):
        f=self.timeline.fig; f.clear(); ax=f.add_subplot(111)
        if self.sonics:
            x=np.arange(len(self.sonics)); ax.plot(x,[s.avg_power for s in self.sonics],'o-'); ax.set_xlabel('Sonication No.'); ax.set_ylabel('Average power'); ax2=ax.twinx(); ax2.plot(x,[s.duration for s in self.sonics],'s--'); ax2.set_ylabel('Duration (s)'); ax.grid(True,alpha=.25); ax.set_title('Treatment Sonication Timeline')
        self.timeline.draw()
    def show_details(self,s):
        spec=self.nearest_spectrum(s)
        html=(f'<h2>Sonication {s.no}</h2><table cellpadding="5">'
              f'<tr><td>Start time</td><td>{s.time}</td></tr><tr><td>Status</td><td>{s.status}</td></tr>'
              f'<tr><td>Duration</td><td>{s.duration:.1f} s</td></tr><tr><td>Commanded power</td><td>{s.power:.1f}</td></tr>'
              f'<tr><td>Average / maximum power</td><td>{s.avg_power:.1f} / {s.max_power:.1f}</td></tr>'
              f'<tr><td>Frequency</td><td>{s.freq:.2f}</td></tr><tr><td>Focal distance</td><td>{s.fd:.1f}</td></tr>'
              f'<tr><td>Position</td><td>X {s.x:.1f}, Y {s.y:.1f}, Elevation {s.elevation:.1f}</td></tr>'
              f'<tr><td>Matched spectrum</td><td>{Path(spec).name if spec else "None"}</td></tr></table>'
              '<p><b>Data provenance:</b> parameters are parsed from the ZIP Treatment Summary. MR/phantom image, hotspot and hydrophone traces are simulations. Spectrum view is an uncalibrated preview extracted from the proprietary compressed FFT payload.</p>')
        self.details.setText(html)

if __name__=='__main__':
    app=QApplication(sys.argv); m=Main(); m.show()
    if len(sys.argv)>1 and Path(sys.argv[1]).exists():m.load_zip(sys.argv[1])
    sys.exit(app.exec())
