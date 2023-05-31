import os
from random import random

from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup as BS

LINKFILE = "PostLinks.xml"
POSTFILE = "Posts.xml"

# LargeVis Input
EDGEFILE = "edges.txt"
# LargeVis Output
POSITIONFILE = "positions.txt"

REGENERATE = False

TAGID = 10000000000
tagidcache = {}
def tagid(tag):
	global tagidcache, TAGID
	if tag not in tagidcache:
		tagidcache[tag] = TAGID
		TAGID += 1
	return tagidcache[tag]

if not os.path.exists(POSITIONFILE) or REGENERATE:
	edges = open(EDGEFILE, "w+")

	"""
	with open(LINKFILE) as f:
		xml = BS(f.read(), "lxml")
		
	for row in xml.find_all("row"):
		print(row)
		created = row["creationdate"]
		postid = row["postid"]
		related = row["relatedpostid"]
		linktype = row["linktypeid"]

		weight = 1

		edges.write(f"{postid} {related} {weight}\n")
	"""

	with open(POSTFILE) as f:
		xml = BS(f.read(), "lxml")
		
	for row in xml.find_all("row"):
		created = row["creationdate"]
		postid = row["id"]
		tags = row.get("tags", "")

		weight = 1
		for tag in tags.split("<"):
			if not tag:
				continue
			tag = tag.replace(">", "")
			edges.write(f"{postid} {tagid(tag)} {weight}\n")
			# TODO two-way, undirected?
			edges.write(f"{tagid(tag)} {postid} {weight}\n")

	edges.close()

	cmd = f"LargeVis/Linux/LargeVis -fea 0 -input {EDGEFILE} -output {POSITIONFILE}"

	print("Running", cmd)

	os.system(cmd)

positions = {}
coords = {}

def roffset():
	# TODO use fixed seed
	return (random()-0.5)*15

with open(POSITIONFILE) as f:
	lines = f.read().splitlines()
	for line in lines[1:]:#skip numnodes, dimensions
		pid, x, y = line.split()
		xy = (int(float(x)),int(float(y)))
		if xy in coords:
			#only try once?
			xy = (xy[0]+roffset(), xy[1]+roffset())
		positions[int(pid)] = xy
		coords[xy] = True
# no overlap

with open(POSTFILE) as f:
	xml = BS(f.read(), "lxml")
	
pids = []
xs = []
ys = []
text = []

def escape(s):
	return secure_filename(s).replace("_", " ")

JSONFILE = "data.js"

f = open(JSONFILE, "w+")

f.write("data = [\n")
	
for row in xml.find_all("row"):
	
	pid = int(row["id"])
	views = row.get("viewcount", 0)
	created = row["creationdate"]
	score = row["score"]

	# have to create cache here again in case not regenerate
	tags = row.get("tags", "")

	for tag in tags.split("<"):
		if not tag:
			continue
		tag = tag.replace(">", "")
		tagid(tag)


	answered = "true" if "acceptedanswerid" in row.attrs else "false"

	if "title" not in row.attrs:
		continue
	
	title = row["title"]
	
	if pid not in positions:
		#TODO print("not found:", pid)
		continue
		
	x, y = positions[pid]

	
	title = title.replace('"', "")
	
	f.write(f"\t[{pid}, {x}, {y}, {views}, \"{escape(title)}\", {answered}, false],\n")

for tag, tagid in tagidcache.items():
	print(tag, tagid)
	x, y = positions[tagid]
	views = 1000
	f.write(f"\t[{tagid}, {x}, {y}, {views}, \"{escape(tag)}\", true, true],\n")
		
f.write("\n]")
f.close()

