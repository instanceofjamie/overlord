# Licensing decision record (open)

Tracked in issue #20. This is an options document, not a licence grant. No licence has yet been selected.

## Leading option
**Apache-2.0 for wholly original OVERLORD source code** (Python director, native bridge and original SQF), subject to review of dependency licences and Bohemia tools/game content terms. This is a permissive licence with an explicit patent grant and permits reuse of the director outside Arma.

Other options:
- MIT: simple and permissive; no explicit patent grant.
- GPL-family: reciprocity for covered derivatives, but stronger compatibility and integration implications.
- APL/APL-SA: specific Bohemia/community Arma content licensing; includes noncommercial and Arma-only restrictions, with share-alike for APL-SA. Not a substitute for a general-purpose software licence for reusable components.

## Community precedents
- ACE3 GPLv2: https://github.com/acemod/ACE3
- CBA A3 GPLv2: https://github.com/CBATeam/CBA_A3 ; CBA clarifies that calling public functions does not alone impose GPL on independent addons.
- Antistasi Ultimate MIT with component exceptions: https://github.com/Antistasi-Ultimate-Community/A3-Antistasi-Ultimate/blob/unstable/LICENSE
- Bohemia licence overview: https://www.bohemia.net/en/licenses

## Before committing
- Confirm objectives for community forks, commercial server hosting and non-Arma reuse.
- Audit all imported source, game assets, sounds, logos, missions and tools; record provenance, attribution and licence.
- Check Arma Tools and Steam Workshop distribution rules for packaged content.
- Decide per-component notices, LICENSE, SPDX headers, THIRD_PARTY_NOTICES and contribution policy.
- Do not claim all components share a licence if they do not.

This is general guidance rather than legal advice.
