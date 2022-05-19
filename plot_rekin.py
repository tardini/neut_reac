import sys
import matplotlib
import numpy as np

try:
    from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout
    from PyQt5.QtCore import QRect
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
except:
    from PyQt4.QtGui import QWidget, QTabWidget, QVBoxLayout
    from PyQt4.QtCore import QRect
    matplotlib.use('Qt4Agg')
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar

import matplotlib.pylab as plt


fsize   = 8
titsize = 10
lblsize = 10
fig_size = (8.8, 5.9)
lwid = 2.5


class plotWindow(QWidget):


    def __init__(self):

        if sys.version_info[0] == 3:
            super().__init__()
        else:
            super(QWidget, self).__init__()
        self.setGeometry(QRect(80, 30, 900, 680))
        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("QTabBar::tab { width: 165 }")
        self.setWindowTitle('Reaction kinematics')


    def addPlot(self, title, figure):

        new_tab = QWidget()
        layout = QVBoxLayout()
        new_tab.setLayout(layout)

        new_canvas = FigureCanvas(figure)
        new_toolbar = NavigationToolbar(new_canvas, new_tab)
        layout.addWidget(new_canvas)
        layout.addWidget(new_toolbar)
        self.tabs.addTab(new_tab, title)


def fig_reactivity(reac_d, Ti_keV, color='#d0d0d0'):

    fig_reac = plt.figure('Reac', fig_size, dpi=100, facecolor=color)
    plt.cla()
    for lbl, reac in reac_d.items():
        plt.semilogy(Ti_keV, reac, label=lbl, linewidth=lwid)
    plt.xlim([Ti_keV[0], Ti_keV[-1]])
    plt.xlabel(r'T$_i$ [keV]')
    plt.ylabel(r'Reactivity [cm$^3$/s]')
    plt.grid()
    plt.legend(loc=4)

    return fig_reac


def fig_cross(reac, theta, Egrid, log_scale=False, color='#d0d0d0'):

    fig_cs = plt.figure('Cross-sections', fig_size, dpi=100, facecolor=color)
    plt.cla()
    the_deg = np.degrees(theta)
    for j, E in enumerate(Egrid):
        if log_scale:
            plt.semilogy(the_deg, reac[:, j], linewidth=lwid, label='E=%5.3f MeV' %E)
        else:
            plt.plot(the_deg, reac[:, j], linewidth=lwid, label='E=%5.3f MeV' %E)
    plt.xlim([the_deg[0], the_deg[-1]])
    plt.legend()
    plt.xlabel('Scattering angle [deg]')
    plt.ylabel(r'$\frac{d\sigma}{d\Omega}$ [mbarn]')

    return fig_cs


def fig_scatt(kin, color='#d0d0d0'):

    fig_sol = plt.figure('Solutions', fig_size, dpi=100, facecolor=color)
    plt.cla()
    ax_sol = fig_sol.add_subplot(projection='3d')
    plt.plot([0, kin.in1.qmom[1]], [0, kin.in1.qmom[2]], [0, kin.in1.qmom[3]], 'k-', linewidth=lwid, label='In1')
    plt.plot([0, kin.in2.qmom[1]], [0, kin.in2.qmom[2]], [0, kin.in2.qmom[3]], 'k--', linewidth=lwid, label='In2')
    if hasattr(kin.prod1, 'qmom_b'):
        plt.plot([0, kin.prod1.qmom_b[1]], [0, kin.prod1.qmom_b[2]], [0, kin.prod1.qmom_b[3]], 'b-', linewidth=lwid, label='out1_b')
        plt.plot([0, kin.prod2.qmom_b[1]], [0, kin.prod2.qmom_b[2]], [0, kin.prod2.qmom_b[3]], 'b--', linewidth=lwid, label='out2_b')
    plt.plot([0, kin.prod1.qmom_a[1]], [0, kin.prod1.qmom_a[2]], [0, kin.prod1.qmom_a[3]], 'r-', linewidth=lwid, label='out1_a')
    plt.plot([0, kin.prod2.qmom_a[1]], [0, kin.prod2.qmom_a[2]], [0, kin.prod2.qmom_a[3]], 'r--', linewidth=lwid, label='out2_a')
    plt.xlim([-200, 200])
    plt.ylim([-200, 200])
    plt.legend()

    return fig_sol


def fig_spec(Egrid, Espec, color='#d0d0d0'):

    fig_spc = plt.figure('Spectrum', fig_size, dpi=100, facecolor=color)
    plt.cla()
#    plt.semilogy(Egrid, Espec)
    plt.plot(Egrid, Espec, linewidth=lwid)
    plt.xlabel('En [MeV]')
    plt.ylabel('dN/dEn')

    return fig_spc
