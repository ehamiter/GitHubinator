# GitHubinator*
*_With regards to [Dr. Heinz Doofenshmirtz](http://en.wikipedia.org/wiki/Dr._Heinz_Doofenshmirtz)_

This will allow you to select text in a Sublime Text file, and see the highlighted lines on GitHub's remote repo, if one exists.

![Screenshot](http://i.imgur.com/lcJ78.png)


## Installation

If you use [Package Control](http://wbond.net/sublime_packages/package_control), just install it from there. If not:

Clone this repo to your Sublime Text Packages folder (ST3 example shown below):

    cd ~/"Library/Application Support/Sublime Text 3/Packages/"
    git clone https://github.com/ehamiter/GitHubinator.git

The plugin should be picked up automatically. If not, restart Sublime Text.


## Configuration

The defaults should work for most setups, but if you have a different remote name, use GitHub Enterprise or default branch, you can configure remote, host, and default branch in the `Githubinator.sublime-settings` file:

    {
      "default_remote": "origin",
      "default_host": "github.com",
      "default_branch": "master"
    }

## Usage

Select some text.
Activate the context menu and select "GitHubinator" or by keypress (&#8984;\\ by default, configurable in .sublime-keymap file).
