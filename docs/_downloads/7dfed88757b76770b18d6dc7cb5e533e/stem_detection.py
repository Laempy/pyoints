
# coding: utf-8

# # Detection of tree stems with Pyoints
# In the following, we try to detect stems in a forest using a three dimensional point cloud generated by a terrestrial laser scanner.
# The basic steps are:
# 
# 	1. Loading of the point cloud data
# 	2. Calculation of the height above ground
# 	3. Filtering of stem points
# 	4. Identification of stem clusters
# 	5. Fitting of stem vectors

# We begin with loading the required modules.

# In[ ]:


import numpy as np

from pyoints import (
	storage,
	Extent,
	filters,
	interpolate,
	clustering,
	classification,
	vector,
)


# In[ ]:


from mpl_toolkits import mplot3d
import matplotlib.pyplot as plt 

get_ipython().run_line_magic('matplotlib', 'inline')


# ## Loading of the point cloud data

# We load a three dimensional point cloud scanned in a forest.

# In[ ]:


lasReader = storage.LasReader('forest.las')
las = lasReader.load()
print(len(las))


# We receive a LasRecords instance representing the point cloud. We can treat it like a numpy record array with additional features. So, we inspect its properties first.

# In[ ]:


print('shape:')
print(las.shape)
print('attributes:')
print(las.dtype.descr)
print('projection:')
print(las.proj.proj4)
print('transformation matrix:')
print(np.round(las.t, 2))
print('data:')
print(las)


# ## Calculation of the height above ground
# The LAS file provides some altitude values. But, we are interested in the height above ground instead. So, we select points representing the ground first, to fit a Digital Elevation Model (DEM). Using the DEM we calculate the height above ground for each point.

# We use a DEM filter with a resolution of 0.5m. The filter selects local minima and guarantees a horizontal point distance of at least 0.5m and an altitude change between neighbored points below 50 degree.

# In[ ]:


grd_ids = filters.dem_filter(las.coords, 0.5, max_angle=50)
print(grd_ids)


# We have received a list of point indices which is used to select the desired representative ground points. So, we update the classification field for these points and plot them.

# In[ ]:


las.classification[grd_ids] = 22


# In[ ]:


plt.scatter(*las[las.classification == 22].coords[:, :2].T, color='black')
plt.xlabel('X (m)')
plt.ylabel('Y (m)')
plt.show()


# Now, we fit a DEM using a nearest neighbor interpolator.

# In[ ]:


xy = las.coords[grd_ids, :2]
z = las.coords[grd_ids, 2]
dem = interpolate.KnnInterpolator(xy, z)


# Finally, we calculate the height above ground and add a corresponding attribute to the point cloud.

# In[ ]:


height = las.coords[:, 2] - dem(las.coords)
las = las.add_fields([('height', float)], data=[height])
print(las.dtype.descr)


# ## Filtering of stem points
# Now, we try to filter the points subsequently until only points associated with stems remain.

# We will focus on points with height above ground greater 0.5m only.

# In[ ]:


fids = np.where(las.height > 0.5)[0]
print(len(fids))


# Due to the unnecessary high point density we filter the point cloud using a duplicate point filter. Only a subset of points with a point distance of at least 0.1m is kept.

# In[ ]:


filter_gen = filters.ball(las[fids].indexKD(), 0.1)
fids = fids[list(filter_gen)]
print(len(fids))


# Let's take a look at the remaining point cloud. To receive a nice plot, we define the axis limits first.

# In[ ]:


axes_lims = Extent([
	las.extent().center - 0.5 * las.extent().ranges.max(),
	las.extent().center + 0.5 * las.extent().ranges.max()
])


# In[ ]:


fig = plt.figure(figsize=(15, 15))
ax = plt.axes(projection='3d')
ax.set_xlim(axes_lims[0], axes_lims[3])
ax.set_ylim(axes_lims[1], axes_lims[4])
ax.set_zlim(axes_lims[2], axes_lims[5])
ax.set_xlabel('X (m)')
ax.set_ylabel('Y (m)')
ax.set_zlabel('Z (m)')

ax.plot_trisurf(*las[las.classification == 22].coords.T, cmap='gist_earth')
ax.scatter(*las[fids].coords.T, c=las.height[fids], cmap='coolwarm', marker='.')
plt.show()


# We can see four trees with linear stems. But, there are a lot of points associated with branches or leaves. We assign class 23 to the selected points for later visualization.

# In[ ]:


las.classification[fids] = 23


# To reduce noise, we only keep points with a lot of neighbors.

# In[ ]:


count = las[fids].indexKD().ball_count(0.3)
fids = fids[count > 10]
print(len(fids))
las.classification[fids] = 24


# In[ ]:


fig = plt.figure(figsize=(15, 15))
ax = plt.axes(projection='3d')
ax.set_xlim(axes_lims[0], axes_lims[3])
ax.set_ylim(axes_lims[1], axes_lims[4])
ax.set_zlim(axes_lims[2], axes_lims[5])
ax.set_xlabel('X (m)')
ax.set_ylabel('Y (m)')
ax.set_zlabel('Z (m)')

ax.plot_trisurf(*las[las.classification == 22].coords.T, cmap='gist_earth')
ax.scatter(*las[las.classification == 23].coords.T, color='gray', marker='.')
ax.scatter(*las[las.classification == 24].coords.T, color='red', marker='.')
plt.show()


# That's much better, but we are interested in the linear shape of the stems only. So, we filter with a radius of 1 m to remove similar points. This results in a point cloud with point distances of at least 1 m.

# In[ ]:


filter_gen = filters.ball(las[fids].indexKD(), 1.0)
fids = fids[list(filter_gen)]
print(len(fids))
las.classification[fids] = 25


# In[ ]:


fig = plt.figure(figsize=(15, 15))
ax = plt.axes(projection='3d')
ax.set_xlim(axes_lims[0], axes_lims[3])
ax.set_ylim(axes_lims[1], axes_lims[4])
ax.set_zlim(axes_lims[2], axes_lims[5])
ax.set_xlabel('X (m)')
ax.set_ylabel('Y (m)')
ax.set_zlabel('Z (m)')

ax.plot_trisurf(*las[las.classification == 22].coords.T, cmap='gist_earth')
ax.scatter(*las[las.classification == 25].coords.T, color='red')
plt.show()


# For dense point clouds, the filtering technique would result in point distances in a range of 1m to 2m. Thus, we can assume that linear arranged points should have 2 to 3 neighboring points within a radius of 1.5 m.

# In[ ]:


count = las[fids].indexKD().ball_count(1.5)
fids = fids[np.all((count >= 2, count <= 3), axis=0)]
print(len(fids))
las.classification[fids] = 26


# In[ ]:


fig = plt.figure(figsize=(15, 15))
ax = plt.axes(projection='3d')
ax.set_xlim(axes_lims[0], axes_lims[3])
ax.set_ylim(axes_lims[1], axes_lims[4])
ax.set_zlim(axes_lims[2], axes_lims[5])
ax.set_xlabel('X (m)')
ax.set_ylabel('Y (m)')
ax.set_zlabel('Z (m)')

ax.plot_trisurf(*las[las.classification == 22].coords.T, cmap='gist_earth')
ax.scatter(*las[las.classification == 25].coords.T, color='gray', marker='.')
ax.scatter(*las[las.classification == 26].coords.T, color='red')
plt.show()


# After applying the filters the stems are clearly visible. Thus, we can proceed with the actual detection of the stems.

# ## Identification of stem clusters
# We can detect the stems easily by clustering the previously filtered points. For this purpose we apply the DBSCAN algorithm.

# In[ ]:


cluster_indices = clustering.dbscan(las[fids].indexKD(), 2, epsilon=1.5)
print('number of points:')
print(len(cluster_indices))
print('cluster IDs:')
print(np.unique(cluster_indices))


# In the next step, we remove small clusters and unassigned points. In addition, we add an additional field, providing the tree ID.

# In[ ]:


cluster_dict = classification.classes_to_dict(cluster_indices, ids=fids, min_size=5)
cluster_indices = classification.dict_to_classes(cluster_dict, len(las))
print('tree IDs:')
print(cluster_dict.keys())
print('cluster_dict:')
print(cluster_dict)


# In[ ]:


las = las.add_fields([('tree_id', int)])
las.tree_id[:] = -1
for tree_id in cluster_dict:
	las.tree_id[cluster_dict[tree_id]] = tree_id


# In[ ]:


fig = plt.figure(figsize=(15, 15))
ax = plt.axes(projection='3d')
ax.set_xlim(axes_lims[0], axes_lims[3])
ax.set_ylim(axes_lims[1], axes_lims[4])
ax.set_zlim(axes_lims[2], axes_lims[5])
ax.set_xlabel('X (m)')
ax.set_ylabel('Y (m)')
ax.set_zlabel('Z (m)')

ax.scatter(*las[las.tree_id > -1].coords.T, c=las.tree_id[las.tree_id > -1], cmap='coolwarm')
plt.show()


# ## Fitting of stem vectors
# To model the stems, we it a vector to each stem.

# In[ ]:


stems = {
	tree_id: vector.Vector.from_coords(las[idx].coords)
	for tree_id, idx in cluster_dict.items()
}


# Finally, we determinate the tree root coordinates of the stems by calculating the intersection points with the surface.

# In[ ]:


roots = {
	tree_id: vector.vector_surface_intersection(stem, dem)
	for tree_id, stem in stems.items()
}
origins = {	tree_id: stem.origin for tree_id, stem in stems.items()}


# In[ ]:


fig = plt.figure(figsize=(15, 15))
ax = plt.axes(projection='3d')
ax.set_xlim(axes_lims[0], axes_lims[3])
ax.set_ylim(axes_lims[1], axes_lims[4])
ax.set_zlim(axes_lims[2], axes_lims[5])
ax.set_xlabel('X (m)')
ax.set_ylabel('Y (m)')
ax.set_zlabel('Z (m)')

ax.scatter(*las[las.tree_id > -1].coords.T, c=las.tree_id[las.tree_id > -1], cmap='Set1')
ax.scatter(*zip(*roots.values()), color='black', marker='X', s=40)
ax.scatter(*zip(*origins.values()), color='black', cmap='Set1', marker='^', s=40)
for tree_id in roots.keys():
	coords = np.vstack([roots[tree_id], origins[tree_id]])
	ax.plot(*coords.T, color='black')
plt.show()

