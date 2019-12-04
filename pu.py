#!/usr/bin/python3

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import curses
from curses.textpad import rectangle
import time
import pulsectl

def find_player():
	while 1:
		sinks = pulse.sink_input_list()
		for sink in sinks:
#			if sink.proplist["application.process.binary"] == "kodi-wayland":
#			if sink.proplist["application.process.binary"] == "firefox":
			if sink.proplist["application.process.binary"] == "vlc":
				curses.nocbreak()
				pa_player_monitor = pulse.sink_info(sink.sink)
				return sink
		std_scr.addstr(1, 1, "No player found, waiting...", curses.color_pair(1))
		curses.halfdelay(50)
		std_scr.refresh()
		keypress_id = std_scr.getch()
		if keypress_id == ord('q'):
			curses.nocbreak()
			std_scr.keypad(False)
			curses.echo()
			curses.endwin()
			exit()

pulse = pulsectl.Pulse('mornalizer')
std_scr = curses.initscr()

curses.noecho()
curses.cbreak()
std_scr.keypad(True)
std_scr.nodelay(True)
curses.start_color()
curses.curs_set(0)
curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)

pa_player = find_player()
pa_player_monitor = pulse.sink_info(pa_player.sink)
current_volume = pulse.volume_get_all_chans(pa_player)
history_values = []
volume_limit = 1.1
step = 0.05
sample_size = 15
too_much = 8
cutoff = 0.45
range_max = 0.25
range_min = 0.05
sample_count = 0
loud = 0
quiet = 0

while 1:
	while curses.LINES < 6:
		std_scr.addstr(0, 0, "Terminal too short.")
		std_scr.refresh()
		curses.update_lines_cols()
		time.sleep(0.5)
		key_id = std_scr.getch()
		if key_id == ord('q'):
			curses.nocbreak()
			std_scr.keypad(False)
			curses.echo()
			curses.endwin()
			exit()

	try:
		peak = pulse.get_peak_sample(pa_player_monitor.monitor_source, 0.2, pa_player.index)
	except Exception as err:
		std_scr.addstr(1, 1, "Couldn't get peak - {0}. Resampling...".format(err))
		std_scr.refresh()
		pa_player = find_player()
		continue

	sample_count += 1
	history_values.append(peak)

	if peak < range_min:
		if peak > 0.001:
			quiet += 1
	elif peak > cutoff:
		current_volume -= (step * 2)
		try:
			pulse.volume_set_all_chans(pa_player, current_volume)
		except Exception as err:
			std_scr.addstr(1, 1, "Couldn't decrease volume - {0}. Resampling...".format(err))
			std_scr.refresh()
			pa_player = find_player()
	elif peak > range_max:
		loud += 1

	if sample_count == sample_size:
		sample_count = 0
		sum = 0
		pa_player = find_player()
		current_volume = pulse.volume_get_all_chans(pa_player)
		if quiet > too_much:
			current_volume += step
		elif loud > too_much:
			current_volume -= step
		else:
			for ite in range(len(history_values) - sample_size - 1, len(history_values) - 1):
				sum += history_values[ite]
			if sum > 0.1:
				if ((sum / sample_size) > (range_max - ((range_max - range_min) / 2))) and (quiet == 0):
					current_volume -= 0.01
				if ((sum / sample_size) < (range_max - ((range_max - range_min) / 2))) and (loud == 0):
					current_volume += 0.01
		quiet = 0
		loud = 0
		if current_volume > volume_limit:
			current_volume = volume_limit
		try:
			pulse.volume_set_all_chans(pa_player, current_volume)
		except Exception as err:
			std_scr.addstr(1, 1, "Couldn't change the volume - {0}. Resampling...".format(err))
			std_scr.refresh()
			pa_player = find_player()

	std_scr.clear()
	rectangle(std_scr, curses.LINES - 5 - round((curses.LINES - 5) * cutoff), 0, curses.LINES - 5 - round((curses.LINES - 5) * cutoff), curses.COLS-2)
	rectangle(std_scr, curses.LINES - 5 - round((curses.LINES - 5) * range_max), 0, curses.LINES - 5 - round((curses.LINES - 5) * range_max), curses.COLS-2)
	rectangle(std_scr, curses.LINES - 5 - round((curses.LINES - 5) * range_min), 0, curses.LINES - 5 - round((curses.LINES - 5) * range_min), curses.COLS-2)
	rectangle(std_scr, 0, 0, curses.LINES - 4, curses.COLS - 2)
	rectangle(std_scr, curses.LINES - 3, 0, curses.LINES - 1, curses.COLS - 2)
	history_entries = len(history_values)
	if history_entries > 500:
		history_values.pop(0)
		history_entries = len(history_values)
	if history_entries > curses.COLS - 2:
		history_start_visible = history_entries - curses.COLS + 2
	else:
		history_start_visible = 0
	for ite in range(history_start_visible, history_entries - 1):
		history_peak = history_values[ite]
		info_line = "Current peak {0:.3f}, current volume {1:.2f}, sample count {2:0>2}, loud {3:0>2}, quiet {4:0>2}".format(history_peak, current_volume, sample_count, loud, quiet)
		std_scr.addstr(curses.LINES - 2, 1, "{0: ^{width}}".format(info_line, width=curses.COLS - 3))
		if history_peak < range_min:
			dot_color = 2
		elif history_peak > cutoff:
			dot_color = 1
		elif history_peak > range_max:
			dot_color = 2
		else:
			dot_color = 3
		vertical_position = curses.LINES - 5 - round((curses.LINES - 5) * history_peak)
		horizontal_position = curses.COLS - len(history_values) + ite - 1
		previous_vertical_position = curses.LINES - 5 - round((curses.LINES - 5) * history_values[ite - 1])
		if vertical_position == previous_vertical_position:
			peak_symbol = '-'
		elif vertical_position > previous_vertical_position:
			peak_symbol = '\\'
		else:
			peak_symbol = '/'
		std_scr.addstr(vertical_position, horizontal_position, peak_symbol, curses.color_pair(dot_color))

	std_scr.refresh()
	curses.update_lines_cols()
	key_id = std_scr.getch()
	if key_id == ord('q'):
		break

curses.nocbreak()
std_scr.keypad(False)
curses.echo()
curses.endwin()
