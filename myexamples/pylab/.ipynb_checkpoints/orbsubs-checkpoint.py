
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage.filters import median_filter
from numpy import linalg as LA
#from matplotlib import rc
#rc('text', usetex=True)
from numpy import polyfit
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from math import fmod
from scipy.signal import medfilt
from scipy.spatial.transform import Rotation as R


from kepcart import *
from outils import * # useful short routines

angfac = 180.0/np.pi # for converting radians to degrees
twopi = np.pi*2.0

# read in an extended mass output file format fileroot_ext.txt
def readresfile(fileroot,ibody):
    filename = fileroot+'_ext'
    if (ibody > 0):
        filename = filename + '_{:0d}'.format(ibody)
    filename = filename + '.txt'
    print(filename)
    t,x,y,z,vx,vy,vz,omx,omy,omz,llx,lly,llz,Ixx,Iyy,Izz,Ixy,Iyz,Ixz,KErot,\
        PEspr,PEgrav,Etot,dEdtnow =\
        np.loadtxt(filename, skiprows=1, unpack='true')
    return t,x,y,z,vx,vy,vz,omx,omy,omz,llx,lly,llz,Ixx,Iyy,Izz,Ixy,Iyz,Ixz,\
        KErot,PEspr,PEgrav,Etot,dEdtnow

# Take I matrix of previous + current timestep
# Find Eigenvalues of both (I = SAS^-1, I' = S'AS'^-1)
# return rotation matrix to get from prev -> current
def rotCalc(current, prev):
    #Find eigenvectors of each I matrix
    EvalCurr, EvecCurr = np.linalg.eig(current)
    EvalPrev, EvecPrev = np.linalg.eig(prev)
    #Product of S'^-1 and S -> R
    rot = np.matmul(np.linalg.inv(EvecPrev), EvecCurr)
    new = np.matmul(np.linalg.inv(rot),np.matmul(prev, rot))
#     np.set_printoptions(suppress=True)
#     print("Difference in Calc\n", (current - new))
#     np.set_printoptions(suppress=False)
    return rot
    
    

# read in numerical simulation output for two resolved bodies
# return spins, orbital elements and obliquities
# uses routines: crossprod_unit, dotprod, readresfile, keplerian
def read_two_bodies(simdir,froot,GM):
    fileroot=simdir+froot
    # format for ext files
    # t x y z vx vy vz omx omy omz llx lly llz Ixx Iyy Izz Ixy Iyz Ixz
    # KErot PEspr PEgrav Etot dEdtnow dEdtave

    # read in first resolved body
    t1  ,x1,y1,z1,vx1,vy1,vz1,omx1,omy1,omz1,\
        llx1,lly1,llz1,Ixx,Iyy,Izz,Ixy,Iyz,Ixz,KErot,PEspr,PEgrav,\
        Etot,dEdtnow = readresfile(fileroot,1)
    # read in second resolved body
    t2  ,x2,y2,z2,vx2,vy2,vz2,omx2,omy2,omz2,\
        llx2,lly2,llz2,Ixx,Iyy,Izz,Ixy,Iyz,Ixz,KErot,PEspr,PEgrav,\
        Etot,dEdtnow = readresfile(fileroot,2)

    # Timesteps
    ns = min(len(t1),len(t2))
    tarr = t2[0:ns]
    # relative positions and velocities
    dx = x2[0:ns]-x1[0:ns]; dvx = vx2[0:ns]-vx1[0:ns];
    dy = y2[0:ns]-y1[0:ns]; dvy = vy2[0:ns]-vy1[0:ns];
    dz = z2[0:ns]-z1[0:ns]; dvz = vz2[0:ns]-vz1[0:ns];

    # compute the orbital elements + rotation matricies
    aaarr = np.zeros(ns); eearr = np.zeros(ns); iiarr = np.zeros(ns)
    lnarr = np.zeros(ns); ararr = np.zeros(ns); maarr = np.zeros(ns)
    rotMx = np.zeros((ns, 3,3)); r_change = np.zeros(ns); r_value = np.zeros(ns)
    for k in range(ns):
        aa,ee,ii,longnode,argperi,meananom=\
               keplerian(GM,dx[k],dy[k],dz[k],dvx[k],dvy[k],dvz[k])
        aaarr[k] = aa
        eearr[k] = ee
        iiarr[k] = ii
        lnarr[k] = longnode
        ararr[k] = argperi
        maarr[k] = meananom
        
        currI = np.array([[Ixx[k],Ixy[k],Ixz[k]],[Ixy[k],Iyy[k],Iyz[k]],[Ixz[k],Iyz[k],Izz[k]]])
        prevI = np.array([[Ixx[k-1],Ixy[k-1],Ixz[k-1]],[Ixy[k-1],Iyy[k-1],Iyz[k-1]],[Ixz[k-1],Iyz[k-1],Izz[k-1]]])
        rotMx[k] = np.zeros((3,3)) if k == 0 else rotCalc(currI, prevI)
        r = R.from_matrix(rotMx[k])
        r_prev = R.from_matrix(rotMx[k-1])
#         print(r.as_euler('zyx', degrees=True))
        r_change[k] = r.as_euler('zyx', degrees=True)[0] 
        r_value[k] = 0 if k == 0 else (r_value[k-1] + r_change[k])% 360.
     
    print(np.average(r_value))
     
        
    # total spin values
    om1 = np.sqrt(omx1[0:ns]**2 + omy1[0:ns]**2 + omz1[0:ns]**2)
    om2 = np.sqrt(omx2[0:ns]**2 + omy2[0:ns]**2 + omz2[0:ns]**2)

    # total angular momentums
    ll1 = np.sqrt(llx1[0:ns]**2 + lly1[0:ns]**2 + llz1[0:ns]**2)
    ll2 = np.sqrt(llx2[0:ns]**2 + lly2[0:ns]**2 + llz2[0:ns]**2)
    
    # compute orbit normal
    no_x,no_y,no_z=crossprod_unit(dx,dy,dz,dvx,dvy,dvz)
    # angular momentum unit vectors
    nlx1 = llx1[0:ns]/ll1; nly1 = lly1[0:ns]/ll1; nlz1 = llz1[0:ns]/ll1;
    nlx2 = llx2[0:ns]/ll2; nly2 = lly2[0:ns]/ll2; nlz2 = llz2[0:ns]/ll2;
    # compute obliquities
    ang_so1 = dotprod(nlx1,nly1,nlz1,no_x,no_y,no_z)
    ang_so1 = np.arccos(ang_so1)*angfac # obliquity body 1 in degrees
    ang_so2 = dotprod(nlx2,nly2,nlz2,no_x,no_y,no_z)
    ang_so2 = np.arccos(ang_so2)*angfac # obliquity body 2 in degrees
    obliquity_deg1 = ang_so1
    obliquity_deg2 = ang_so2
    
    #compute mean motion of binary
    meanmotion = np.sqrt(GM)/aaarr**1.5


    
    return tarr,aaarr,eearr,iiarr,lnarr,ararr,maarr,om1,om2,\
        obliquity_deg1,obliquity_deg2,meanmotion, rotMx, r_change, r_value
    
    
