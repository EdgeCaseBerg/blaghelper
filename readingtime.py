import sublime
import sublime_plugin
import inspect
from html.parser import HTMLParser

def plugin_loaded():
	print("blag: reading time tracker loaded")

class MyHTMLParser(HTMLParser):
	def __init__(self):
		super().__init__()
		self.reading_time = 0;
		self.words = 0;

	def handle_starttag(self, tag, attrs):
		# Restart the count!
		if tag == "main":
			self.words = 0;
			self.reading_time = 0

	def handle_endtag(self, tag):
		if tag == "main":
			self.reading_time = self.words / 200

	def handle_data(self, data):
		words = len(data.split())
		self.words += words

import sublime
import sublime_plugin


class UpdateReadingCommand(sublime_plugin.TextCommand):
	def run(self, edit, region_to_replace_start, region_to_replace_end, new_time_text):
		text = "            <small>Estimated reading time <span id=\"reading-time\">{0}</span></small>".format(new_time_text)
		self.view.replace(edit, sublime.Region(region_to_replace_start, region_to_replace_end), text)


class ReadingTimeViewEventListener(sublime_plugin.ViewEventListener):
	def __init__(self, view):
		self.view = view
		self.parser = MyHTMLParser()

	def make_human_reading_time(self, reading_time):
		how_many_five_minute_intervals = int(reading_time / 5)
		how_many_hours = int(reading_time / 60)
		out = []

		if how_many_hours > 0:
			out.append(f"{how_many_hours} hours")

		leftover_five_minutes = how_many_five_minute_intervals % 12
		if leftover_five_minutes > 0:
			out.append(f"{leftover_five_minutes * 5} minutes")

		if not out:
			return "Less than 5 minutes"

		return ", ".join(out)


	def on_pre_save(self):
		if not self.view.match_selector(0, "text.html"):
			return

		reading_time_symbols = [item for item in self.view.symbols() if item[1] == "reading-time"]
		if not reading_time_symbols:
			return

		
		full_region = sublime.Region(0, self.view.size())
		all_content = self.view.substr(full_region)
		self.parser.feed(all_content)

		[reading_time_region, _] = reading_time_symbols[0]
		reading_time_line_region = self.view.line(reading_time_region)

		new_time_text = self.make_human_reading_time(self.parser.reading_time)
		self.view.run_command("update_reading", {
			"region_to_replace_start": reading_time_line_region.begin(),
			"region_to_replace_end": reading_time_line_region.end(),
			"new_time_text": new_time_text
		})
