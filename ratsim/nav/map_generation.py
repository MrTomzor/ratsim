from ratsim.roslike_unity_connector.connector import *
from ratsim.roslike_unity_connector.message_definitions import *
from PIL import Image
from scipy.ndimage import label, center_of_mass

import numpy as np
import os

class MapGenTemplate():
    def __init__(self, root_path: str = "", meters_per_pixel = 1):
        if root_path != "":
            self.load_from_root_path(root_path)
        self.meters_per_pixel = meters_per_pixel

    def load_from_root_path(self, root_path, spawn_idx=1, poi_idx=1, forbidden_idx=1, growable_idx=1):
        print(f"loading map template from {root_path}")
        print(f"using spawn{spawn_idx}, poi{poi_idx}, forbidden{forbidden_idx}, growable{growable_idx}")

        # load PNG image as binary mask: 1 where alpha channel is nonzero
        def load_mask(file_name: str) -> np.ndarray:
            file_path = os.path.join(root_path, file_name)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Missing required mask: {file_path}")

            img = Image.open(file_path).convert("RGBA")  # ensure RGBA
            arr = np.array(img)  # shape (H, W, 4)
            alpha = arr[:, :, 3]  # extract alpha channel
            return alpha > 0  # binary mask

        # always load obstacles
        self.obstacles       = load_mask("obstacles.png")
        # load indexed masks
        self.spawn_mask      = load_mask(f"spawn{spawn_idx}.png")
        self.poi_mask        = load_mask(f"poi{poi_idx}.png")
        self.forbidden_mask  = load_mask(f"forbidden{forbidden_idx}.png")
        self.growable_mask   = load_mask(f"growable{growable_idx}.png")

        # segment pois
        self.poi_labeled, self.num_poi_clusters = label(self.poi_mask)
        self.poi_centroids = center_of_mass(self.poi_mask, self.poi_labeled, range(1, self.num_poi_clusters + 1))

        # order clusters left-to-right (by x coordinate)
        self.poi_order = sorted(range(self.num_poi_clusters), key=lambda i: self.poi_centroids[i][1])

    def visualize(self):
        import matplotlib.pyplot as plt

        h, w = self.obstacles.shape
        canvas = np.ones((h, w, 3), dtype=np.float32)  # white background

        # paint obstacles in black
        canvas[self.obstacles] = [0, 0, 0]

        # paint forbidden areas in red with 50% opacity
        red = np.array([1, 0, 0], dtype=np.float32)
        alpha = 0.5
        canvas[self.forbidden_mask] = alpha * red + (1 - alpha) * canvas[self.forbidden_mask]

        # draw poi cluster numbers
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.imshow(canvas)

        for idx, cluster_idx in enumerate(self.poi_order, start=1):
            cy, cx = self.poi_centroids[cluster_idx]
            ax.text(cx, cy, str(idx), color='blue', fontsize=12, fontweight='bold',
                    ha='center', va='center', bbox=dict(facecolor='white', alpha=0.5, edgecolor='none'))

        ax.axis('off')
        plt.show()


    def to_ratsim_msg(self) -> MapGenTemplate2D:
        msg = MapGenTemplate2D()
        msg.meters_per_pixel = self.meters_per_pixel
        msg.width = self.obstacles.shape[1]
        msg.height = self.obstacles.shape[0]
        msg.obstacles = self.obstacles.flatten().astype(np.uint8).tolist()
        msg.spawnMask = self.spawn_mask.flatten().astype(np.uint8).tolist()
        msg.poiMask = self.poi_mask.flatten().astype(np.uint8).tolist()
        msg.forbiddenMask = self.forbidden_mask.flatten().astype(np.uint8).tolist()
        msg.growableMask = self.growable_mask.flatten().astype(np.uint8).tolist()
        return msg


