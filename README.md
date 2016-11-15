# GitHubinator*
*_With regards to [Dr. Heinz Doofenshmirtz](http://en.wikipedia.org/wiki/Dr._Heinz_Doofenshmirtz)_

[![git-brag-stats](https://labs.turbo.run/git-brag?user=ehamiter&repo=GitHubinator)](https://github.com/turbo/git-brag)  

This will allow you to select text in a Sublime Text file, and see the highlighted lines on GitHub's remote repo, if one exists.

![Screenshot](http://i.imgur.com/lcJ78.png)


## Installation

If you use [Package Control](http://wbond.net/sublime_packages/package_control), just install it from there. If not:

Clone this repo to your Sublime Text Packages folder (ST2 example shown below):

    cd ~/"Library/Application Support/Sublime Text 2/Packages/"
    git clone https://github.com/ehamiter/ST2-GitHubinator.git

The plugin should be picked up automatically. If not, restart Sublime Text.


## Configuration

The defaults should work for most setups, but if you have a different remote name or use GitHub Enterprise, you can configure remote and host in the `Githubinator.sublime-settings` file:

    {
      "default_remote": "origin",
      "default_host": "github.com"
    }


## Usage

Select some text.
Activate the context menu and select "GitHubinator" or by keypress (&#8984;\\ by default, configurable in .sublime-keymap file).
