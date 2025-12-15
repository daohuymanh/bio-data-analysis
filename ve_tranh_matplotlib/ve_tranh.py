import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from matplotlib.transforms import Affine2D

# Tạo canvas
fig, ax = plt.subplots(figsize=(8, 5))
ax.set_facecolor("#f5efe6")  # nền giấy nhẹ
ax.set_xlim(-5, 5)
ax.set_ylim(-3, 3)
ax.axis("off")

# ===== DÒNG NƯỚC =====
x = np.linspace(-6, 6, 400)
for y0 in [-0.8, -1.2, -1.6]:
    y = 0.15 * np.sin(x) + y0
    ax.plot(x, y, color="#9bb7c9", linewidth=2, alpha=0.8)

# ===== LÁ BÀNG =====
leaf = Ellipse(
    (0, 0.2),
    width=3.0,
    height=1.6,
    facecolor="#b23a2f",
    edgecolor="none"
)

# Nghiêng lá như bị gió cuốn
transform = Affine2D().rotate_deg_around(0, 0.2, -25) + ax.transData
leaf.set_transform(transform)
ax.add_patch(leaf)

# ===== GÂN LÁ =====
vein_x = np.linspace(-1.3, 1.3, 100)
vein_y = 0.1 * np.sin(vein_x)

ax.plot(
    vein_x,
    vein_y + 0.2,
    color="#7a1f1a",
    linewidth=2,
    transform=transform
)

# Gân phụ
for offset in [-0.4, 0.4]:
    ax.plot(
        vein_x,
        vein_y * 0.5 + offset + 0.2,
        color="#7a1f1a",
        linewidth=1,
        alpha=0.6,
        transform=transform
    )

# Lưu ảnh
plt.savefig("la_bang_buong_troi.png", dpi=300, bbox_inches="tight")
print("la_bang_buong_troi.png")
