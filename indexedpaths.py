import sublime
import sublime_plugin
import os
import sys
import tracemalloc
import timeit
from functools import cached_property, wraps
from collections import deque

href_files = []
known_files_tracker = {}

ENABLE_MEM_COUNT = False
ENABLE_TIMING = False
CURRENT_KIND = (sublime.KindId.COLOR_BLUISH, "➘", "Link Expansion")

def timing(func):
    @wraps(func)
    def wrap(*args, **kw):
        if ENABLE_TIMING:
            ts = timeit.default_timer()
        result = func(*args, **kw)
        if ENABLE_TIMING:
            te = timeit.default_timer()
            info = f"{func.__name__}({args}, {kw}) took: {1000.0 * (te - ts):2.3f} ms"
            print(info)
        return result
    return wrap

# https://docs.python.org/3/library/tracemalloc.html#tracemalloc.start
def memoryusage(func):
	@wraps(func)
	def wrap(*args, **kw):
		if ENABLE_MEM_COUNT:
			tracemalloc.start()
			(current_start, peak_1) = tracemalloc.get_traced_memory()
		result = func(*args, **kw)
		if ENABLE_MEM_COUNT:
			(curent_end, peak_2) = tracemalloc.get_traced_memory()
			tracemalloc.stop()
			info = f"{func.__name__}({args}, {kw}) start:{current_start} stop:{curent_end} peaks: {peak_1} {peak_2}"
			print(info)

		return result
	return wrap

class ReindexFoldersCommand(sublime_plugin.WindowCommand):
	def run(self):
		for window in sublime.windows():
			for folder in window.folders():
				add_files_to_suggestions(folder)

@timing
def plugin_loaded():
	for window in sublime.windows():
		for folder in window.folders():
			add_files_to_suggestions(folder)
	sublime.status_message("HrefHelper context loaded")

@memoryusage
def add_files_to_suggestions(folder):
	for root, dirs, filenames in os.walk(folder):
		for handle in filenames:
			full_path = os.path.join(root, handle)
			# Skip if we know about this already
			if full_path is None:
				continue

			if full_path in known_files_tracker:
				continue

			relative = os.path.relpath(full_path, folder)
			file_href_path = relative.replace(os.sep, "/")

			# We could make this a setting for the plugin
			if file_href_path[0] != ".":
				href_files.append(completion_for(handle, file_href_path))
				href_files.append(completion_for(file_href_path, file_href_path))
				known_files_tracker[full_path] = 0
	sublime.status_message(f"Loaded {folder} to href context")

def completion_for(handle, file_href_path):
	annotation = f"/{file_href_path}"
	details = f"""Will expand to <strong>{annotation}</strong>"""
	return sublime.CompletionItem(
		handle, # trigger (Text to match against the user input)
		annotation, # hint to the right of text
		annotation, # completion to insert
		sublime.CompletionFormat.TEXT, # insert as is, no snippet
		CURRENT_KIND,
		details
	)

class IndexedFilesCompletionsViewEventListener(sublime_plugin.ViewEventListener):
	def on_query_completions(self, prefix, locations):
		# If someone is using multicursors, ensure all cursors
		# are within the correct context before we offer ourselves
		# as an option
		for point in locations:
			in_html_scope = self.view.match_selector(point, "text.html.basic")
			if in_html_scope is False:
				return None

			in_meta = self.view.match_selector(point, "meta.string.html")
			if in_meta is False:
				return None

			in_href = self.view.match_selector(point, "meta.attribute-with-value.href.html")
			if in_href is False:
				return None

		return sublime.CompletionList(href_files)


