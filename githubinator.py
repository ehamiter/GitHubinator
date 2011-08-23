import os
import re
import webbrowser
import sublime
import sublime_plugin


class GithubinatorCommand(sublime_plugin.TextCommand):
    '''This will allow you to highlight your code, activate the plugin, then see the 
    highlighted results on GitHub.
    '''

    def run(self, edit):
        if len(self.view.file_name()) > 0:
            full_name = self.view.file_name()
            folder_name, file_name = os.path.split(full_name)
            begin_line, begin_column = self.view.rowcol(self.view.sel()[0].begin())
            end_line, end_column = self.view.rowcol(self.view.sel()[0].end())
            begin_line = str(begin_line + 1)
            end_line = str(end_line + 1)

            git_path = self.recurse_dir(folder_name,'.git')
            if git_path:
                git_config_path = os.path.join(git_path,'.git','config')
                new_git_path = folder_name[len(git_path):]           

                git_config_file = open(git_config_path, "r")
                config = git_config_file.read()
                git_config_file.close()
                config = str(config)

                mainline = re.search(r'mainline.*\s.*:(.*)/(.*)\.', config)
                origin = re.search(r'origin.*\s.*:(.*)/(.*)\.', config)
                gitrdone = None

                if mainline:
                    gitrdone = list(mainline.groups())
                elif origin:
                    gitrdone = list(origin.groups())
                else:
                    pass

                if gitrdone:
                    gitrdone[:] = ['/'.join(gitrdone[:])]
                    gitrdone = str(gitrdone).strip("[']")

                if begin_line == end_line:
                    lines = begin_line
                else:
                    lines = '%s-%s' % (begin_line, end_line)

            if git_path and gitrdone:
                for region in self.view.sel():
                    git_link = 'https://github.com/%s/blob/master%s' % (gitrdone, new_git_path)
                    full_link = '%s/%s#L%s' % (git_link, file_name, lines)
                    sublime.set_clipboard(full_link)
                    sublime.status_message('Copied %s to clipboard.' % full_link)
                    print 'Copied %s to clipboard.' % full_link
                    webbrowser.open_new_tab(full_link)
            else:
                sublime.status_message('Could not find .git directory.')
                print 'Could not find .git directory.'
        else:
            pass


    def recurse_dir(self, path, folder):
        items = os.listdir(path)
        if folder in items and os.path.isdir(os.path.join(path, folder)):
            return path
        else:
            return self.recurse_dir(os.path.dirname(path), folder) if '/' != path else None


    def is_enabled(self):
        return self.view.file_name() and len(self.view.file_name()) > 0
