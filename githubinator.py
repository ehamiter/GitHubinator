import os
import re
import subprocess
import webbrowser

import sublime
import sublime_plugin

# The urllib module has been split into parts and renamed in Python 3 to urllib.parse
try:
    from urllib.parse import quote, quote_plus
except ImportError:
    from urllib import quote, quote_plus


class GithubinatorCommand(sublime_plugin.TextCommand):
    """
    This will allow you to highlight your code, activate the plugin, then see the
    highlighted results on GitHub/Bitbucket.
    """
    DEFAULT_GIT_REMOTE = "origin"
    DEFAULT_HOST = "github.com"
    DEFAULT_BRANCH = "main"

    def load_config(self):
        settings = sublime.load_settings("Githubinator.sublime-settings")
        self.default_remote = settings.get("default_remote") or self.DEFAULT_GIT_REMOTE

        if not isinstance(self.default_remote, list):
            self.default_remote = [self.default_remote]

        self.default_host = settings.get("default_host") or self.DEFAULT_HOST
        self.default_branch = settings.get("default_branch") or self.DEFAULT_BRANCH

    def run(self, edit, copyonly=False, permalink=False, mode="blob", default_branch=False, open_repo=False):
        self.load_config()
        branch = self.default_branch if default_branch else None

        if not self.view.file_name():
            return

        # The current file
        full_name = os.path.realpath(self.view.file_name())
        folder_name, file_name = os.path.split(full_name)

        try:
            # Path of the current folder relative to the repo root, like "src/"
            prefix = self.run_git(folder_name, "rev-parse", "--show-prefix")
            sha = self.run_git(folder_name, "rev-parse", "HEAD")
        except (OSError, subprocess.CalledProcessError):
            sublime.status_message("Could not find git repository.")
            return
        path = prefix + file_name

        current_branch = self.try_run_git(folder_name, "symbolic-ref", "--short", "HEAD")
        if not branch:
            branch = current_branch

        target = sha if permalink or branch is None else branch
        target = quote_plus(target, safe="/")

        detected_remote = None
        # we can only do this search when we have a branch to work with.
        if branch is not None:
            remote = self.try_run_git(folder_name, "config", "branch.%s.remote" % branch)
            if remote:
                detected_remote = [remote]

        for remote in (detected_remote or self.default_remote):
            url = self.try_run_git(folder_name, "remote", "get-url", remote)
            if not url:
                continue

            # https://git-scm.com/docs/git-clone#_git_urls
            # Examples: https://github.com/user/project.git, git@github.com:user/project.git
            result = re.match(r"^(?:(\w+)://)?(?:[^@/]+@)?([^/:]+)(?::\d+)?[:/](.+?)(?:\.git)?/?$", url)
            if not result:
                continue
            url_scheme, self.default_host, repo_path = result.groups()
            scheme = "http" if url_scheme == "http" else "https"

            lines = self.get_selected_line_nums()

            repo_link = scheme + "://%s/%s/" % (self.default_host, repo_path)

            if open_repo:
                full_link = repo_link
            else:
                if "bitbucket" in self.default_host:
                    mode = "src" if mode == "blob" else "annotate"
                    lines = ":".join([str(l) for l in lines])
                    full_link = repo_link + "%s/%s/%s#cl-%s" % (mode, sha, path, lines)
                elif "gitlab" in self.default_host:
                    lines = "-".join("%s" % line for line in lines)
                    full_link = repo_link + "%s/%s/%s#L%s" % (mode, target, path, lines)
                else:
                    lines = "-".join("L%s" % line for line in lines)
                    full_link = repo_link + "%s/%s/%s#%s" % (mode, target, path, lines)

            full_link = quote(full_link, safe=':/#@')

            sublime.set_clipboard(full_link)
            sublime.status_message("Copied %s to clipboard." % full_link)

            if not copyonly:
                webbrowser.open_new_tab(full_link)

            break

    def get_selected_line_nums(self):
        """Get the line number of selections."""
        sel = self.view.sel()[0]
        begin = self.view.rowcol(sel.begin())
        end = self.view.rowcol(sel.end())

        begin_line = begin[0] + 1

        # Unless both regions are the same (meaning nothing is highlighted),
        # if the column index of the end of the selection is 0, that means the user has selected up to and including the EOL character
        # We don't want to increment `end_line` in that case, because it will highlight the line after the EOL character.
        end_line = end[0] + 1 if (begin == end) or end[1] != 0 else end[0]

        if begin_line == end_line:
            lines = [begin_line]
        else:
            lines = [begin_line, end_line]

        return lines

    def run_git(self, cwd, *args):
        startupinfo = None
        if os.name == "nt":
            # Don't flash a console window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        output = subprocess.check_output(
            ("git",) + args, cwd=cwd, stderr=subprocess.DEVNULL, startupinfo=startupinfo
        )
        return output.decode("utf-8").strip()

    def try_run_git(self, cwd, *args):
        """Like `run_git`, but return None if the command fails."""
        try:
            return self.run_git(cwd, *args) or None
        except subprocess.CalledProcessError:
            return None

    def recurse_dir(self, path, folder):
        """Traverse through parent directories until we find `folder`, starting
        in `path`"""
        items = os.listdir(path)
        # Is `folder` a directory in the current path?
        if folder in items:
            return path
        # Check the parent directory
        dirname = os.path.dirname(path)
        # See if we're at root
        if dirname == path:
            return None
        # Recurse the parent directory
        return self.recurse_dir(dirname, folder)

    def is_enabled(self):
        """Enable command only for files under git repos."""
        if not self.view.file_name():
            return False

        full_name = os.path.realpath(self.view.file_name())
        git_path = self.recurse_dir(os.path.dirname(full_name), ".git")
        if git_path:
            return True
        else:
            return False
