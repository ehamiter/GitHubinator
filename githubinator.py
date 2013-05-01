import os
import re
import sublime
import sublime_plugin


class GithubinatorCommand(sublime_plugin.TextCommand):
    '''This will allow you to highlight your code, activate the plugin, then see the
    highlighted results on GitHub.
    '''

    def load_config(self):
        s = sublime.load_settings("Githubinator.sublime-settings")
        global DEFAULT_GIT_REMOTE, DEFAULT_GITHUB_HOST
        DEFAULT_GIT_REMOTE = s.get("default_remote")
        if not isinstance(DEFAULT_GIT_REMOTE, list):
            DEFAULT_GIT_REMOTE = [DEFAULT_GIT_REMOTE]
        DEFAULT_GITHUB_HOST = s.get("default_host")
        if DEFAULT_GITHUB_HOST is None:
            DEFAULT_GITHUB_HOST = "github.com"
        

    def run(self, edit, permalink = False, mode = 'blob'):
        self.load_config()
        if not self.view.file_name():
            return

        full_name = os.path.realpath(self.view.file_name())
        folder_name, file_name = os.path.split(full_name)

        git_path = self.recurse_dir(folder_name, '.git')
        if not git_path:
            sublime.status_message('Could not find .git directory.')
            print('Could not find .git directory.')
            return

        git_config_path = os.path.join(git_path, '.git', 'config')
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

        re_host = re.escape(DEFAULT_GITHUB_HOST)
        for remote in DEFAULT_GIT_REMOTE:
            regex = r'.*\s.*(?:https://%s/|%s:|git://%s/)(.*)/(.*?)(?:\.git)?\r?\n' % (re_host, re_host, re_host)
            result = re.search(remote + regex, config)
            if not result:
                continue
            matches = result.groups()

            ref_path = open(os.path.join(git_path, '.git', 'HEAD'), "r").read().replace('ref: ', '')[:-1]
            branch = ref_path.replace('refs/heads/','')
            sha = open(os.path.join(git_path, '.git', ref_path), "r").read()[:-1]
            target = sha if permalink else branch

            full_link = 'https://%s/%s/%s/%s/%s%s/%s#L%s' % \
                (DEFAULT_GITHUB_HOST, matches[0], matches[1], mode, target, new_git_path, file_name, lines)
            sublime.set_clipboard(full_link)
            sublime.status_message('Copied %s to clipboard.' % full_link)
            print('Copied %s to clipboard.' % full_link)
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
