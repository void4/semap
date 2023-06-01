from random import random
import os
import pickle
from collections import defaultdict

from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup as BS
import numpy as np


BREAKPOINT = None

REGENERATE = False

PLOT = False

CACHEF = "cache.pickle"

LINKFILE = "PostLinks.xml"
POSTFILE = "Posts.xml"

TAGID = 0
tagidcache = {}
def tagid(tag):
	global tagidcache, TAGID
	if tag not in tagidcache:
		tagidcache[tag] = TAGID
		TAGID += 1
	return tagidcache[tag]


cache_exists = os.path.exists(CACHEF)


if not cache_exists or (cache_exists and REGENERATE):
	print("Regenerating...")
	from umap import UMAP
	import scipy

	"""
	edges = []
	with open(LINKFILE) as f:
		xml = BS(f.read(), "lxml")
		
	for row in xml.find_all("row"):
		print(row)
		created = row["creationdate"]
		postid = row["postid"]
		related = row["relatedpostid"]
		linktype = row["linktypeid"]

		weight = 1

		edges.append([postid, related, weight])
	"""

	with open(POSTFILE) as f:
		xml = BS(f.read(), "lxml")


	lil_matrix_rows = []
	lil_matrix_data = []

	postrow = {}

	for r, row in enumerate(xml.find_all("row")):
		if BREAKPOINT and r >= BREAKPOINT:
			break
		created = row["creationdate"]
		postid = int(row["id"])
		tags = row.get("tags", "")

		weight = 1
		
		row = []
		data = []
		
		for tag in tags.split("<"):
			if not tag:
				continue
			tag = tag.replace(">", "")
			
			#edges.append([postid, tagid(tag), weight])
			# TODO two-way, undirected?
			#edges.append([tagid(tag), postid, weight])
			row.append(tagid(tag))
			data.append(weight)
			
		postrow[postid] = len(lil_matrix_rows)
		lil_matrix_rows.append(row)
		lil_matrix_data.append(data)


	factor_matrix = scipy.sparse.lil_matrix((len(lil_matrix_rows), TAGID), dtype=np.float32)
	factor_matrix.rows = np.array(lil_matrix_rows)
	factor_matrix.data = np.array(lil_matrix_data)

	mapper = UMAP(metric="cosine", random_state=42, low_memory=True).fit(factor_matrix)



	with open(CACHEF, "wb+") as cachef:
		cachef.write(pickle.dumps([postrow, mapper]))

else:
	print("Loading embedding...")
	with open(CACHEF, "rb") as cachef:
		postrow, mapper = pickle.loads(cachef.read())




with open(POSTFILE) as f:
	xml = BS(f.read(), "lxml")
	
pids = []
xs = []
ys = []
text = []

def escape(s):
	return secure_filename(s).replace("_", " ")


JSONFILE = "data.js"
print(f"Writing {JSONFILE}...")

f = open(JSONFILE, "w+")

f.write("data = [\n")

lines = ""

tagposx = defaultdict(list)
tagposy = defaultdict(list)

coords = {}
def roffset(scale=10):
	# TODO use fixed seed
	return (random()-0.5)*scale

for r, row in enumerate(xml.find_all("row")):
	if BREAKPOINT and r >= BREAKPOINT:
		break
	postid = int(row["id"])
	views = row.get("viewcount", 0)
	created = row["creationdate"]
	score = row["score"]


	answered = "true" if "acceptedanswerid" in row.attrs else "false"

	if "title" not in row.attrs:
		continue
	
	title = row["title"]
	
	r = postrow[postid]
	
	x, y = mapper.embedding_[r]
	
	scale = 100
	x *= scale
	y *= scale
	
	x = int(x)
	y = int(y)

	
	xy = (x,y)
	if xy in coords:
		x += roffset(10)
		y += roffset(40)
	
	xy = (int(x), int(y))
	
	coords[xy] = True
	
	#x = max(0, min(x, 1000))
	#y = max(0, min(y, 1000))
	
	title = title.replace('"', "")
	
	lines += f"\t[{postid}, {x}, {y}, {views}, \"{escape(title)}\", {answered}, false, {score}],\n"
	

	# have to create cache here again in case not regenerate
	tags = row.get("tags", "")

	for tag in tags.split("<"):
		if not tag:
			continue
		tag = tag.replace(">", "")
		tagid(tag)
		tagposx[tag].append(x)
		tagposy[tag].append(y)

for tag, tagid in tagidcache.items():
	print(tag, tagid)
	x = np.median(tagposx[tag])
	y = np.median(tagposy[tag])
	views = 1000
	f.write(f"\t[{tagid}, {x}, {y}, {views}, \"{escape(tag)}\", true, true, 0],\n")

# just use average of tag position?

f.write(lines)
f.write("\n]")
f.close()

if PLOT:
	print("Plotting...")
	import umap.plot
	umap.plot.points(mapper, values=np.arange(len(mapper.embedding_)), theme="viridis")
	import matplotlib.pyplot as plt
	plt.show()
