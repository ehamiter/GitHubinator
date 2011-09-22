import os
import re
import sublime
import sublime_plugin


class GithubinatorCommand(sublime_plugin.TextCommand):
    '''This will allow you to highlight your code, activate the plugin, then see the
    highlighted results on GitHub.
    '''

    def run(self, edit):
        if not self.view.file_name():
            return

        full_name = self.view.file_name()
        folder_name, file_name = os.path.split(full_name)

        git_path = self.recurse_dir(folder_name,'.git')
        if not git_path:
            sublime.status_message('Could not find .git directory.')
            print 'Could not find .git directory.'
            return

        git_head_path = os.path.join(git_path,'.git','HEAD')
        with open(git_head_path, "r") as git_head_file:
            head = git_head_file.read()

        git_config_path = os.path.join(git_path,'.git','config')
        new_git_path = folder_name[len(git_path):]

        with open(git_config_path, "r") as git_config_file:
            config = git_config_file.read()

        sel = self.view.sel()[0]
        begin_line = self.view.rowcol(sel.begin())[0] + 1
        end_line = self.view.rowcol(sel.end())[0] + 1
        if begin_line == end_line:
            lines = begin_line
        else:
            lines = '%s-%s' % (begin_line, end_line)

        for remote in ['mainline', 'origin']:
            regex = r'.*\s.*(?:https://github\.com/|github\.com:)(.*)/(.*?)(?:\.git)?\r?\n'
            result = re.search(remote + regex, config)
            if not result:
                continue
            matches = result.groups()

            head_regex = r'(ref:\srefs/heads/)*(.*)'
            head_result = re.search(head_regex, head)

            if head_result:
                head_matches = head_result.groups()
                branch = head_matches[1]
            else:
                branch = 'master'

            full_link = 'https://github.com/%s/%s/blob/%s%s/%s#L%s' % \
                (matches[0], matches[1], branch, new_git_path, file_name, lines)
            sublime.set_clipboard(full_link)
            sublime.status_message('Copied %s to clipboard.' % full_link)
            print 'Copied %s to clipboard.' % full_link
            self.view.window().run_command('open_url', {"url": full_link})
            break


    def recurse_dir(self, path, folder):
        items = os.listdir(path)
        if folder in items and os.path.isdir(os.path.join(path, folder)):
            return path
        dirname = os.path.dirname(path)
        if dirname == path:
            return None
        return self.recurse_dir(dirname, folder)


    def is_enabled(self):
        return self.view.file_name() and len(self.view.file_name()) > 0
