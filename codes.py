#!/usr/bin/python3
# encoding: utf-8

# --                                                            ; {{{1
#
# File        : codes.py
# Maintainer  : Felix C. Stegerman <flx@obfusk.net>
# Date        : 2020-03-26
#
# Copyright   : Copyright (C) 2020  Felix C. Stegerman
# Version     : v0.0.1
# License     : AGPLv3+
#
# --                                                            ; }}}1

# NB: only works single-threaded!

# TODO:
# * ...

import functools, itertools, os, random, secrets, time

import jinja2
import regex

from flask import Flask, jsonify, redirect, request, \
                  render_template, url_for

# === logic ===

POLL  = 1000
LANGS = "green british dutch".split()

class Oops(RuntimeError):
  def msg(self): return self.args[0]
class InProgress(Oops):
  def __init__(self): super().__init__("in progress")
class InvalidAction(Oops): pass
class InvalidParam(Oops):
  def msg(self): return "invalid parameter: " + self.args[0]

word_ok = regex.compile(r"^[\p{L}-]+$").match

# load words from disk
WORDS = {}
for lang in LANGS:
  with open("words/" + lang) as f:
    WORDS[lang] = [ word.strip() for word in f if word_ok(word) ]

# global state
games = {}

def current_game(game):
  return games[game]

def restart_game(game):
  del games[game]

def update_game(game, new):
  cur = current_game(game)
  cur.update(new, tick = max(cur["tick"] + 1, int(time.time())))

def valid_ident(s):
  return s and s.isprintable() and all( not c.isspace() for c in s )

def random_words(lang):
  words = random.sample(WORDS[lang], 25)
  return set(words), tuple(itertools.zip_longest(*([iter(words)] * 5)))

# NB: mutates!
def take_random(s, n):
  t = set(random.sample(s, n))
  s -= t
  return t

def random_key(words):
  words           = words.copy()
  green           = take_random(words, 3)
  black           = take_random(words, 1)
  green_a_black_b = take_random(words, 1)
  green_b_black_a = take_random(words, 1)
  black_a_white_b = take_random(words, 1)
  black_b_white_a = take_random(words, 1)
  green_a_white_b = take_random(words, 5)
  green_b_white_a = take_random(words, 5)
  return dict(
    a = dict( green = green | green_a_black_b | green_a_white_b,
              black = black | black_a_white_b | green_b_black_a,
              white = words | black_b_white_a | green_b_white_a ),
    b = dict( green = green | green_b_black_a | green_b_white_a,
              black = black | black_b_white_a | green_a_black_b,
              white = words | black_a_white_b | green_a_white_b )
  )

def other_side(side):
  return dict(a = "b", b = "a")[side]

def player_data(cur):
  pa = [ p for p, s in cur["players"].items() if s == "a" ]
  pb = [ p for p, s in cur["players"].items() if s == "b" ]
  return pa, pb

def init_game(game, name, side = None, lang = None):
  if game not in games:
    if lang not in LANGS: raise ValueError("lang must be in LANGS")
    words, grid = random_words(lang)
    games[game] = dict(
      lang = lang, grid = grid, key = random_key(words),
      green = set(), white_a = set(), white_b = set(), players = {},
      side = None, hint = None, game_over = False, tick = 0
    )
  cur = current_game(game)
  if name not in cur["players"]:
    if cur["hint"]: raise InProgress()    # in progress -> can't join
    if side not in ["a", "b"]:
      raise ValueError('side must be "a" or "b"')
    return dict(players = { **cur["players"], name: side })
  return None

def leave_game(game, name):
  cur = current_game(game)
  if cur["hint"]: raise InProgress()      # in progress -> can't leave
  players = { p: s for p, s in cur["players"].items() if p != name }
  return dict(players = players)

def start_game(cur, name):
  pa, pb = player_data(cur)
  if not pa or not pb: raise InvalidAction("missing side(s)")
  return dict(side = other_side(cur["players"][name]))

def give_hint(cur, name, hint):
  if cur["hint"]: raise InvalidAction("existing hint")
  if cur["players"][name] != other_side(cur["side"]):
    raise InvalidAction("wrong side")
  return dict(hint = hint)

def make_guess(cur, name, word):
  if not cur["hint"]: raise InvalidAction("no hint")
  side = cur["players"][name]; ws = "white_" + side
  if side != cur["side"]: raise InvalidAction("wrong side")
  if word in cur["green"] or word in cur[ws]:
    raise InvalidAction("already guessed")
  key = cur["key"][side]
  if word in key["black"]:
    return dict(game_over = True)
  elif word in key["green"]:
    return dict(green = cur["green"] | set([word]))
  elif word in key["white"]:
    new = give_up(cur, name)
    return { ws : cur[ws] | set([word]), **new }
  else:
    raise InvalidAction("word not in play")

def give_up(cur, name):
  if not cur["hint"]: raise InvalidAction("no hint")
  if cur["players"][name] != cur["side"]:
    raise InvalidAction("wrong side")
  return dict(hint = None, side = other_side(cur["side"]))

def colour_of(cur, name, word):
  side  = cur["side"]
  white = cur["white_" + side]
  return "green" if word in cur["green"] else \
         "white" if word in white else "yellow"

def key_of(cur, name, word):
  side  = cur["players"][name]
  key   = cur["key"][other_side(side)]
  return "green" if word in key["green"] else \
         "black" if word in key["black"] else "white"

def data(cur, game, name):
  return dict(
    cur = cur, game = game, name = name, players = player_data(cur),
    your_side = cur["players"][name] == cur["side"],
    side = cur["side"], hint = cur["hint"], tick = cur["tick"],
    POLL = POLL, colour_of = colour_of, key_of = key_of
  )

# === http ===

app = Flask(__name__)

if os.environ.get("CODESPY_HTTPS") == "force":
  @app.before_request
  def https_required():
    if request.scheme != "https":
      return redirect(request.url.replace("http:", "https:"), code = 301)
  @app.after_request
  def after_request_func(response):
    response.headers["Strict-Transport-Security"] = 'max-age=63072000'
    return response

if os.environ.get("CODESPY_PASSWORD"):
  PASSWORD = os.environ.get("CODESPY_PASSWORD")
  @app.before_request
  def auth_required():
    auth = request.authorization
    if not auth or auth.password != PASSWORD:
      m = "Password required."
      return m, 401, { "WWW-Authenticate": 'Basic realm="'+m+'"' }

@app.route("/")
def r_index():
  args = request.args
  game = args.get("game") or secrets.token_hex(10)
  return render_template(
    "index.html", game = game, name = args.get("name"),
    join = "join" in args, langs = LANGS
  )

@app.route("/status/<game>")
def r_status(game):
  return jsonify(dict(tick = current_game(game)["tick"]))

@app.route("/play", methods = ["POST"])
def r_play():
  form        = request.form
  action      = form.get("action")
  game, name  = form.get("game"), form.get("name")
  side, lang  = form.get("side"), form.get("lang")
  hint, word  = form.get("hint"), form.get("word")
  try:
    if not valid_ident(game): raise InvalidParam("game")
    if not valid_ident(name): raise InvalidParam("name")
    if action in "leave restart rejoin".split():
      if action == "leave":
        update_game(game, leave_game(game, name))
      elif action == "restart":
        restart_game(game)
      return redirect(url_for(
        "r_index", join = "yes" if action != "restart" else None,
        game = game, name = name
      ))
    try:
      new = init_game(game, name, side, lang)
    except ValueError as e:
      raise InvalidParam(e.args[0])
    if new: update_game(game, new)
    cur, new = current_game(game), None
    if not cur["game_over"]:
      if action == "start":
        new = start_game(cur, name)
      elif action == "hint":
        new = give_hint(cur, name, hint)
      elif action == "guess":
        new = make_guess(cur, name, word)
      elif action == "give up":
        new = give_up(cur, name)
      if new: update_game(game, new)
    return render_template("play.html", **data(cur, game, name))
  except InProgress:
    return render_template("late.html", game = game)
  except Oops as e:
    return render_template("error.html", error = e.msg()), 400

# vim: set tw=70 sw=2 sts=2 et fdm=marker :
