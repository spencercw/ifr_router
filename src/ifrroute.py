#!/usr/bin/env python3
# coding=utf-8

from math import *

## Calculates the great circle distance between two points.
#  \param standpoint Standpoint tuple (lat, lon)
#  \param forepoint Forepoint tuple (lat, lon)
def coordsDistance(standpoint, forepoint):
	s = (radians(standpoint[0]), radians(standpoint[1]))
	f = (radians(forepoint[0]),  radians(forepoint[1]))
	lonDiff = f[1] - s[1]
	return 3441.035 * atan2(sqrt(pow(cos(f[0]) * sin(lonDiff), 2) + pow(cos(s[0]) * sin(f[0]) - sin(s[0]) * cos(f[0]) * cos(lonDiff), 2)),
		sin(s[1]) * sin(f[1]) + cos(s[1]) * cos(s[1]) * cos(lonDiff))

class IfrRoute:
	## Constructor; creates a route from the given route string.
	#  \param navdata Navdata to use while parsing the route.
	#  \param route Route to parse. This constructor will make a best guess at the route if any of
	#  the requested waypoints or airways are missing, or if there are multiple choices. If you need
	#  to be alerted in these cases, leave this as None and use the append() function instead.
	def __init__(self, navdata, route = None):
		self._navdata = navdata
		self.waypoints = [ ]
		if route is not None:
			self.append(route, True, False)

	## Appends the given route to the current route.
	#  \param route Route to append.
	#  \param bestGuess If set to \c True, when there are multiple potential navaids, the closest
	#  will be used. If there are multiple potential ariways, the first will be used. If this is set
	#  to \c False and this happens, the function will return a RouteFailure object.
	#  \param missingOk If False, when a navaid or airway in the route is not found, a
	#  RouteFailure will be returned, otherwise it will be ignored.
	#  \param choice If not None, this identifies which waypoint to use in case of multiple choices.
	def append(self, route, bestGuess = False, missingOk = False, choice = None):
		lastWaypoint = None
		tokens = route.upper().split()
		remaining = ' '.join(tokens)
		# Type of token we are expecting the next to be
		expecting = dict(waypoint = True, airway = False, direct = False)

		# Parse each token
		i = 0
		while i != len(tokens):
			if expecting['direct'] and i != len(tokens) - 1:
				if tokens[i] == 'DCT' or tokens[i] == 'SID' or tokens[i] == 'STAR':
					expecting['waypoint'] = True
					expecting['airway'] = False
					expecting['direct'] = False
					continue

			if expecting['airway']:
				# Make sure this isn't the first or last token
				if lastWaypoint is not None and i != len(tokens) - 1:
					found, lastWaypoint = self._findAirway(tokens[i], lastWaypoint, tokens[i + 1])
					if found:
						i += 2
						if i == len(tokens):
							break
						expecting['waypoint'] = True
						expecting['airway'] = True
						expecting['direct'] = True
						continue

			if expecting['waypoint']:
				if choice is not None:
					self.waypoints.append(choice.update(inAwy = None, outAwy = None))
					lastWaypoint = choice
					choice = None
				else:
					if tokens[i] not in self._navdata.navaids:
						# No waypoints found
						if not missingOk:
							# Could it be an airway as well?
							navaid, wp1, wp2 = True, None, None
							if expecting['airway'] and lastWaypoint is not None and \
								i != len(tokens) - 1:
								navaid, wp1, wp2 = False, tokens[i - 1], tokens[i + 1]
							return dict(remaining = remaining, navaid = navaid, code = tokens[i],
								choices = [ ], wp1 = wp1, wp2 = wp2)
					else:
						navaids = self._navdata.navaids[tokens[i]]
						if bestGuess:
							# Sort navaids by distance
							standpoint = (0, 0)
							if lastWaypoint is not None:
								standpoint = lastWaypoint['coords']
							navaids = sorted(navaids, key = lambda navaid:
								coordsDistance(standpoint, navaid['coords']))

							if len(navaids) == 1 or i >= len(tokens) - 2:
								# Only one waypoint found, or no possibility of following airway
								waypoint = navaids[0].copy()
								waypoint.update(inAwy = None, outAwy = None)
								self.waypoints.append(waypoint)
								# Check for airway
								if i < len(tokens) - 2:
									found, lastWaypoint = self._findAirway(tokens[i + 1],
										navaids[0], tokens[i + 2])
									if found:
										i += 2
							elif i < len(tokens) - 2:
								# More than one waypoint found with possibility of following airway
								self.waypoints.append(None)
								found = False
								for navaid in navaids:
									waypoint = navaid.copy()
									waypoint.update(inAwy = None, outAwy = None)
									self.waypoints[-1] = waypoint
									found, lastWaypoint = self._findAirway(tokens[i + 1],
										navaid, tokens[i + 2])
									if found:
										i += 2
										break
								if not found:
									# Couldn't find any suitable adjoining airway; just use the
									# nearest navaid
									waypoint = navaids[0]
									waypoint.copy().update(inAwy = None, outAwy = None)
									self.waypoints[-1] = waypoint
									lastWaypoint = navaids[0]
						else:
							if len(navaids) == 1:
								waypoint = navaids[0].copy()
								waypoint.update(inAwy = None, outAwy = None)
								self.waypoints.append(waypoint)
								lastWaypoint = navaids[0]
							elif len(navaids) > 1:
								# Could it be an airway as well?
								navaid, wp1, wp2 = True, None, None
								if expecting['airway'] and lastWaypoint is not None and \
									i != len(tokens) - 1:
									navaid, wp1, wp2 = False, tokens[i - 1], tokens[i + 1]
								return dict(remaining = remaining, navaid = navaid,
									code = tokens[i], choices = navaids, wp1 = wp1, wp2 = wp2)

				expecting['direct'] = True
				expecting['airway'] = True

			i += 1
			remaining = ' '.join(tokens[i:])

		return None

	## Finds the given airway and appends the waypoints to the route if found.
	#  \returns If the airway was found, True and the final navaid, otherwise, False and \c src.
	def _findAirway(self, airway, src, dest):
		waypoints, airway = self._navdata.findAirway(airway, src, dest)
		if waypoints is None or airway is None:
			return False, src
		else:
			self.waypoints[-1]['outAwy'] = airway
			self.waypoints += waypoints
			return True, waypoints[-1]
