# ----------------------------------------------------------------------------------------------------------------------
# Licensing Information: You are free to use or extend these projects for
# education or reserach purposes provided that you provide clear attribution to UC Berkeley,
# including a reference to the papers describing the control framework:
# [1] Ugo Rosolia and Francesco Borrelli. "Learning Model Predictive Control for Iterative Tasks. A Data-Driven
#     Control Framework." In IEEE Transactions on Automatic Control (2017).
#
# [2] Ugo Rosolia and Francesco Borrelli "Learning how to autonomously race a car: a predictive control approach" 
#     In 2017 IEEE Conference on Decision and Control (CDC)
#
# [3] Ugo Rosolia and Francesco Borrelli. "Learning Model Predictive Control for Iterative Tasks: A Computationally
#     IEEE Transactions on Control Systems Technology (2019).
#
# Attibution Information: Code developed by Ugo Rosolia
# (for clarifiactions and suggestions please write to ugo.rosolia@berkeley.edu).
#
# Code description: Simulation of the Learning Model Predictive Controller (LMPC). The main file runs:
# 1) A PID path following controller
# 2) A MPC which uses a LTI model identified from the data collected with the PID in 1)
# 3) A MPC which uses a LTV model identified from the date collected in 1)
# 4) A LMPC for racing where the safe set and value function approximation are build using the data from 1), 2) and 3)
# ----------------------------------------------------------------------------------------------------------------------

import sys
sys.path.append('fnc')
from SysModel import Simulator, PID
from Classes import ClosedLoopData, LMPCprediction
from PathFollowingLTVMPC import PathFollowingLTV_MPC
from PathFollowingLTIMPC import PathFollowingLTI_MPC
from Track import Map, unityTestChangeOfCoordinates
from LMPC import ControllerLMPC
from Utilities import Regression
from plot import plotTrajectory, plotClosedLoopLMPC, animation_xy, animation_states, saveGif_xyResults, Save_statesAnimation
import numpy as np
import matplotlib.pyplot as plt
import pdb
import pickle

# ======================================================================================================================
# ============================ Choose which controller to run ==========================================================
# ======================================================================================================================
#Select '1' for "Run..." variables if running for the first time on a given track and/or changing the track. Changing the track can be
#done from "Track.py" file. The data is being stored hence we can use "plot...." variables as "1" for plotting the data.
#We don't have to perform computations again for plotting. Just change "1" to "0" for "Run..." variables for the same track.
#The Track is L-shaped by default 
RunPID     = 1; plotFlag       = 1
RunMPC     = 1; plotFlagMPC    = 1
RunMPC_tv  = 1; plotFlagMPC_tv = 1
RunLMPC    = 1; plotFlagLMPC   = 1; animation_xyFlag = 0; animation_stateFlag = 0

# ======================================================================================================================
# ============================ Initialize parameters for path following ================================================
# ======================================================================================================================
dt         = 1.0/10.0        # Controller discretization time
Time       = 100             # Simulation time for PID
TimeMPC    = 100             # Simulation time for path following MPC
TimeMPC_tv = 100             # Simulation time for path following LTV-MPC
vt         = 0.8             # Reference velocity for path following controllers
v0         = 0.5             # Initial velocity at lap 0
N          = 12              # Horizon length
n = 6;   d = 2               # State and Input dimension

# Path Following tuning
Q = np.diag([1.0, 1.0, 1, 1, 0.0, 100.0]) # vx, vy, wz, epsi, s, ey
R = np.diag([1.0, 10.0])                  # delta, a

map = Map(0.4)                            # Initialize the map
simulator = Simulator(map)                # Initialize the Simulator

# ======================================================================================================================
# ==================================== Initialize parameters for LMPC ==================================================
# ======================================================================================================================

# Safe Set Parameters
LMPC_Solver = "CVX"           # Can pick CVX for cvxopt or OSQP. For OSQP uncomment line 14 in LMPC.py
numSS_it = 4                  # Number of trajectories used at each iteration to build the safe set
numSS_Points = 40             # Number of points to select from each trajectory to build the safe set

Laps       = 46+numSS_it      # Total LMPC laps (50 laps)
TimeLMPC   = 400              # Simulation time

# Tuning Parameters
Qslack  = 20 * np.diag([10, 1, 1, 1, 10, 1])            # Cost on the slack variable for the terminal constraint
Qlane   =  1 * np.array([0, 10])                        # Quadratic and linear slack lane cost
Q_LMPC  =  0 * np.diag([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # State cost x = [vx, vy, wz, epsi, s, ey]
R_LMPC  =  0 * np.diag([1.0, 1.0])                      # Input cost u = [delta, a]
dR_LMPC = 10 * np.array([1.0, 10.0])                    # Input rate cost u

inputConstr = np.array([[0.5, 0.5],                     # Min Steering and Max Steering
                        [10.0, 10.0]])                    # Min Acceleration and Max Acceleration

# Initialize LMPC simulator
LMPCSimulator = Simulator(map, 1, 1)

# ======================================================================================================================
# ======================================= PID path following ===========================================================
# ======================================================================================================================
print("Starting PID")
if RunPID == 1:
    ClosedLoopDataPID = ClosedLoopData(dt, Time , v0)
    PIDController = PID(vt)
    simulator.Sim(ClosedLoopDataPID, PIDController)

    file_data = open(sys.path[0]+'\data\ClosedLoopDataPID.obj', 'wb')
    pickle.dump(ClosedLoopDataPID, file_data)
    file_data.close()
else:
    file_data = open(sys.path[0]+'\data\ClosedLoopDataPID.obj', 'rb')
    ClosedLoopDataPID = pickle.load(file_data)
    file_data.close()
print("===== PID terminated")

# ======================================================================================================================
# ======================================  LINEAR REGRESSION ============================================================
# ======================================================================================================================
print("Starting MPC")
lamb = 0.0000001
A, B, Error = Regression(ClosedLoopDataPID.x, ClosedLoopDataPID.u, lamb)

if RunMPC == 1:
    ClosedLoopDataLTI_MPC = ClosedLoopData(dt, TimeMPC, v0)
    Controller_PathFollowingLTI_MPC = PathFollowingLTI_MPC(A, B, Q, R, N, vt, inputConstr)
    simulator.Sim(ClosedLoopDataLTI_MPC, Controller_PathFollowingLTI_MPC)

    file_data = open(sys.path[0]+'\data\ClosedLoopDataLTI_MPC.obj', 'wb')
    pickle.dump(ClosedLoopDataLTI_MPC, file_data)
    file_data.close()
else:
    file_data = open(sys.path[0]+'\data\ClosedLoopDataLTI_MPC.obj', 'rb')
    ClosedLoopDataLTI_MPC = pickle.load(file_data)
    file_data.close()
print("===== MPC terminated")

# ======================================================================================================================
# ===================================  LOCAL LINEAR REGRESSION =========================================================
# ======================================================================================================================
print("Starting TV-MPC")
if RunMPC_tv == 1:
    ClosedLoopDataLTV_MPC = ClosedLoopData(dt, TimeMPC_tv, v0)
    Controller_PathFollowingLTV_MPC = PathFollowingLTV_MPC(Q, R, N, vt, n, d, ClosedLoopDataPID.x, ClosedLoopDataPID.u, dt, map, inputConstr)
    simulator.Sim(ClosedLoopDataLTV_MPC, Controller_PathFollowingLTV_MPC)

    file_data = open(sys.path[0]+'data\ClosedLoopDataLTV_MPC.obj', 'wb')
    pickle.dump(ClosedLoopDataLTV_MPC, file_data)
    file_data.close()
else:
    file_data = open(sys.path[0]+'\data\ClosedLoopDataLTV_MPC.obj', 'rb')
    ClosedLoopDataLTV_MPC = pickle.load(file_data)
    file_data.close()
print("===== TV-MPC terminated")
# ======================================================================================================================
# ==============================  LMPC w\ LOCAL LINEAR REGRESSION ======================================================
# ======================================================================================================================
print("Starting LMPC")
ClosedLoopLMPC = ClosedLoopData(dt, TimeLMPC, v0)
LMPCOpenLoopData = LMPCprediction(N, n, d, TimeLMPC, numSS_Points, Laps)
LMPCSimulator = Simulator(map, 1, 1)

LMPController = ControllerLMPC(numSS_Points, numSS_it, N, Qslack, Qlane, Q_LMPC, R_LMPC, dR_LMPC, dt, map, Laps, TimeLMPC, LMPC_Solver, inputConstr)
LMPController.addTrajectory(ClosedLoopDataPID)
LMPController.addTrajectory(ClosedLoopDataLTV_MPC)
LMPController.addTrajectory(ClosedLoopDataPID)
LMPController.addTrajectory(ClosedLoopDataLTI_MPC)

x0           = np.zeros((1,n))
x0_glob      = np.zeros((1,n))
x0[0,:]      = ClosedLoopLMPC.x[0,:]
x0_glob[0,:] = ClosedLoopLMPC.x_glob[0,:]

if RunLMPC == 1:
    for it in range(numSS_it, Laps):

        ClosedLoopLMPC.updateInitialConditions(x0, x0_glob)
        LMPCSimulator.Sim(ClosedLoopLMPC, LMPController, LMPCOpenLoopData)
        LMPController.addTrajectory(ClosedLoopLMPC)

        if LMPController.feasible == 0:
            break
        else:
            # Reset Initial Conditions
            x0[0,:]      = ClosedLoopLMPC.x[ClosedLoopLMPC.SimTime, :] - np.array([0, 0, 0, 0, map.TrackLength, 0])
            x0_glob[0,:] = ClosedLoopLMPC.x_glob[ClosedLoopLMPC.SimTime, :]

    file_data = open(sys.path[0]+'\data\LMPController.obj', 'wb')
    pickle.dump(ClosedLoopLMPC, file_data)
    pickle.dump(LMPController, file_data)
    pickle.dump(LMPCOpenLoopData, file_data)
    file_data.close()
else:
    file_data = open(sys.path[0]+'\data\LMPController.obj', 'rb')
    ClosedLoopLMPC = pickle.load(file_data)
    LMPController  = pickle.load(file_data)
    LMPCOpenLoopData  = pickle.load(file_data)
    file_data.close()

print("===== LMPC terminated")
# ======================================================================================================================
# ========================================= PLOT TRACK =================================================================
# ======================================================================================================================
laptimes = np.zeros((50,2))

#Laptime Plot
for i in range(0, LMPController.it):
    print("Lap time at iteration ", i, " is ", LMPController.Qfun[0, i]*dt, "s")
    laptimes[i,0] = LMPController.Qfun[0, i]*dt
    laptimes[i,1] = i
plt.figure(3)
plt.plot(laptimes[:,1],laptimes[:,0],'-o')
plt.ylabel('Lap Time (sec)')
plt.xlabel('Lap Number')

print("===== Start Plotting")
if plotFlag == 1:
    plotTrajectory(map, ClosedLoopDataPID.x, ClosedLoopDataPID.x_glob, ClosedLoopDataPID.u)

if plotFlagMPC == 1:
    plotTrajectory(map, ClosedLoopDataLTI_MPC.x, ClosedLoopDataLTI_MPC.x_glob, ClosedLoopDataLTI_MPC.u)

if plotFlagMPC_tv == 1:
    plotTrajectory(map, ClosedLoopDataLTV_MPC.x, ClosedLoopDataLTV_MPC.x_glob, ClosedLoopDataLTV_MPC.u)

if plotFlagLMPC == 1:
    plotClosedLoopLMPC(LMPController, map)

if animation_xyFlag == 1:
    animation_xy(map, LMPCOpenLoopData, LMPController, Laps-2)

if animation_stateFlag == 1:
    animation_states(map, LMPCOpenLoopData, LMPController, 10)

unityTestChangeOfCoordinates(map, ClosedLoopDataPID)
unityTestChangeOfCoordinates(map, ClosedLoopDataLTI_MPC)
unityTestChangeOfCoordinates(map, ClosedLoopLMPC)

# saveGif_xyResults(map, LMPCOpenLoopData, LMPController, Laps-1)
# Save_statesAnimation(map, LMPCOpenLoopData, LMPController, 5)
plt.show()
