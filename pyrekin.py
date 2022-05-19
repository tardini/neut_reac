#!/usr/bin/env python

__author__  = 'Giovanni Tardini (Tel. 1898)'
__version__ = '0.0.1'
__date__    = '29.03.2022'

import os, sys, logging, webbrowser

try:
    from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication, QGridLayout, QMenu, QAction, QLabel, QPushButton, QLineEdit, QCheckBox, QFileDialog, QRadioButton, QButtonGroup, QTabWidget, QVBoxLayout, QComboBox
    from PyQt5.QtGui import QPixmap, QIcon
    from PyQt5.QtCore import Qt, QRect, QSize
    qt5 = True
except:
    from PyQt4.QtCore import Qt, QRect, QSize
    from PyQt4.QtGui import QPixmap, QIcon, QMainWindow, QWidget, QApplication, QGridLayout, QMenu, QAction, QLabel, QPushButton, QLineEdit, QCheckBox, QFileDialog, QRadioButton, QButtonGroup, QTabWidget, QVBoxLayout, QComboBox
    qt5 = False

import numpy as np
import matplotlib.pylab as plt
from mpl_toolkits.mplot3d import Axes3D
import dixm
from reactivities import *
import constants as con
import calc_cross_section as cs
import calc_kinematics as ck
import calc_spectrum as spc
import plot_rekin
from reactions import reaction


xml = dixm.DIX()

os.environ['BROWSER'] = '/usr/bin/firefox'

fmt = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s: %(message)s', '%H:%M:%S')
hnd = logging.StreamHandler()
hnd.setFormatter(fmt)
logger = logging.getLogger('rekin')
logger.addHandler(hnd)
logger.setLevel(logging.DEBUG)

rekin_dir = os.path.dirname(os.path.realpath(__file__))


class REKIN(QMainWindow):


    def __init__(self):

        if sys.version_info[0] == 3:
            super().__init__()
        else:
            super(QMainWindow, self).__init__()

        xwin  = 643
        yhead = 44
        yline = 30
        ybar  = 48
        ywin  = 15*yline + yhead + ybar

        qhead  = QWidget(self)
        qbar   = QWidget(self)
        qtabs  = QTabWidget(self)
        qhead.setGeometry(QRect(0,     0, xwin, yhead))
        qbar.setGeometry(QRect(0, yhead, xwin, ybar))
        qtabs.setGeometry(QRect(0, yhead+ybar, xwin, ywin-yhead-ybar))
        qtabs.setStyleSheet("QTabBar::tab { width: 160 }")
        header_grid = QGridLayout(qhead) 
        tbar_grid   = QGridLayout(qbar) 

#-----
# Tabs
#-----

        qreac = QWidget()
        reac_layout = QGridLayout()
        qreac.setLayout(reac_layout)
        qtabs.addTab(qreac, 'Reactivities')

        qcross = QWidget()
        cross_layout = QGridLayout()
        qcross.setLayout(cross_layout)
        qtabs.addTab(qcross, 'Cross-sections')

        qkin = QWidget()
        kin_layout = QGridLayout()
        qkin.setLayout(kin_layout)
        qtabs.addTab(qkin, 'Scattering kinematics')

        qspec = QWidget()
        spec_layout = QGridLayout()
        qspec.setLayout(spec_layout)
        qtabs.addTab(qspec, 'Neutron spectra')

#--------
# Menubar
#--------

        menubar = self.menuBar()
        fileMenu = QMenu('&File', self)
        xmlMenu  = QMenu('&Setup', self)
        helpMenu = QMenu('&Help', self)
        menubar.addMenu(fileMenu)
        menubar.addMenu(xmlMenu)
        menubar.addMenu(helpMenu)

        fmap = {'reac': self.reactivity, 'csec': self.cross_section, 'kine': self.scatt_kine, \
            'spec': self.spectra, 'exit': sys.exit}
        qlbl = {'reac': '&Reactivity', 'csec': '&Cross-section', 'kine': '&Kinematics', \
            'spec': '&Spectra', 'exit': 'Exit'}
        Action = {}
        for key, lbl in qlbl.items():
            Action = QAction(lbl, fileMenu)
            Action.triggered.connect(fmap[key])
            if key == 'exit':
                fileMenu.addSeparator()
            fileMenu.addAction(Action)

        loadAction  = QAction('&Load Setup', xmlMenu)
        saveAction  = QAction('&Save Setup', xmlMenu)
        xmlMenu.addAction(loadAction)
        xmlMenu.addAction(saveAction)
        loadAction.triggered.connect(self.load_xml)
        saveAction.triggered.connect(self.save_xml)

        aboutAction = QAction('&Web docu', helpMenu)
        aboutAction.triggered.connect(self.about)
        helpMenu.addAction(aboutAction)

        header_grid.addWidget(menubar, 0, 0, 1, 10)

# Icons
        dum_lbl  = QLabel(200*' ')
        for jpos, key in enumerate(qlbl.keys()):
            but = QPushButton()
            but.setIcon(QIcon('%s/%s.gif' %(rekin_dir, key)))
            but.setIconSize(QSize(ybar, ybar))
            but.clicked.connect(fmap[key])
            tbar_grid.addWidget(but, 0, jpos)

        tbar_grid.addWidget(dum_lbl, 0, jpos+1, 1, 10)

# User options

        self.setup_init = xml.xml2dict('%s/xml/default.xml' %rekin_dir)['main']
        self.gui = {}
        for node in self.setup_init.keys():
            self.gui[node] = {}
        user = os.getenv('USER')

#------------
# Reactivity
#------------

        cb = ['ddn3he', 'ddpt', 'dt', 'd3he']
        self.new_tab(reac_layout, 'reac', checkbuts=cb)

#---------------
# Cross-sections
#---------------

        entries = ['E', 'Z1', 'Z2']
        cb = ['log_scale']
        combos = {'reac': reaction.keys()}
        self.new_tab(cross_layout, 'cross', entries=entries, checkbuts=cb, combos=combos)

#-----------
# Kinematics
#-----------

        entries = ['v1x', 'v1y', 'v1z', 'v2x', 'v2y', 'v2z', 'losx', 'losy', 'losz']
        combos = {'reac': reaction.keys()}
        self.new_tab(kin_layout, 'kinematics', entries=entries, combos=combos, lbl_wid=40, ent_wid=80)

#--------
# Spectra
#--------

        entries = ['dens', 'E1', 'E2', 'losx', 'losy', 'losz', 'n_sample']
        combos = {'reac': reaction.keys()}
        self.new_tab(spec_layout, 'spectrum', entries=entries, combos=combos)

#-----------
# GUI layout
#-----------

        self.setStyleSheet("QLabel { width: 4 }")
        self.setStyleSheet("QLineEdit { width: 4 }")
        self.setGeometry(10, 10, xwin, ywin)
        self.setWindowTitle('ReKin')
        self.show()


    def about(self):

        webbrowser.open('https://www.aug.ipp.mpg.de/~git/rekin/index.html')


    def new_tab(self, layout, node, entries=[], checkbuts=[], combos={}, lbl_wid=140, ent_wid=180):
# Checkbutton

        jrow = 0

        for key in checkbuts:
            if key in reaction.keys():
                lbl = reaction[key].label
            else:
                lbl = key
            self.gui[node][key] = QCheckBox(lbl)
            layout.addWidget(self.gui[node][key], jrow, 0, 1, 2)
            if self.setup_init[node][key].lower().strip() == 'true':
                self.gui[node][key].setChecked(True)
            jrow += 1

        for key in entries:
            val = self.setup_init[node][key]
            if key in reaction.keys():
                lbl = reaction[key].label
            else:
                lbl = key
            qlbl = QLabel(lbl)
            qlbl.setFixedWidth(lbl_wid)
            self.gui[node][key] = QLineEdit(val)
            self.gui[node][key].setFixedWidth(ent_wid)
            layout.addWidget(qlbl         , jrow, 0)
            layout.addWidget(self.gui[node][key], jrow, 1)
            jrow += 1

        for key, combs in combos.items():
            self.gui[node][key] = QComboBox()
            for comb in combs:
                self.gui[node][key].addItem(comb.strip())
            index = self.gui[node][key].findText(self.setup_init[node][key].strip())
            self.gui[node][key].setCurrentIndex(index)
            layout.addWidget(self.gui[node][key], jrow, 0, 1, 2)
            jrow += 1

        layout.setRowStretch(layout.rowCount(), 1)
        layout.setColumnStretch(layout.columnCount(), 1)


    def get_gui(self, node):

        rekin_dic = {}
        for key, val in self.gui[node].items():
            if isinstance(val, QLineEdit):
                rekin_dic[key] = val.text()
            elif isinstance(val, QCheckBox):
                rekin_dic[key] = val.isChecked()
            elif isinstance(val, QComboBox):
                rekin_dic[key] = val.itemText(val.currentIndex())

        return rekin_dic


    def set_gui(self, xml_d):

        for node, val1 in xml_d.items():
            for key, val in val1.items():
                val = val.strip()
                val_low = val.lower()
                widget = self.gui[node][key]
                if isinstance(widget, QCheckBox):
                    if val_low == 'false':
                        widget.setChecked(False)
                    elif val_low == 'true':
                        widget.setChecked(True)
                elif isinstance(widget, QButtonGroup):
                    for but in widget.buttons():
                        if but.text().lower() == val_low:
                            but.setChecked(True)
                elif isinstance(widget, QLineEdit):
                    if val_low == '':
                        widget.setText(' ')
                    else:
                        widget.setText(val)
                elif isinstance(widget, QComboBox):
                    for index in range(widget.count()):
                        if widget.itemText(index).strip() == val.strip():
                            widget.setCurrentIndex(index)
                            break


    def load_xml(self):

        ftmp = QFileDialog.getOpenFileName(self, 'Open file', \
            '%s/xml' %rekin_dir, "xml files (*.xml)")
        if qt5:
            fxml = ftmp[0]
        else:
            fxml = str(ftmp)
        setup_d = xml.xml2dict(fxml)
        self.set_gui(setup_d['main'])


    def save_xml(self):

        out_dic = {'main': {}}
        for node in self.gui.keys():
            out_dic['main'][node] = self.get_gui(node)
        ftmp = QFileDialog.getSaveFileName(self, 'Save file', \
            '%s/xml' %rekin_dir, "xml files (*.xml)")
        if qt5:
            fxml = ftmp[0]
        else:
            fxml = str(ftmp)
        xml.dict2xml(out_dic, fxml)


    def reactivity(self):

        rekin_dic = self.get_gui('reac')

        Ti_keV = np.linspace(1., 60., 60)
        
        logger.info('Reactivities')

        reac_d = {}

        for key, reac in reaction.items():
            if hasattr(reac, 'coeff_reac') and rekin_dic[key]:
                reac_d[reac.label] = react(Ti_keV, key)

        self.wid = plot_rekin.plotWindow()
        fig_reac =  plot_rekin.fig_reactivity(reac_d, Ti_keV)       
        self.wid.addPlot('Reactivities', fig_reac)
        self.wid.show()


    def cross_section(self):

        rekin_dic = self.get_gui('cross')

        Egrid = np.array([float(x) for x in eval(rekin_dic['E'])], dtype=np.float32)
        logger.info('Cross-section')

        theta = np.linspace(0, np.pi, 61)
        mu_grid = np.cos(theta)
        reac_lbl = rekin_dic['reac'].lower().strip()
        sigma = cs.sigma_diff(Egrid, mu_grid, reac_lbl, 2, 2)

        self.wid = plot_rekin.plotWindow()
        fig_cross = plot_rekin.fig_cross(sigma, theta, Egrid, log_scale=rekin_dic['log_scale'])
        self.wid.addPlot('Cross-sections', fig_cross)
        self.wid.show()


    def scatt_kine(self):

        rekin_dic = self.get_gui('kinematics')

        logger.info('Scattering kinematics')
        reac_lbl = rekin_dic['reac'].lower().strip()
        v1 = [float(rekin_dic['v1x']), float(rekin_dic['v1y']), float(rekin_dic['v1z'])]
        v2 = [float(rekin_dic['v2x']), float(rekin_dic['v2y']), float(rekin_dic['v2z'])]
        versor_out = [float(rekin_dic['losx']), float(rekin_dic['losy']), float(rekin_dic['losz'])]
        kin = ck.calc_reac(v1, v2, versor_out, 'dt')

        self.wid = plot_rekin.plotWindow()
        fig_kine = plot_rekin.fig_scatt(kin)
        self.wid.addPlot('Scattering kinematics', fig_kine)
        self.wid.show()


    def spectra(self):

        rekin_dic = self.get_gui('spectrum')

        logger.info('Spectra')
        dens = float(rekin_dic['dens'])
        reac_lbl = rekin_dic['reac'].lower().strip()
        n_sample = int(rekin_dic['n_sample'])
        E1 = float(rekin_dic['E1'])
        E2 = float(rekin_dic['E2'])
        losx = float(rekin_dic['losx'])
        losy = float(rekin_dic['losy'])
        losz = float(rekin_dic['losz'])
        Earr, weight = spc.mono_iso(E1, E2, [losx, losy, losz], reac_lbl, n_sample=n_sample)
        Egrid, Espec = spc.calc_spectrum(dens, Earr, weight)

        self.wid = plot_rekin.plotWindow()
        fig_spec = plot_rekin.fig_spec(Egrid, Espec)
        self.wid.addPlot('Neutron Spectrum', fig_spec)
        self.wid.show()


if __name__ == '__main__':


    app = QApplication(sys.argv)
    main = REKIN()
    app.exec_()
