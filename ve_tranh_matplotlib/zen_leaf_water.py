
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(6, 8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 14)
ax.axis("off")
ax.set_facecolor("white")

t = np.linspace(0, 2*np.pi, 300)
x_leaf = 5 + 1.4 * np.cos(t)
y_leaf = 9 + 0.9 * np.sin(t)

ax.plot(x_leaf, y_leaf, color="black", linewidth=1.2)
ax.plot([5, 5.7], [9, 9.8], color="black", linewidth=1)
ax.plot([5, 5.9], [8.2, 7.7], color="black", linewidth=1)

for y in [10.1, 9.6]:
    x = np.linspace(3, 4.5, 200)
    ax.plot(x, y + 0.12*np.sin(1.5*x), color="black", linewidth=0.8)

for i, y in enumerate([4.6, 4.1, 3.6]):
    x = np.linspace(2.5, 7.5, 300)
    ax.plot(x, y + 0.1*np.sin(x + i), color="black", linewidth=0.9)

theta = np.linspace(0, 2*np.pi, 200)
ax.plot(7.8 + 0.35*np.cos(theta),
        2.3 + 0.35*np.sin(theta),
        color="black", linewidth=1)

plt.show()
