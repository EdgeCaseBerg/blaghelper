import sublime
import sublime_plugin
import os
import subprocess
import webbrowser

folder_to_running_processes = {}
port_to_start_at = 35729



class StopAllLiveReloadServers(sublime_plugin.WindowCommand):
	def run(self):
		sublime.status_message("Shuting down all livereload servers")
		command = ["taskkill.exe", "/IM", "livereload.exe", "/F"]
		try:
			process = subprocess.Popen(
				command,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				shell=True
			)
			sublime.status_message(f"Stopped all livereload servers")
			global port_to_start_at
			port_to_start_at = 35729
			global folder_to_running_processes
			folder_to_running_processes = {}
			
		except Exception as e:
			sublime.error_message(f"Failed to run command: {e}")

def start_live_reload(folder_path):
	global port_to_start_at
	global folder_to_running_processes
	process_port = port_to_start_at

	if folder_path in folder_to_running_processes:
		sublime.status_message("livereload is running for this folder and will be restarted")
		[process, previously_used_port] = folder_to_running_processes[folder_path]
		process_port = previously_used_port
		process.kill()

	command = ["livereload.exe", "-p", f"{process_port}", folder_path]
	try:
		process = subprocess.Popen(
			command,
			cwd=os.path.dirname(folder_path),
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			shell=True
		)
		sublime.status_message(f"Started livereload.exe on port {process_port}")
		folder_to_running_processes[folder_path] = (process, process_port)
		if port_to_start_at == process_port:
			port_to_start_at += 1
		
	except Exception as e:
		sublime.error_message(f"Failed to run command: {e}")

class LiveReloadStartCommand(sublime_plugin.WindowCommand):
	def run(self):
		if not self.window.active_view():
			sublime.error_message("Window has no active view, cannot determine path to start server in")
			return

		sheet_file_name = self.window.active_sheet().file_name()
		if sheet_file_name is None:
			sublime.error_message("Could not determine folder for open file to run livereload for")
			return

		longest_path = None
		for folder in self.window.folders():
			in_common = os.path.commonprefix([sheet_file_name, folder])
			if longest_path is None or len(in_common) > len(longest_path):
				longest_path = in_common

		if longest_path is None:
			sublime.message_dialog("It appears this file is not in an open folder, add its folder to sublime and try again")
			return

		start_live_reload(longest_path)



class OpenInLiveReloadCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		if not self.view.file_name():
			return

		sheet_file_name = self.view.window().active_sheet().file_name()
		if sheet_file_name is None:
			sublime.error_message("Cannot open a file in the browser that has not been saved yet")
			return

		longest_path = None
		for folder in self.view.window().folders():
			in_common = os.path.commonprefix([sheet_file_name, folder])
			if longest_path is None or len(in_common) > len(longest_path):
				longest_path = in_common

		global folder_to_running_processes

		if longest_path not in folder_to_running_processes:
			sublime.status_message("No running live reload yet!")
			start_live_reload(longest_path)

		if longest_path not in folder_to_running_processes:
			sublime.error_message("Could not determine livereload process to run this file under")
			return

		[process, process_port] = folder_to_running_processes[longest_path]

		relative_file_path = os.path.relpath(self.view.file_name(), longest_path)
		web_path = "/".join(relative_file_path.split(os.sep))
		url = f"http://127.0.0.1:{process_port}/{web_path}"
		webbrowser.open_new_tab(url)

	def is_visible(self):
		return self.view.file_name() is not None and (
			self.view.file_name()[-5:] == ".html" or
			self.view.file_name()[-5:] == ".HTML" or
			self.view.file_name()[-4:] == ".htm" or
			self.view.file_name()[-4:] == ".HTM")
