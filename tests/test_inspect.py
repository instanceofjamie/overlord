# SPDX-License-Identifier: Apache-2.0
import sys
from uuid import uuid4

import httpx
import pytest

from overlord.inspect import main


def test_inspect_reads_multiple_pages(monkeypatch, capsys):
    session = str(uuid4())
    calls = []

    def handle(request):
        calls.append(str(request.url))
        if request.url.path == "/v1/sessions":
            return httpx.Response(200, json=[{"session_id": session}])
        offset = request.url.params.get("offset")
        return httpx.Response(200, json=[{"event_id": "sample"}] * (100 if offset == "0" else 1))

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kw: real_client(**kw, transport=httpx.MockTransport(handle))
    )
    monkeypatch.setattr(sys, "argv", ["overlord-inspect", "--latest"])
    main()
    output = capsys.readouterr().out
    assert session in output
    assert "Recorded observations: 101" in output
    assert len(calls) == 3


def test_inspect_empty_sessions(monkeypatch, capsys):
    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: real_client(
            **kw, transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[]))
        ),
    )
    monkeypatch.setattr(sys, "argv", ["overlord-inspect", "--latest"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "No sessions" in capsys.readouterr().err
