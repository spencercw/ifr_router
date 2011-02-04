#!/usr/bin/env python3
# coding=utf-8

import os
import re
import sys
from pprint import pprint

## Provides access to the X-Plane structured navadata.
class NavData:
	## Constructor; specifies the path to the navdata.
	#  \param path Path to the navdata. This must contain at least earth_awy.dat, earth_fix.dat,
	#  earth_nav.dat and apt.dat.
	def __init__(self, path):
		# Check the path and files
		if not os.path.exists(path):
			raise ValueError('path does not exist')
		if not os.path.isdir(path):
			raise ValueError('path is not a directory')
		files = [
			os.path.join(path, 'earth_awy.dat'),
			os.path.join(path, 'earth_fix.dat'),
			os.path.join(path, 'earth_nav.dat'),
			os.path.join(path, 'apt.dat') ]
		for file in files:
			if not os.path.exists(file):
				raise ValueError('{0} missing'.format(file))
			if not os.path.isfile(file):
				raise ValueError('{0} is not a file'.format(file))

		# Parse the data
		self.airways = { }
		self.navaids = { }
		for file in files:
			print('Parsing {0}'.format(file), file = sys.stderr)
			self._parseData(file)

	## Returns the navaids between the source and destination waypoints in an airway.
	#  \returns A list of navaids and the airway. The list will not include the source but will
	# include the destination. \c None and \c None is returned if the airway could not be found
	def findAirway(self, code, src, dest):
		if code not in self.airways:
			return None, None
		airways = self.airways[code]

		# FIXME: This shouldn't be checking the code for the source
		for airway in airways:
			foundSrc, foundDest, reverse = False, False, False
			waypoints = [ ]

			for waypoint in airway['waypoints']:
				if waypoint['navaid']['code'] == src['code']:
					if foundDest:
						# The destination was found first; we've now found the source so we are
						# finished
						waypoints.reverse()
						return waypoints, airway
					foundSrc = True
				elif waypoint['navaid']['code'] == dest:
					waypoint = waypoint['navaid'].copy()
					waypoint.update(inAwy = airway, outAwy = None)
					waypoints.append(waypoint)
					if foundSrc:
						# Found the source first; we are finished
						return waypoints, airway
					foundDest = True
				elif foundSrc or foundDest:
					# We are somewhere between the source and destination
					if len(waypoints) != 0:
						waypoints[-1]['outAwy'] = airway
					waypoint = waypoint['navaid'].copy()
					waypoint.update(inAwy = airway, outAwy = None)
					waypoints.append(waypoint)

		return None, None

	# Parses and stores the data in the give file
	def _parseData(self, path):
		if path.endswith('awy.dat'):
			type, version = 'awy', '640'
		elif path.endswith('fix.dat'):
			type, version = 'fix', '600'
		elif path.endswith('nav.dat'):
			type, version = 'nav', '810'
		elif path.endswith('apt.dat'):
			type, version = 'apt', '850'
		else:
			raise ValueError('{0}: Unrecognised navdata type')

		airports = [ ]
		awySegments = { }
		f = open(path, 'r', encoding = 'latin_1')
		i = 0
		for line in f:
			i += 1
			line = line.rstrip('\r\n')

			# Parse the header
			if i < 4:
				if line == 1:
					# Origin code. We don't use this, but check it's valid anyway.
					if line != 'I' and line != 'A':
						raise ValueError('{0} invalid. Line {1}: Invalid origin code'.format(path, i))
				elif line == 2:
					m = re.match('^([0-9]+) Version', line)
					if m is None:
						raise ValueError('{0} invalid. Line {1}: Invalid version string'.format(path, i))
					if m.group(1) != version:
						raise ValueError('{0}: Unsupported file format version'.format(path))
				elif line == 3:
					if line != '':
						raise ValueError('{0} invalid. Line {1}: Expected empty line'.format(path, i))
				continue

			# Parse the data
			if type == 'nav':
				m = re.match('^([0-9]+)\s?', line)
				if m is None:
					raise ValueError('{0} invalid. Line {1}: Invalid row code'.format(path, i))
				code = m.group(1)

				if code == '2':
					# NDB
					expected = 9
					tokens = line.split(None, expected - 1)
					if len(tokens) != expected:
						raise ValueError('{0} invalid. Line {1}: Incorrect number of tokens. Got {2}; expected {3}.'.format(path, i, len(tokens), expected))

					ident = tokens[7]
					data = dict(
						type      = 'ndb',
						coords    = (float(tokens[1]), float(tokens[2])),
						elevation = int(tokens[3]),
						freq      = int(tokens[4]),
						recRange  = int(tokens[5]),
						code      = ident,
						name      = tokens[8])
					if ident in self.navaids:
						self.navaids[ident].append(data)
					else:
						self.navaids[ident] = [ data ]

				elif code == '3':
					# VOR
					expected = 9
					tokens = line.split(None, expected - 1)
					if len(tokens) != expected:
						raise ValueError('{0} invalid. Line {1}: Incorrect number of tokens. Got {2}; expected {3}.'.format(path, i, len(tokens), expected))

					ident = tokens[7]
					data = dict(
						type      = 'vor',
						coords    = (float(tokens[1]), float(tokens[2])),
						elevation = int(tokens[3]),
						freq      = int(tokens[4]),
						recRange  = int(tokens[5]),
						sVar      = float(tokens[6]),
						code      = ident,
						name      = tokens[8])
					if ident in self.navaids:
						self.navaids[ident].append(data)
					else:
						self.navaids[ident] = [ data ]

				elif code == '12' or code == '13':
					# DME
					expected = 9
					tokens = line.split(None, expected - 1)
					if len(tokens) != expected:
						raise ValueError('{0} invalid. Line {1}: Incorrect number of tokens. Got {2}; expected {3}.'.format(path, i, len(tokens), expected))

					ident = tokens[7]
					data = dict(
						type      = 'dme',
						coords    = (float(tokens[1]), float(tokens[2])),
						elevation = int(tokens[3]),
						freq      = int(tokens[4]),
						recRange  = int(tokens[5]),
						dmeBias   = float(tokens[6]),
						code      = ident,
						name      = tokens[8])
					if ident in self.navaids:
						self.navaids[ident].append(data)
					else:
						self.navaids[ident] = [ data ]

				elif code == '99':
					# End of file
					break

				# Not interested in these
				elif code == '4' or code == '5' or code == '6' or code == '7' or code == '8' or code == '9':
					pass

				else:
					raise ValueError('{0} invalid. Line {1}: Unrecognised row code {2}.'.format(path, i, code))

			elif type == 'fix':
				# Discard lines we aren't interested in
				if line == '':
					continue
				if line == '99':
					break

				expected = 3
				tokens = line.split(None, expected - 1)
				if len(tokens) != expected:
					raise ValueError('{0} invalid. Line {1}: Incorrect number of tokens. Got {2}; expected {3}.'.format(path, i, len(tokens), expected))

				ident = tokens[2]
				data = dict(
					type      = 'fix',
					coords    = (float(tokens[0]), float(tokens[1])),
					code      = ident)
				if ident in self.navaids:
					self.navaids[ident].append(data)
				else:
					self.navaids[ident] = [ data ]

			elif type == 'awy':
				# Loading airway data is a two step process. First we read the segments into a dict
				# keyed by the airway identifier, then we run through the segments and join up
				# segments into actual airways. We can't do this in one step because segments may be
				# presented in any order, and more than one airway can have the same identifier.
				expected = 10
				tokens = line.split(None, expected - 1)
				if len(tokens) != expected:
					if len(tokens) == 1 and line == '99':
						# End of file
						break
					raise ValueError('{0} invalid. Line {1}: Incorrect number of tokens. Got {2}; expected {3}.'.format(path, i, len(tokens), expected))
				if tokens[6] != '1' and tokens[6] != '2':
					raise ValueError("{0} invalid. Line {1}: Invalid airway type '{2}.".format(path, i, tokens[6]))

				idents = tokens[9].split('-')
				data = dict(
					waypoints = (
						dict(code = tokens[0], coords = (float(tokens[1]), float(tokens[2]))),
						dict(code = tokens[3], coords = (float(tokens[4]), float(tokens[5])))),
					high = tokens[6] == '2',
					base = int(tokens[7]),
					top  = int(tokens[8]))
				for ident in idents:
					if ident in awySegments:
						awySegments[ident].append(data.copy())
					else:
						awySegments[ident] = [ data.copy() ]

			elif type == 'apt':
				# The airport data unhelpfully doesn't include the airport reference point, so use
				# the geographical centre of the airport taking into account runways and helipads

				# Discard lines we aren't interested in
				if line == '':
					continue
				if line == '99':
					break
				code = line.split(None, 1)[0]
				if code != '1' and code != '16' and code != '17' and \
					code != '100' and code != '102' and code != '103':
					continue

				if code == '1' or code == '16' or code == '17':
					# Airport header
					expected = 6
					tokens = line.split(None, expected - 1)
					if len(tokens) != expected:
						raise ValueError('{0} invalid. Line {1}: Incorrect number of tokens. Got {2}; expected {3}.'.format(path, i, len(tokens), expected))

					airports.append(dict(
						coords    = [ ],
						elevation = int(tokens[1]),
						code      = tokens[4],
						name      = tokens[5]))

				else:
					if len(airports) == 0:
						raise ValueError('{0} invalid. Line {1}: Runway before airport header.'.format(path, i))

					if code == '100':
						# Land runway
						expected = 26
						tokens = line.split(None, expected - 1)
						if len(tokens) != expected:
							raise ValueError('{0} invalid. Line {1}: Incorrect number of tokens. Got {2}; expected {3}.'.format(path, i, len(tokens), expected))

						airports[-1]['coords'] += [
							(float(tokens[9]), float(tokens[10])),
							(float(tokens[18]), float(tokens[19])) ]

					elif code == '101':
						# Water runway
						expected = 9
						tokens = line.split(None, expected - 1)
						if len(tokens) != expected:
							raise ValueError('{0} invalid. Line {1}: Incorrect number of tokens. Got {2}; expected {3}.'.format(path, i, len(tokens), expected))

						airports[-1]['coords'] += [
							(float(tokens[4]), float(tokens[5])),
							(float(tokens[7]), float(tokens[8])) ]

					elif code == '103':
						# Helipad
						expected = 12
						tokens = line.split(None, expected - 1)
						if len(tokens) != expected:
							raise ValueError('{0} invalid. Line {1}: Incorrect number of tokens. Got {2}; expected {3}.'.format(path, i, len(tokens), expected))

						airports[-1]['coords'].append((float(tokens[2]), float(tokens[3])))

		if type == 'awy':
			# Join airway segments into airways
			for ident, segments in awySegments.items():
				while len(segments) != 0:
					# Fill the airway structure
					airway = dict(
						code      = ident,
						high      = segments[0]['high'],
						waypoints = [
							dict(
								base   = segments[0]['base'],
								top    = segments[0]['top'],
								navaid = segments[0]['waypoints'][0]),
							dict(
								base   = None,
								top    = None,
								navaid = segments[0]['waypoints'][1])])
					del segments[0]

					while True:
						found = False
						i = 0
						for segment in segments:
							if segment['high'] == airway['high'] and \
							  (segment['waypoints'][0] == airway['waypoints'][-1]['navaid'] or \
							   segment['waypoints'][1] == airway['waypoints'][-1]['navaid']):
								found = True

								# Flip the source and destination around if necessary
								if segment['waypoints'][1] == airway['waypoints'][-1]['navaid']:
									waypoint = segment['waypoints'][0]
								else:
									waypoint = segment['waypoints'][1]

								airway['waypoints'][-1]['base'] = segment['base']
								airway['waypoints'][-1]['top']  = segment['top']
								airway['waypoints'].append(dict(
									base   = None,
									top    = None,
									navaid = waypoint))

								del segments[i]
								break
							i += 1

						if not found:
							# End of airway; continue in the other direction
							i = 0
							for segment in segments:
								if segment['high'] == airway['high'] and \
								  (segment['waypoints'][0] == airway['waypoints'][0]['navaid'] or \
								   segment['waypoints'][1] == airway['waypoints'][0]['navaid']):
									found = True

									if segment['waypoints'][0] == airway['waypoints'][0]['navaid']:
										waypoint = segment['waypoints'][1]
									else:
										waypoint = segment['waypoints'][0]

									airway['waypoints'].insert(0, dict(
										base   = segment['base'],
										top    = segment['top'],
										navaid = waypoint))

									del segments[i]
									break
								i += 1
							if not found:
								# Got all the waypoints
								break

					if ident in self.airways:
						self.airways[ident].append(airway)
					else:
						self.airways[ident] = [ airway ]

		elif type == 'apt':
			# Average coordinates
			for airport in airports:
				if len(airport['coords']) == 0:
					continue
				coords = [0, 0]
				for point in airport['coords']:
					coords[0] += point[0]
					coords[1] += point[1]
				coords[0] /= len(airport['coords'])
				coords[1] /= len(airport['coords'])
				airport['coords'] = tuple(coords)

				if airport['code'] in self.navaids:
					self.navaids[airport['code']].append(airport)
				else:
					self.navaids[airport['code']] = [ airport ]
