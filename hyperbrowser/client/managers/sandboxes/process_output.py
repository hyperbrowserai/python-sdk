"""Collection and validation of the receiver's command event stream."""

import base64
import codecs
from typing import Dict, List, Optional

from ....exceptions import HyperbrowserError
from ....models.sandbox import SandboxProcessOutputEvent, SandboxProcessResult

DEFAULT_MAX_PROCESS_OUTPUT_BYTES = 64 * 1024 * 1024


class ProcessOutput:
    def __init__(self, process_id: str, max_bytes: int):
        self.process_id = process_id
        self.max_bytes = max_bytes
        self.size = 0
        self.seq = 0
        self.events: List[SandboxProcessOutputEvent] = []
        self.result: Optional[SandboxProcessResult] = None
        self.error: Optional[BaseException] = None
        self._chunks: Dict[str, List[str]] = {"stdout": [], "stderr": []}
        self._decoders = {
            stream: codecs.getincrementaldecoder("utf-8")(errors="replace")
            for stream in ("stdout", "stderr", "system")
        }

    def failure(
        self, message: str, code: str = "incomplete_output"
    ) -> HyperbrowserError:
        return HyperbrowserError(
            message,
            code=code,
            service="runtime",
            details={"process_id": self.process_id, "last_seq": self.seq},
        )

    def consume(self, event) -> None:
        kind, data = event["event"], event["data"]
        if kind == "output":
            if data["seq"] != self.seq + 1:
                raise self.failure("Command output contains a sequence gap")
            stream = data["stream"]
            if stream not in self._decoders:
                raise self.failure("Unknown command output stream")
            raw = (
                base64.b64decode(data["data"], validate=True)
                if data.get("encoding") == "base64"
                else data["data"].encode("utf-8")
            )
            self.size += len(raw)
            if self.size > self.max_bytes:
                raise self.failure(
                    "Command output exceeds max_output_bytes; increase the collection limit or disconnect a detached process",
                    "output_limit_exceeded",
                )
            self.seq = data["seq"]
            text = self._decoders[stream].decode(raw)
            self._chunks["stdout" if stream == "stdout" else "stderr"].append(text)
            self.events.append(
                SandboxProcessOutputEvent(
                    type=stream,
                    seq=self.seq,
                    data=text,
                    timestamp=data["timestamp"],
                )
            )
        elif kind == "done":
            if data.get("last_seq") != self.seq or data.get("output_truncated", False):
                raise self.failure("Receiver reported incomplete command output")
            for stream, decoder in self._decoders.items():
                self._chunks["stdout" if stream == "stdout" else "stderr"].append(
                    decoder.decode(b"", final=True)
                )
            result = dict(data)
            result["stdout"] = "".join(self._chunks["stdout"])
            result["stderr"] = "".join(self._chunks["stderr"])
            self.result = SandboxProcessResult(**result)
        elif kind == "error":
            raise self.failure(
                str(data.get("error", "Command stream failed")),
                data.get("code", "incomplete_output"),
            )


def validate_output_limit(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("max_output_bytes must be a positive integer")
