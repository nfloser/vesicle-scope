"""Loopback-only HTTP server for the local VesicleScope workspace."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit
import webbrowser

from vesiclescope.ui.app import WorkspaceApplication


_MAX_JSON_BODY = 2_100_000
_MAX_ARCHIVE_BODY = 64 * 1024 * 1024


def _index_bytes() -> bytes:
    resource = resources.files("vesiclescope.ui").joinpath("static/index.html")
    return resource.read_bytes()


def _handler_class(app: WorkspaceApplication, index: bytes):
    class Handler(BaseHTTPRequestHandler):
        server_version = "VesicleScopeLocalUI/0.1"

        def _security_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
            )

        def _send_json(self, status: int, payload: Any) -> None:
            data = json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            ).encode("utf-8")
            self.send_response(status)
            self._security_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_error_json(self, status: int, message: str) -> None:
            self._send_json(status, {"error": message})

        def _query_one(self, query: dict[str, list[str]], name: str) -> str:
            values = query.get(name)
            if values is None or len(values) != 1 or not values[0]:
                raise ValueError(f"missing query parameter: {name}")
            return values[0]

        def _validate_host(self) -> None:
            raw_host = self.headers.get("Host")
            if not raw_host:
                raise ValueError("request Host header is required")
            hostname = urlsplit(f"//{raw_host}").hostname
            if hostname not in {"127.0.0.1", "localhost"}:
                raise ValueError("request Host must resolve to the local VesicleScope UI")

        def _read_json(self) -> dict[str, Any]:
            if self.headers.get_content_type() != "application/json":
                raise ValueError("request Content-Type must be application/json")
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ValueError("request Content-Length is required")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValueError("invalid request Content-Length") from exc
            if length < 0 or length > _MAX_JSON_BODY:
                raise ValueError("request body exceeds 2.1 MB limit")
            body = self.rfile.read(length)
            try:
                value = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("request body is not valid UTF-8 JSON") from exc
            if not isinstance(value, dict):
                raise ValueError("request JSON must be an object")
            return value


        def _read_archive_body(self) -> bytes:
            if self.headers.get_content_type() != "application/zip":
                raise ValueError("archive request Content-Type must be application/zip")
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ValueError("request Content-Length is required")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValueError("invalid request Content-Length") from exc
            if length < 0 or length > _MAX_ARCHIVE_BODY:
                raise ValueError("COMBINE archive request exceeds 64 MB limit")
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("COMBINE archive request body is incomplete")
            return body

        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query, keep_blank_values=True)
            try:
                self._validate_host()
                if parsed.path == "/":
                    self.send_response(HTTPStatus.OK)
                    self._security_headers()
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(index)))
                    self.end_headers()
                    self.wfile.write(index)
                    return
                if parsed.path == "/api/health":
                    self._send_json(HTTPStatus.OK, {"ok": True})
                    return
                if parsed.path == "/api/state":
                    self._send_json(HTTPStatus.OK, app.state())
                    return
                if parsed.path == "/api/experiment":
                    name = self._query_one(query, "name")
                    self._send_json(HTTPStatus.OK, app.experiment(name))
                    return
                if parsed.path == "/api/run":
                    name = self._query_one(query, "name")
                    self._send_json(HTTPStatus.OK, app.run(name, include_field=True))
                    return
                if parsed.path == "/api/compare":
                    left = self._query_one(query, "left")
                    right = self._query_one(query, "right")
                    self._send_json(HTTPStatus.OK, app.compare(left, right))
                    return
                if parsed.path == "/download/experiment":
                    self._send_artifact("experiment", self._query_one(query, "name"))
                    return
                if parsed.path == "/download/run":
                    self._send_artifact("run", self._query_one(query, "name"))
                    return
                if parsed.path == "/download/batch-archive":
                    self._send_archive_data(*app.export_batch_archive(query.get("run", [])))
                    return
                if parsed.path == "/download/archive":
                    self._send_archive(self._query_one(query, "experiment"))
                    return
                self._send_error_json(HTTPStatus.NOT_FOUND, "not found")
            except (OSError, RuntimeError, TypeError, ValueError) as exc:
                self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

        def _send_artifact(self, kind: str, name: str) -> None:
            path = app.artifact_path(kind, name)
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self._security_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header(
                "Content-Disposition",
                f"attachment; filename*=UTF-8''{quote(path.name)}",
            )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)


        def _send_archive(self, experiment_name: str) -> None:
            self._send_archive_data(*app.export_archive(experiment_name))

        def _send_archive_data(self, filename: str, data: bytes) -> None:
            self.send_response(HTTPStatus.OK)
            self._security_headers()
            self.send_header("Content-Type", "application/zip")
            self.send_header(
                "Content-Disposition",
                f"attachment; filename*=UTF-8''{quote(filename)}",
            )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self) -> None:
            parsed = urlsplit(self.path)
            try:
                self._validate_host()
                if parsed.path == "/api/batch-archive/import":
                    self._send_json(HTTPStatus.CREATED, app.import_batch_archive(self._read_archive_body()))
                    return
                if parsed.path == "/api/archive/import":
                    self._send_json(
                        HTTPStatus.CREATED,
                        app.import_archive(self._read_archive_body()),
                    )
                    return
                payload = self._read_json()
                if parsed.path == "/api/example":
                    name = payload.get("name", "diffusion-uptake-baseline.json")
                    self._send_json(HTTPStatus.CREATED, app.create_baseline(name))
                    return
                if parsed.path == "/api/import":
                    name = payload.get("name")
                    document = payload.get("document")
                    if not isinstance(name, str):
                        raise ValueError("import name must be a string")
                    self._send_json(
                        HTTPStatus.CREATED,
                        app.import_experiment(name, document),
                    )
                    return
                if parsed.path == "/api/derive":
                    source_name = payload.get("source")
                    output_name = payload.get("name")
                    experiment_id = payload.get("experiment_id")
                    if not isinstance(source_name, str):
                        raise ValueError("derive source must be a string")
                    if not isinstance(output_name, str):
                        raise ValueError("derive name must be a string")
                    if not isinstance(experiment_id, str):
                        raise ValueError("derive experiment_id must be a string")
                    self._send_json(
                        HTTPStatus.CREATED,
                        app.derive_synthetic_experiment(
                            source_name=source_name,
                            output_name=output_name,
                            experiment_id=experiment_id,
                            duration_min=payload.get("duration_min"),
                            sample_every_min=payload.get("sample_every_min"),
                            diffusion_value=payload.get("diffusion_value"),
                            decay_value=payload.get("decay_value"),
                            initial_concentration_value=payload.get(
                                "initial_concentration_value"
                            ),
                            release_rates=payload.get("release_rates"),
                            uptake_rates=payload.get("uptake_rates"),
                        ),
                    )
                    return
                if parsed.path == "/api/run":
                    experiment_name = payload.get("experiment")
                    run_name = payload.get("run_name")
                    if not isinstance(experiment_name, str):
                        raise ValueError("experiment must be a string")
                    if not isinstance(run_name, str):
                        raise ValueError("run_name must be a string")
                    self._send_json(
                        HTTPStatus.CREATED,
                        app.execute(
                            experiment_name=experiment_name,
                            run_name=run_name,
                            grid_spacing_micron=payload.get("grid_spacing_micron"),
                            time_step_min=payload.get("time_step_min"),
                        ),
                    )
                    return
                self._send_error_json(HTTPStatus.NOT_FOUND, "not found")
            except (OSError, RuntimeError, TypeError, ValueError) as exc:
                self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

        def log_message(self, format: str, *args: object) -> None:
            # Keep the local UI quiet unless the caller wraps/overrides the handler.
            return

    return Handler


def create_server(
    app: WorkspaceApplication,
    *,
    port: int = 0,
) -> ThreadingHTTPServer:
    if isinstance(port, bool) or not isinstance(port, int) or port < 0 or port > 65535:
        raise ValueError("port must be an integer between 0 and 65535")
    return ThreadingHTTPServer(
        ("127.0.0.1", port),
        _handler_class(app, _index_bytes()),
    )


def serve_ui(
    app: WorkspaceApplication,
    *,
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    server = create_server(app, port=port)
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/"
    print(f"VesicleScope UI: {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
