"""Part 1 — robots.txt matcher (RFC 9309).

Chokmi's external-evidence crawler must honour robots.txt exactly. Implement
`Robots`:

    Robots.from_response(status: int, body: str | None) -> Robots
    Robots.is_allowed(user_agent: str, path: str) -> bool

Rules you are expected to know or look up:

* 2xx: parse `body`. 4xx: no robots file, everything allowed. 5xx (and anything
  else, including 3xx after redirects were exhausted): everything disallowed.
* A UTF-8 BOM, `#` comments, CRLF/LF, any-case directive names, and whitespace
  around `:` are all legal. Unknown directives (e.g. `Sitemap`, `Crawl-delay`)
  are ignored and do NOT end a group.
* Consecutive `User-agent` lines share one group. A rule line ends the
  "agent block"; the next `User-agent` starts a new group. Rules that appear
  before any `User-agent` are ignored.
* `user_agent` is a full UA string such as "ChokmiBot/1.2 (+https://...)". Its
  product token is the part before the first "/" or space, compared
  case-insensitively with the group's agent token. If any group names the
  token, ONLY those groups apply (all of them are merged); otherwise the `*`
  groups apply (merged); if neither exists everything is allowed.
* `path` is a path plus optional query, e.g. "/a/b?x=1". A path with no
  leading "/" is treated as having one.
* Matching is prefix-based on the percent-normalised path. `*` matches any run
  of characters and a trailing `$` anchors the end. Paths are case-sensitive.
  Normalise before comparing: decode %XX of unreserved characters
  (A-Z a-z 0-9 - . _ ~), uppercase the hex of the rest, and percent-encode
  non-ASCII characters as UTF-8. Apply the same normalisation to patterns.
* The most specific rule wins: the longest pattern (length of the normalised
  pattern string, wildcards included). On a tie, Allow beats Disallow.
  An empty `Disallow:` or `Allow:` value is not a rule.
* When a robots file was parsed (2xx), "/robots.txt" itself is always allowed.
"""


class Robots:
    @classmethod
    def from_response(cls, status, body):
        raise NotImplementedError

    def is_allowed(self, user_agent, path):
        raise NotImplementedError
