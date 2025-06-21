import sublime
import sublime_plugin
import inspect

def plugin_loaded():
	print("blag: dynamic snippets loaded")

class DynamicSnippetsViewEventListener(sublime_plugin.ViewEventListener):
	def __init__(self, view):
		self.view = view
		self.footnote_snippet = inspect.cleandoc("""
			<li id="footnote-{0}">
			    $0
			    <a href="#footnote-{0}-ref">&#8617;</a>
			</li>
			""")
		self.footnote_ref_snippet = """<sup id="footnote-{0}-ref"><a href="#footnote-{0}">{0}</a></sup>$0"""
		self.number_of_footnotes_in_file = 0

	def calculate_footnote_count(self):
		footnotes_in_view = self.view.find_all("id=\"footnote-[0-9]+\"", sublime.FindFlags.WRAP)
		self.number_of_footnotes_in_file = len(footnotes_in_view)

	def footnote_completion(self):
		new_snippet = self.footnote_snippet.format(f"{self.number_of_footnotes_in_file + 1}")
		return sublime.CompletionItem(
			"blag_footnote",
			annotation = "A footnote for the bottom of the page",
			completion = new_snippet,
			completion_format = sublime.COMPLETION_FORMAT_SNIPPET,
			kind=sublime.KIND_SNIPPET
		)

	def footnote_ref_completion(self):
		new_snippet = self.footnote_ref_snippet.format(f"{self.number_of_footnotes_in_file + 1}")
		return sublime.CompletionItem(
			"blag_footref",
			annotation = "the anchor and sup combination",
			completion = new_snippet,
			completion_format = sublime.COMPLETION_FORMAT_SNIPPET,
			kind=sublime.KIND_SNIPPET
		)

	def on_query_completions(self, prefix, locations):
		for point in locations:
			in_html_scope = self.view.match_selector(point, "text.html.basic")
			if in_html_scope is False:
				return None

		if "blag" not in prefix:
			return None

		self.calculate_footnote_count()

		prefilled_snippets = [
			self.footnote_completion(),
			self.footnote_ref_completion()
		]
		return sublime.CompletionList(prefilled_snippets)
