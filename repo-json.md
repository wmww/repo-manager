# repo.json format

`repo-manager` can be used to initialize repositories. Repository configuration is in a directory (somewhere other than where the repository is cloned). It contains a `repo.json` files, and optionally other files. See [wmww/personal](https://github.com/wmww/personal/tree/master/repos) for an example. All files including `repo.json` are symlinked into the cloned repo. `repo.json` contains a JSON object, with the following keys:

## `remotes`
An object where keys are names of remotes and values are the URLs

## `origin`
A string that hold the origin remote URL. Can only be used if `remotes` is empty or unspecified.

## `exclude`
An array of strings, where each string is one line in the repo's `.git/info/exclude` file. The lines added to the exclude file start with `# <repo-manager>` and end with `# </repo-manager>`.

## `name`
Name of the repo, defaults to the name of the directory the `repo.json`, or the origin remote URL.

## '//` (comment)
Like npm, repo-manager allows a `//` key for comments
