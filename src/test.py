#!/usr/bin/env python3
# coding=utf-8

import pickle
import sys
from pprint import pprint

from ifrroute import *
from navdata import *

# Check arguments
if len(sys.argv) == 1:
	print('Usage: test.py <route>', file = sys.stderr)
	sys.exit(1)

# Load navdata
try:
	f = open('navdata.pik', 'rb')
	print('Unpickling data', file = sys.stderr)
	navdata = pickle.load(f)
	f.close()
except IOError:
	print('Loading data')
	navdata = NavData(sys.path[0] + '/../navdata')

	print('Pickling data', file = sys.stderr)
	f = open('navdata.pik', 'wb')
	pickle.dump(navdata, f, pickle.HIGHEST_PROTOCOL)

# Parse route
print('Parsing route', file = sys.stderr)
route = IfrRoute(navdata)
result = route.append(' '.join(sys.argv[1:]), bestGuess = True, missingOk = False)

if result is not None:
	# Failed
	print('Parse failed:')
	pprint(result)
	print()
	if result['navaid']:
		print('Navaid {0} not found.'.format(result['code']))
	else:
		print('Navaid {0} or airway {1} {0} {2} not found.'.
			format(result['code'], result['wp1'], result['wp2']))
	sys.exit(1)

else:
	# Print waypoints
	for waypoint in route.waypoints:
		print(waypoint['code'], end = ' ')
	print()
