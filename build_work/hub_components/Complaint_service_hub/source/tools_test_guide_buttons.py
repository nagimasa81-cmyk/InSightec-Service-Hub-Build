from __future__ import annotations
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QMessageBox
from common_guide.manager import GuideManager, GuideViewer

class Dummy(QWidget):
    def __init__(self):
        super().__init__()
        self.lang_cb=QPushButton('language',self)
        self.status=QLabel(self)
        self.nav_buttons=[('complaint',QPushButton('complaint',self))]
        self.opened=[]
    def open_tool(self,key): self.opened.append(key)

def main():
    app=QApplication.instance() or QApplication([])
    host=Dummy(); host.resize(800,600); host.show()
    manager=GuideManager(host,Path(__file__).resolve().parent,'ja')
    viewer=GuideViewer(manager,manager.steps,host)
    assert viewer.previous.isEnabled() is False
    viewer.go_next(); assert viewer.index==1
    viewer.go_previous(); assert viewer.index==0
    viewer.jump_to_target()
    viewer.skip_guide(); assert viewer.result()==viewer.Rejected
    viewer=GuideViewer(manager,manager.steps,host)
    viewer.index=len(viewer.steps)-1; viewer.render_step()
    old_exec=QMessageBox.exec
    QMessageBox.exec=lambda self: 0
    try: viewer.go_next()
    finally: QMessageBox.exec=old_exec
    assert manager.settings.get('last_completed_guide_version')
    print('GUIDE_BUTTON_TESTS_OK')

if __name__=='__main__': main()
