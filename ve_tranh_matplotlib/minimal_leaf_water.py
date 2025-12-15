
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(6, 8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 14)
ax.axis("off")

leaf_x = np.linspace(0, 2*np.pi, 300)
x_leaf = 5 + 1.8 * np.cos(leaf_x)
y_leaf = 9 + 1.2 * np.sin(leaf_x)

ax.fill(x_leaf, y_leaf, color="#c0392b", alpha=0.9)
ax.plot(x_leaf, y_leaf, color="black", linewidth=1)

ax.plot([5, 5.9], [9, 9.9], color="black", linewidth=1)
ax.plot([5, 4.2], [9, 9.7], color="black", linewidth=0.8)
ax.plot([5, 5.8], [9, 8.3], color="black", linewidth=0.8)

ax.plot([5, 6.2], [8.3, 7.8], color="black", linewidth=1.2)

for y in [10.2, 9.7, 9.2]:
    x = np.linspace(2.5, 4.2, 200)
    ax.plot(x, y + 0.15*np.sin(2*x), color="black", linewidth=1)

for i, y in enumerate([4.8, 4.3, 3.8, 3.3]):
    x = np.linspace(2, 8, 400)
    ax.plot(x, y + 0.15*np.sin(x + i), color="black", linewidth=1)

plt.show()
