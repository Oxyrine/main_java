#Scatterplot of X,Y,Z coordinates

import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Load Excel data
df = pd.read_excel("Data Extraction and Multileaders Sample Coordinates.xlsx")

# Extract coordinates and dimensions
x = df['Position X']
y = df['Position Y']
z = df['Position Z']   # often 0 for 2D floor plans

# Plot as 3D scatter
fig = plt.figure(figsize=(8,6))
ax = fig.add_subplot(111, projection='3d')
ax.scatter(x, y, z, c='cyan', marker='o')

ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
plt.show()
