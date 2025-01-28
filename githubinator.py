import codecs
import os
import re
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

        # Try to find a git directory
        git_worktree = self.recurse_dir(folder_name, ".git")
        if not git_worktree:
            sublime.status_message("Could not find .git directory.")
            return

        relative_git_worktree = folder_name[len(git_worktree):]

        # path names normalize for UNC styling
        if os.name == "nt":
            relative_git_worktree = relative_git_worktree.replace("\\", "/")
            file_name = file_name.replace("\\", "/")

        git_dir = os.path.join(git_worktree, ".git")

        is_linked_git = not os.path.isdir(git_dir)
        if is_linked_git:
            # we're in a linked Git repo (either a submodule or a worktree)
            with codecs.open(os.path.join(git_dir), "r", "utf-8") as git_link_file:
                # we need to get the link to the git folder from the .git file
                result = re.search(r"^gitdir: (.*) *$", git_link_file.read())
                if result:
                    matches = result.groups()
                    if matches[0]:
                        linked_path = matches[0]
                        if os.path.isabs(linked_path):
                            git_dir = linked_path
                        else:
                            git_dir = os.path.join(git_worktree, linked_path)
                        if git_dir.find("/.git/worktrees/"):
                            git_dir = re.sub(r'/.git/worktrees/[^/]+$', '/.git', git_dir)

        # Read the config file in .git
        git_config_path = os.path.join(git_dir, "config")
        with codecs.open(git_config_path, "r", "utf-8") as git_config_file:
            config = git_config_file.read()

        # Figure out the host
        # https://git-scm.com/book/en/v2/Git-on-the-Server-The-Protocols
        scheme = "https"
        result = re.search(r"url.*?=.*?((https?)://([^/]*)/)|(git@([^:]*):)", config)
        # Example: (None, None, None, 'git@github.com:', 'github.com')
        if result:
            matches = result.groups()
            if matches[0]:
                scheme = matches[1]
                self.default_host = matches[2]
            else:
                self.default_host = matches[4]

        re_host = re.escape(self.default_host)

        sha, current_branch = self.get_git_status(git_dir)
        if not branch:
            branch = current_branch

        target = sha if permalink or branch is None else branch
        target = quote_plus(target, safe="/")

        detected_remote = None
        # we can only do this search when we have a branch to work with.
        if branch is not None:
            regex = r".*\s.*(?:remote = )(\w+?)\r?\n"
            result = re.search(branch + regex, config)

            if result:
                matches = result.groups()
                detected_remote = [matches[0]]

        for remote in (detected_remote or self.default_remote):

            regex = r".*\s.*(?:https?://%s/|%s:|git://%s/)(.*)/(.*?)(?:\.git)?\r?\n" % (re_host, re_host, re_host)
            result = re.search(remote + regex, config)
            if not result:
                continue

            matches = result.groups()
            username = matches[0]
            project = matches[1]

            lines = self.get_selected_line_nums()

            repo_link = scheme + "://%s/%s/%s/" % (self.default_host, username, project)

            if open_repo:
                full_link = repo_link
            else:
                if "bitbucket" in self.default_host:
                    mode = "src" if mode == "blob" else "annotate"
                    lines = ":".join([str(l) for l in lines])
                    full_link = repo_link + "%s/%s%s/%s#cl-%s" % \
                        (mode, sha, relative_git_worktree, file_name, lines)
                elif "gitlab" in self.default_host:
                    lines = "-".join("%s" % line for line in lines)
                    full_link = repo_link + "%s/%s%s/%s#L%s" % \
                        (mode, target, relative_git_worktree, file_name, lines)
                else:
                    lines = "-".join("L%s" % line for line in lines)
                    full_link = repo_link + "%s/%s%s/%s#%s" % \
                        (mode, target, relative_git_worktree, file_name, lines)

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

    def get_git_status(self, git_dir):
        """Get the current branch and SHA from git.

        type: (str) -> (str, Optional[str])
        """
        ref = self.get_ref(git_dir)

        if not ref.startswith('refs/'):
            # we are in detached head mode and ref will be
            # `26e7c31036641177fa929e5a3ae925f214b23ed9`, instead of
            # `ref/heads/main`. So we're returning the sha when we return ref.
            return ref, None

        sha = self.get_sha_from_ref(git_dir, ref)
        if not sha:
            sha = self.get_sha_from_packed_refs(git_dir, ref)

        branch = ref.replace("refs/heads/", "")

        return sha, branch

    def get_ref(self, git_dir):
        head_path = os.path.join(git_dir, "HEAD")
        with open(head_path, "r") as f:
            # Something like "ref: refs/heads/main"
            return f.read().replace("ref: ", "")[:-1]

    def get_sha_from_packed_refs(self, git_dir, ref):
        """Get a sha from `.git/packed-refs`, useful if `.git/HEAD` is a tag

        `.git/packed-refs` is a list of commit hashes and their refs

        Example:
        # pack-refs with: peeled fully-peeled sorted
        0252a960f3cb3d93f1d080539f5be92efbc41200 refs/remotes/origin/main
        """
        packed_ref_path = os.path.join(git_dir, "packed-refs")

        if not os.path.isfile(packed_ref_path):
            return None
        regex = r"\s{0}(\s.*)?$".format(ref)
        with codecs.open(packed_ref_path, "r", "utf-8") as f:
            try:
                for line in f:
                    if re.search(regex, line):
                        return line.split(" ")[0]
            except UnicodeDecodeError:
                pass

    def get_sha_from_ref(self, git_dir, ref):
        ref_path = os.path.join(git_dir, ref)
        if not os.path.isfile(ref_path):
            return None
        with open(ref_path, "r") as f:
            return f.read().strip()

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
