import sublime
import sublime_plugin
import inspect
from email.utils import formatdate

def plugin_loaded():
	print("blag: dynamic snippets loaded")

class DynamicHtmlSnippets(sublime_plugin.ViewEventListener):
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

		self.new_section_snippet= inspect.cleandoc("""
		<section id="section-{0}">
		    <h2>$1 <a href="#toc">&#8617;</a></h2>
		    <p>
		        $0
		    </p>
		</section>
		""")
		self.number_of_sections_in_file = 0

	def calculate_footnote_count(self):
		footnotes_in_view = self.view.find_all("id=\"footnote-[0-9]+\"", sublime.FindFlags.WRAP)
		self.number_of_footnotes_in_file = len(footnotes_in_view)

	def calculate_section_count(self):
		sections_in_view = self.view.find_all("<section id=\"section-[0-9]+\">", sublime.FindFlags.WRAP)
		self.number_of_sections_in_file = len(sections_in_view)

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

	def new_section_completion(self):
		new_snippet = self.new_section_snippet.format(f"{self.number_of_sections_in_file + 1}")
		return sublime.CompletionItem(
			"blag_section",
			annotation = "a new section",
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
		self.calculate_section_count()

		prefilled_snippets = [
			self.footnote_completion(),
			self.footnote_ref_completion(),
			self.new_section_completion()
		]
		return sublime.CompletionList(prefilled_snippets)


class DynamicXmlSnippets(sublime_plugin.ViewEventListener):
	def __init__(self, view):
		self.view = view
		self.feeditem_snipet = inspect.cleandoc("""
			<item>
				<title>$1</title>
				<link>$2</link>
				<guid>$2</guid>
				<pubDate>{0}</pubDate>
				<description>
					![CDATA[
						$0
					]]
				</description>
			</item>
			""")

	def new_feed_item_completion(self):
		# Current time in RFC 822 format for RSS
		todays_date_in_gmt = formatdate(timeval=None, localtime=False, usegmt=True)
		new_snippet = self.feeditem_snipet.format(f"{todays_date_in_gmt}")
		return sublime.CompletionItem(
			"blag_xml_item",
			annotation = "a new rss item",
			completion = new_snippet,
			completion_format = sublime.COMPLETION_FORMAT_SNIPPET,
			kind=sublime.KIND_SNIPPET
		)		

	def on_query_completions(self, prefix, locations):
		for point in locations:
			in_xml_scope = self.view.match_selector(point, "text.xml")
			if in_xml_scope is False:
				return None

		if "blag" not in prefix:
			return None

		prefilled_snippets = [
			self.new_feed_item_completion()
		]
		return sublime.CompletionList(prefilled_snippets)
