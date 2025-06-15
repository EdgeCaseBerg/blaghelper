import sublime
import sublime_plugin
import os
import sys
import tracemalloc
import timeit
from functools import cached_property, wraps
from collections import deque

href_files = []
known_files_tracker = PathTrie()

ENABLE_MEM_COUNT = False
ENABLE_TIMING = False
CURRENT_KIND = (sublime.KindId.COLOR_BLUISH, "➘", "Link Expansion")

class PathTrieNode:
	def __init__(self):
		self.children = {}
		self.is_end_of_path = False

class PathTrie:
	def __init__(self):
		self.root = PathTrieNode()
		self.seperator = os.sep

	def insert(self, path):
		node = self.root
		parts = path.split(self.seperator)
		for path_part in parts:
			node = node.children.setdefault(path_part, PathTrieNode())
		node.is_end_of_path = True

	@timing
	def contains(self, path):
		node = self.root
		parts = path.split(self.seperator)
		for path_part in parts:
			if path_part in node.children:
				node = node.children[path_part]
			else:
				return False
		return node.is_end_of_path

	def remove(self, path):
		# This is a sweep the broom back and forth approach
		# where we go to the child, while tracking where we
		# were, and then sweep back and decide to drop the
		# entire Trie branch if there's no more children or similar
		parents = deque()
		node = self.root
		parts = path.split(self.seperator)
		for part in path_parts:
			if part not in node.children:
				# It's not in the Trie in the first place, piss off
				return
			parents.appendleft((node, part))
			node = node.children[part]

		if not node.is_end_of_path:
			# If the path drops us off without a file at the end
			# then there's not really anything to be done here.
			return

		# But if we ARE at the end, then it's time to clean up!
		# Congrats, you are not the father:
		node.is_end_of_path = False

		# Let's walk back up and see if we can trim the branches
		for parent, part in parents:
			child = parent.children[part]
			if child.is_end_of_path or child.children:
				# The child is a terminal (not likely)
				# or the child has other files in it (likely)
				break
			del parent.children[part]

		# Done! 

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

def total_size(obj, seen=None):
    """Recursively calculate total memory size of an object and its contents."""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)

    if isinstance(obj, dict):
        size += sum(total_size(k, seen) + total_size(v, seen) for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set)):
        size += sum(total_size(i, seen) for i in obj)
    elif hasattr(obj, "__dict__"):
        size += total_size(obj.__dict__, seen)
    elif hasattr(obj, "__slots__"):
        size += sum(total_size(getattr(obj, slot), seen) for slot in obj.__slots__ if hasattr(obj, slot))

    return size

@timing
def plugin_loaded():
	for window in sublime.windows():
		for folder in window.folders():
			add_files_to_suggestions(folder)
	sublime.status_message("HrefHelper context loaded")

def add_files_to_suggestions(folder):
	for root, dirs, filenames in os.walk(folder):
		for handle in filenames:
			full_path = os.path.join(root, handle)
			# Skip if we know about this already
			if known_files_tracker.contains(full_path):
				continue

			relative = os.path.relpath(full_path, folder)
			file_href_path = relative.replace("\\", "/")

			# We could make this a setting for the plugin
			if file_href_path[0] != ".":
				href_files.append(completion_for(handle, file_href_path))
				href_files.append(completion_for(file_href_path, file_href_path))
				known_files_tracker.insert(full_path)
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

class HrefCommand(sublime_plugin.ViewEventListener):
	def on_activated_async(self):
		active_view = sublime.active_window().active_view()
		if active_view is None:
			return

		file_name = active_view.file_name()
		if known_files_tracker.contains(file_name):
			return

		handle = file_name.split(os.sep)[-1]
		inside_folder = False
		found_folder = None
		for window in sublime.windows():
			for folder in window.folders():
				try:
					common = os.path.commonpath([file_name, folder])
					if common == folder:
						inside_folder = True
						found_folder = folder
				except ValueError as e:
					print(e)
				
				

		if not inside_folder:
			# We have a file that is not inside any folder in sublime,
			# this means it's just a loose file and we have no way
			# to make a sensible url to it, so skip it.
			return

		# If we've hit this point, then the file is inside of a folder
		# that's open sublime, but we haven't indexed it. This might
		# mean it's a new file create in an existing folder, or there's
		# a brand new folder added to the sublime project we need to index
		# so go ahead and do that, the Trie contains check will prevent
		# dupes!
		add_files_to_suggestions(found_folder)

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
