# OVERLORD licensing decision

**Decision: Apache License 2.0** (SPDX identifier: `Apache-2.0`), selected 2026-11-07. See the repository [LICENSE](../LICENSE).

## Intent

OVERLORD is permissively open source. We want users and contributors to be free to use, study, modify, redistribute, fork and commercially deploy our original code, including outside Arma 3. Recipients must preserve required notices and state relevant modifications. The Apache licence contains an express patent grant. It does not grant trademark rights.

## Scope

- Original OVERLORD code in the Python director, SQF scripts, native bridge, configuration, test code and project documentation is Apache-2.0 unless a file explicitly says otherwise.
- Third-party libraries, assets, code snippets, sound, artwork, mission content and trademarks keep their own rights and terms. Do not copy or include them without provenance and permission.
- The licence does **not** relicense Arma 3, Bohemia content or other mods. Bohemia APL/APL-SA content can have noncommercial and Arma-only restrictions and must be kept out of any purported Apache-only distribution unless its own terms are complied with.
- Integration through public game/mod APIs does not imply ownership of their implementation or grant broader redistribution rights.
- A server operator's permission to commercialise original OVERLORD code does not override separately applicable Arma, server monetisation, mod or platform terms.

## Contribution rules

- Contributions intended for inclusion should be original or otherwise legally compatible with Apache-2.0 and any existing required terms.
- Contributors should clearly identify copied/adapted third-party content and licence provenance in the pull request; no unreviewed imported code or copyrighted game assets.
- No contributor licence agreement or copyright assignment is planned at this stage. We can consider DCO sign-offs in contributor guidance; this is not yet a requirement.
- Use `SPDX-License-Identifier: Apache-2.0` on new source files where sensible.
- Retain copyright notices, LICENSE and any required NOTICE records in redistributions; record changed files where required.

## Open operational checks

These do not prevent licensing our wholly original code now, but **must** be reviewed before bundling and releasing an Arma addon or Workshop package:

1. Arma Tools, game content, Steam Workshop and server monetisation terms.
2. Actual code/assets from CBA, ACE, Antistasi or any other mod, if included or redistributed.
3. Attribution and third-party notices for each imported dependency and asset.
4. Distribution packaging, embedded binaries, keys and logos.

## References

- [Apache-2.0 official text](https://www.apache.org/licenses/LICENSE-2.0)
- [Applying Apache-2.0](https://www.apache.org/legal/apply-license.html)
- [Bohemia licences](https://www.bohemia.net/en/licenses)
- [ACE3](https://github.com/acemod/ACE3) and [CBA A3](https://github.com/CBATeam/CBA_A3)
- [Antistasi Ultimate](https://github.com/Antistasi-Ultimate-Community/A3-Antistasi-Ultimate)

This is project-level guidance, not legal advice.
