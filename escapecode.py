import sublime
import sublime_plugin
import html
import os

def get_tab_size(view):
    return int(view.settings().get('tab_size', 8))

class EscapeCodeSnippetCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		current_caret = self.view.sel()
		pre_tag_locations = []
		previous_region = None
		for region in reversed(self.view.find_by_selector("text.html.basic meta.tag.block.any.html entity.name.tag.block.any.html")):
			# Keep track of the region in front of our current one
			if previous_region is None:
				previous_region = region
				continue

			# I only care about pre tags or else we'd select pre to inner tags if in-use
			# This means I can't do pre tag in a pre tag but I'm not going to run into that
			# scenario very often.
			tag = self.view.substr(region)
			if not tag == "pre":
				continue
			
			if current_caret[0].begin() > region.end() and current_caret[0].begin() < previous_region.begin():
				pre_tag_contents_region = sublime.Region(region.end() + 2, previous_region.begin() - 2)
				pre_tag_locations.append(pre_tag_contents_region)

			previous_region = region

			if current_caret[0].begin() > region.end():
				break

		# We now have the regions where pre>[0] ends and [1]</pre starts. 
		# Escape the content inbetween for HTML:
		modified_html = ""
		for region_to_escape in pre_tag_locations:
			unescaped = self.view.substr(region_to_escape)
			escaped = html.escape(unescaped)

			# then we need to handle whitespace indentation with HTML comments
			ending_line = self.view.substr(self.view.line(sublime.Region(region_to_escape.end(), region_to_escape.end())))
			
			# Tabs need to be converted to spaces so we can build the comment's dashes properly
			tab_size = get_tab_size(self.view)
			line_with_only_spaces = ending_line.expandtabs(tab_size)

			character_space_for_comment = line_with_only_spaces.find("</pre>")
			comment_dashes = "-" * (character_space_for_comment - 3)
			comment_prefix = f"<!{comment_dashes}---->" # align > with ending > of <pre>
			comment_prefix_endingline = f"<!{comment_dashes}>"

			region_lines = self.view.lines(region_to_escape)
			last_index = len(region_lines) - 1
			for index, line_region in enumerate(region_lines):
				if index == last_index:
					comment_prefix = comment_prefix_endingline
				
				padding_length = len(comment_prefix)

				this_line = self.view.substr(self.view.line(line_region))
				this_line_notabs = this_line.expandtabs(tab_size)

				# If the length of the line is smaller than the prefix, then we can ditch all whitespace
				space_at_start = 0
				for c in this_line_notabs:
					if c.isspace():
						space_at_start += 1
					else:
						break

				if space_at_start < padding_length:
					padding = " " * (padding_length - space_at_start)
					this_line_notabs = f"{padding}{this_line_notabs}"

				escaped = html.escape(this_line_notabs[len(comment_prefix):])
				new_line = f"{comment_prefix}{escaped}\n"
				if index == last_index:
					modified_html += comment_prefix
				else:
					modified_html += new_line

			self.view.replace(edit, region_to_escape, modified_html)
