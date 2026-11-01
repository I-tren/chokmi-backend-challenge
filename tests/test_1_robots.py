import pytest
from chokmi_challenge.robots import Robots

UA = "ChokmiBot/1.2 (+https://chokmi.com/bot)"


def R(body):
    return Robots.from_response(200, body)


def test_status_policies():
    assert Robots.from_response(404, None).is_allowed(UA, "/x")
    assert Robots.from_response(410, "").is_allowed(UA, "/x")
    assert not Robots.from_response(503, None).is_allowed(UA, "/x")
    assert not Robots.from_response(302, None).is_allowed(UA, "/x")
    assert R("").is_allowed(UA, "/anything")


def test_basic_and_prefix():
    r = R("User-agent: *\nDisallow: /private\n")
    assert not r.is_allowed(UA, "/private")
    assert not r.is_allowed(UA, "/private/deep?x=1")
    assert not r.is_allowed(UA, "/privateer")
    assert r.is_allowed(UA, "/Private")
    assert r.is_allowed(UA, "/public")
    assert r.is_allowed(UA, "no-leading-slash")


def test_longest_match_and_allow_wins_tie():
    r = R("User-agent: *\nDisallow: /a/\nAllow: /a/b\nDisallow: /a/b/c\n")
    assert not r.is_allowed(UA, "/a/x")
    assert r.is_allowed(UA, "/a/b")
    assert r.is_allowed(UA, "/a/bz")
    assert not r.is_allowed(UA, "/a/b/c/d")
    tie = R("User-agent: *\nDisallow: /t\nAllow: /t\n")
    assert tie.is_allowed(UA, "/t/1")
    tie2 = R("User-agent: *\nAllow: /t\nDisallow: /t\n")
    assert tie2.is_allowed(UA, "/t/1")


def test_wildcards_and_anchor():
    r = R("User-agent: *\nDisallow: /*.pdf$\nDisallow: /tmp*/cache\nAllow: /tmp-ok/cache\n")
    assert not r.is_allowed(UA, "/docs/a.pdf")
    assert r.is_allowed(UA, "/docs/a.pdf?download=1")
    assert r.is_allowed(UA, "/docs/a.pdfx")
    assert not r.is_allowed(UA, "/tmp123/cache/z")
    assert r.is_allowed(UA, "/tmp-ok/cache/z")  # longer allow beats disallow


def test_wildcard_length_counts_pattern_chars():
    # "/a*" (len 3) beats "/a" (len 2) -> disallow wins on /ab
    r = R("User-agent: *\nAllow: /a\nDisallow: /a*\n")
    assert not r.is_allowed(UA, "/ab")


def test_group_selection_specific_beats_star_and_merges():
    body = """
User-agent: *
Disallow: /

User-agent: chokmibot
Disallow: /secret

User-agent: otherbot
User-agent: CHOKMIBOT
Allow: /secret/open
"""
    r = R(body)
    assert r.is_allowed(UA, "/anything")           # '*' group NOT applied
    assert not r.is_allowed(UA, "/secret/x")
    assert r.is_allowed(UA, "/secret/open/1")      # merged groups
    assert not r.is_allowed("RandomBot/9", "/anything")
    assert r.is_allowed("ChokmiBotExtra/1", "/a") is False  # different token -> '*'


def test_stacked_agents_and_rule_boundary():
    body = "User-agent: a\nUser-agent: b\nDisallow: /x\nUser-agent: c\nDisallow: /y\n"
    r = R(body)
    assert not r.is_allowed("a", "/x") and not r.is_allowed("B", "/x")
    assert r.is_allowed("c", "/x") and not r.is_allowed("c", "/y")
    assert r.is_allowed("a", "/y")


def test_rules_before_agent_ignored_and_unknown_directives_do_not_break_groups():
    body = "Disallow: /orphan\nUser-agent: *\nSitemap: https://x/s.xml\nCrawl-delay: 5\nDisallow: /d\n"
    r = R(body)
    assert r.is_allowed(UA, "/orphan")
    assert not r.is_allowed(UA, "/d")


def test_syntax_noise():
    body = "﻿USER-AGENT :   *   # all\r\ndisallow:/Caps # c\r\n\r\n# only comment\r\nALLOW: /Caps/ok\r\n"
    r = R(body)
    assert not r.is_allowed(UA, "/Caps/zzz")
    assert r.is_allowed(UA, "/Caps/ok")
    assert r.is_allowed(UA, "/caps/zzz")


def test_empty_disallow_is_not_a_rule():
    r = R("User-agent: *\nDisallow:\nAllow:\n")
    assert r.is_allowed(UA, "/x")
    r2 = R("User-agent: *\nDisallow: /\nDisallow:\n")
    assert not r2.is_allowed(UA, "/x")


def test_percent_normalisation():
    r = R("User-agent: *\nDisallow: /a%62c\nDisallow: /café\nDisallow: /sp%2fl\n")
    assert not r.is_allowed(UA, "/abc")                 # %62 == 'b'
    assert not r.is_allowed(UA, "/caf%C3%A9/menu")
    assert not r.is_allowed(UA, "/caf%c3%a9")
    assert not r.is_allowed(UA, "/café")
    assert not r.is_allowed(UA, "/sp%2Fl")              # reserved stays encoded, hex uppercased
    assert r.is_allowed(UA, "/sp/l")                    # %2F is NOT '/'


def test_robots_txt_always_allowed_when_parsed():
    r = R("User-agent: *\nDisallow: /\n")
    assert r.is_allowed(UA, "/robots.txt")
    assert not r.is_allowed(UA, "/robots.txt.bak")


def test_ua_token_parsing():
    r = R("User-agent: chokmibot\nDisallow: /no\nUser-agent: *\nDisallow: /\n")
    assert not r.is_allowed("chokmibot", "/no")
    assert not r.is_allowed("ChokmiBot (compatible; x)", "/no")
    assert r.is_allowed("CHOKMIBOT/2.0", "/yes")
