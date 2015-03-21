import os
import re
import sublime
import sublime_plugin


class GithubinatorCommand(sublime_plugin.TextCommand):
    '''
    This will allow you to highlight your code, activate the plugin, then see the
    highlighted results on GitHub/Bitbucket.
    '''

    def load_config(self):
        s = sublime.load_settings("Githubinator.sublime-settings")
        global DEFAULT_GIT_REMOTE, DEFAULT_HOST

        DEFAULT_GIT_REMOTE = s.get("default_remote")
        if DEFAULT_GIT_REMOTE is None:
            DEFAULT_GIT_REMOTE = ["origin"]

        if not isinstance(DEFAULT_GIT_REMOTE, list):
            DEFAULT_GIT_REMOTE = [DEFAULT_GIT_REMOTE]

        DEFAULT_HOST = s.get("default_host")
        if DEFAULT_HOST is None:
            DEFAULT_HOST = "github.com"

    def run(self, edit, copyonly=False, permalink=False, mode='blob', branch=None):
        self.load_config()

        if not self.view.file_name():
            return

        # The current file
        full_name = os.path.realpath(self.view.file_name())
        folder_name, file_name = os.path.split(full_name)

        # Try to find a git directory
        git_path = self.recurse_dir(folder_name, '.git')
        if not git_path:
            sublime.status_message('Could not find .git directory.')
            return

        new_git_path = folder_name[len(git_path):]

        # Read the config file in .git
        git_config_path = os.path.join(git_path, '.git', 'config')
        with open(git_config_path, "r") as git_config_file:
            config = git_config_file.read()

        # Figure out the host
        HTTP = 'https'
        result = re.search(r'url.*?=.*?((https?)://([^/]*)/)|(git@([^:]*):)', config)
        if result:
            matches = result.groups()
            if matches[0]:
                HTTP = matches[1]
                DEFAULT_HOST = matches[2]
            else:
                DEFAULT_HOST = matches[4]

        re_host = re.escape(DEFAULT_HOST)

        for remote in DEFAULT_GIT_REMOTE:

            regex = r'.*\s.*(?:https?://%s/|%s:|git://%s/)(.*)/(.*?)(?:\.git)?\r?\n' % (re_host, re_host, re_host)
            result = re.search(remote + regex, config)
            if not result:
                continue

            sha, branch = self.get_git_status(git_path)
            target = sha if permalink else branch

            matches = result.groups()
            username = matches[0]
            project = matches[1]

            lines = self.get_selected_line_nums()

            if 'bitbucket' in DEFAULT_HOST:
                full_link = HTTP + '://%s/%s/%s/src/%s%s/%s?at=%s#cl-%s' % \
                    (DEFAULT_HOST, username, project, sha, new_git_path,
                        file_name, branch, lines)
            else:
                full_link = HTTP + '://%s/%s/%s/%s/%s%s/%s#L%s' % \
                    (DEFAULT_HOST, username, project, mode, target, new_git_path,
                        file_name, lines)

            sublime.set_clipboard(full_link)
            sublime.status_message('Copied %s to clipboard.' % full_link)

            if not copyonly:
                self.view.window().run_command('open_url', {"url": full_link})

            break

    def get_selected_line_nums(self):
        """Get the line number of selections."""
        sel = self.view.sel()[0]
        begin_line = self.view.rowcol(sel.begin())[0] + 1
        end_line = self.view.rowcol(sel.end())[0] + 1

        if begin_line == end_line:
            lines = begin_line
        else:
            lines = '%s-%s' % (begin_line, end_line)

        return lines

    def get_git_status(self, git_path):
        """Get the current branch and SHA from git."""

        with open(os.path.join(git_path, '.git', 'HEAD'), "r") as f:
            ref = f.read().replace('ref: ', '')[:-1]

        with open(os.path.join(git_path, '.git', ref), "r") as f:
            sha = f.read()[:-1]

        branch = ref.replace('refs/heads/', '')

        return sha, branch

    def recurse_dir(self, path, folder):
        items = os.listdir(path)
        if folder in items and os.path.isdir(os.path.join(path, folder)):
            return path
        dirname = os.path.dirname(path)
        if dirname == path:
            return None
        return self.recurse_dir(dirname, folder)

    def is_enabled(self):
        if self.view.file_name() and len(self.view.file_name()) > 0:
            return True
        else:
            return False
