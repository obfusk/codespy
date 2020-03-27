<!-- {{{1 -->

    File        : README.md
    Maintainer  : Felix C. Stegerman <flx@obfusk.net>
    Date        : 2020-03-27

    Copyright   : Copyright (C) 2020  Felix C. Stegerman
    Version     : v0.0.1
    License     : AGPLv3+

<!-- }}}1 -->

<!-- TODO: badges -->

[![AGPLv3+](https://img.shields.io/badge/license-AGPLv3+-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

## Description

codespy - cooperative spy code

Codespy is a web-based clone of the cooperative board game "Codenames
Duet".

## Installing

Just `git clone` :)

## Requirements

Python (>= 3.5) & Flask & regex.

### Debian

```bash
$ apt install python3-flask python3-regex
```

### pip

```bash
$ pip3 install --user Flask   # for Debian; on other OS's you may need
                              # pip instead of pip3 and/or no --user
$ pip3 install --user regex
```

## Running

### Flask

```bash
$ FLASK_APP=codes.py flask run
```

### Gunicorn

```bash
$ gunicorn codes:app
```

### Heroku

Just `git push` :)

NB: you'll need to set `WEB_CONCURRENCY=1` b/c it only works
single-theaded atm!

### Password

```bash
$ export CODESPY_PASSWORD=swordfish
```

### Forcing HTTPS

```bash
$ export CODESPY_HTTPS=force
```

## License

### Code

© Felix C. Stegerman

[![AGPLv3+](https://www.gnu.org/graphics/agplv3-155x51.png)](https://www.gnu.org/licenses/agpl-3.0.html)

### Word lists

(i.e. `words/*`)

See [`words/COPYING`](words/COPYING).

<!-- vim: set tw=70 sw=2 sts=2 et fdm=marker : -->
