# This file is part of photoframe (https://github.com/mrworf/photoframe).
#
# photoframe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# photoframe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with photoframe.  If not, see <http://www.gnu.org/licenses/>.
#
import subprocess
import socket
import logging
import os
import re

class helper:
	@staticmethod
	def getResolution():
		res = None
		output = subprocess.check_output(['/bin/fbset'], stderr=DEVNULL)
		for line in output.split('\n'):
			line = line.strip()
			if line.startswith('mode "'):
				res = line[6:-1]
				break
		return res

	@staticmethod
	def getIP():
		ip = None
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.connect(("photoframe.sensenet.nu", 80))
			ip = s.getsockname()[0]
			s.close()
		except:
			pass
		return ip

	@staticmethod
	def getExtension(mime):
		mapping = {
			'image/jpeg' : 'jpg',
			'image/png' : 'png',
			'image/gif' : 'gif',
			'image/x-adobe-dng' : 'dng',
			'image/bmp' : 'bmp'
		}
		mime = mime.lower()
		if mime in mapping:
			return mapping[mime]
		return None

	@staticmethod
	def makeFullframe(filename, displayWidth, displayHeight, zoomOnly=False, autoChoose=False):
		name, ext = os.path.splitext(filename)
		filename_temp = "%s-frame%s" % (name, ext)

		with open(os.devnull, 'wb') as void:
			try:
				output = subprocess.check_output(['/usr/bin/identify', filename], stderr=void)
			except:
				logging.exception('Error trying to identify image')
				return False

		m = re.search('([1-9][0-9]*)x([1-9][0-9]*)', output)
		if m is None or m.groups() is None or len(m.groups()) != 2:
			logging.error('Unable to resolve regular expression for image size')
			return False
		width = int(m.group(1))
		height = int(m.group(2))

		width_border = 15
		width_spacing = 3
		border = None
		borderSmall = None

		# Calculate actual size of image based on display
		ar = (float)(width) / (float)(height)
		if width > displayWidth:
			adjWidth = displayWidth
			adjHeight = int(float(displayWidth) / ar)
		else:
			adjWidth = int(float(displayHeight) * ar)
			adjHeight = displayHeight

		logging.debug('Size of image is %dx%d, screen is %dx%d. New size is %dx%d', width, height, displayWidth, displayHeight, adjWidth, adjHeight)

		resizeString = '%sx%s'
		if adjHeight < displayHeight:
			border = '0x%d' % width_border
			spacing = '0x%d' % width_spacing
			padding = ((displayHeight - adjHeight) / 2 - width_border)
			resizeString = '%sx%s^'
			logging.debug('Landscape image, reframing (padding required %dpx)' % padding)
		elif adjWidth < displayWidth:
			border = '%dx0' % width_border
			spacing = '%dx0' % width_spacing
			padding = ((displayWidth - adjWidth) / 2 - width_border)
			resizeString = '^%sx%s'
			logging.debug('Portrait image, reframing (padding required %dpx)' % padding)
		else:
			logging.debug('Image is fullscreen, no reframing needed')
			return False

		#if padding < 20 and not autoChoose:
		#	logging.debug('That\'s less than 20px so skip reframing (%dx%d => %dx%d)', width, height, adjWidth, adjHeight)
		#	return False

		if padding < 60 and autoChoose:
			zoomOnly = True

		cmd = None
		try:
			# Time to process
			if zoomOnly:
				cmd = [
					'convert',
					filename + '[0]',
					'-resize',
					resizeString % (displayWidth, displayHeight),
					'-gravity',
					'center',
					'-crop',
					'%sx%s+0+0' % (displayWidth, displayHeight),
					'+repage',
					filename_temp
				]
			else:
				cmd = [
					'convert',
					filename + '[0]',
					'-resize',
					resizeString % (displayWidth, displayHeight),
					'-gravity',
					'center',
					'-crop',
					'%sx%s+0+0' % (displayWidth, displayHeight),
					'+repage',
					'-blur',
					'0x12',
					'-brightness-contrast',
					'-20x0',
					'(',
					filename + '[0]',
					'-bordercolor',
					'black',
					'-border',
					border,
					'-bordercolor',
					'black',
					'-border',
					spacing,
					'-resize',
					'%sx%s' % (displayWidth, displayHeight),
					'-background',
					'transparent',
					'-gravity',
					'center',
					'-extent',
					'%sx%s' % (displayWidth, displayHeight),
					')',
					'-composite',
					filename_temp
				]
		except:
			logging.exception('Error building command line')
			logging.debug('Filename: ' + repr(filename))
			logging.debug('Filename_temp: ' + repr(filename_temp))
			logging.debug('border: ' + repr(border))
			logging.debug('spacing: ' + repr(spacing))
			return False

		try:
			subprocess.check_output(cmd, stderr=subprocess.STDOUT)
		except subprocess.CalledProcessError as e:
			logging.exception('Unable to reframe the image')
			logging.error('Output: %s' % repr(e.output))
			return False
		os.rename(filename_temp, filename)
		return True

	@staticmethod
	def timezoneList():
		zones = subprocess.check_output(['/usr/bin/timedatectl', 'list-timezones']).split('\n')
		return [x for x in zones if x]

	@staticmethod
	def timezoneCurrent():
		with open('/etc/timezone', 'r') as f:
			result = f.readlines()
		return result[0].strip()

	@staticmethod
	def timezoneSet(zone):
		result = 1
		try:
			with open(os.devnull, 'wb') as void:
				result = subprocess.check_call(['/usr/bin/timedatectl', 'set-timezone', zone], stderr=void)
		except:
			logging.exception('Unable to change timezone')
			pass
		return result == 0
