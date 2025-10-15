import pybullet as p
import time
import pybullet_data

physicsClient = p.connect(p.GUI)  # or p.DIRECT for non-graphical version
p.setAdditionalSearchPath(pybullet_data.getDataPath())  # optionally
p.setGravity(0, 0, -10)
# planeId = p.loadURDF("plane.urdf")

for i in range(10000):
    p.stepSimulation()
    time.sleep(1.0 / 240.0)

p.disconnect()
