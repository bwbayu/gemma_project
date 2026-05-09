from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_credentials_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return Path.cwd() / path


def _record(results: list[CheckResult], name: str, ok: bool, detail: str) -> None:
    results.append(CheckResult(name=name, ok=ok, detail=detail))


def _print_summary(results: list[CheckResult]) -> int:
    print("\n=== Infra Test Summary ===")
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")

    failed = [r for r in results if not r.ok]
    print(f"\nTotal checks: {len(results)} | Passed: {len(results) - len(failed)} | Failed: {len(failed)}")
    return 1 if failed else 0


def main() -> int:
    load_dotenv()
    results: list[CheckResult] = []

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    creds_path_raw = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    gcs_bucket_name = os.getenv("GCS_BUCKET_NAME", "").strip()
    firebase_bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()

    required = {
        "GOOGLE_CLOUD_PROJECT": project_id,
        "GOOGLE_APPLICATION_CREDENTIALS": creds_path_raw,
        "GCS_BUCKET_NAME": gcs_bucket_name,
        "FIREBASE_STORAGE_BUCKET": firebase_bucket_name,
    }

    for key, value in required.items():
        _record(
            results,
            f"env:{key}",
            bool(value),
            "set" if value else "missing",
        )

    if not creds_path_raw:
        return _print_summary(results)

    creds_path = _resolve_credentials_path(creds_path_raw)
    _record(
        results,
        "credentials:file_exists",
        creds_path.exists(),
        str(creds_path),
    )

    if not creds_path.exists():
        return _print_summary(results)

    # Make the resolved absolute path available to Google SDKs.
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, storage
        from google.cloud import storage as gcs_storage
    except Exception as exc:
        _record(results, "python:google_sdk_imports", False, f"import error: {exc}")
        return _print_summary(results)

    try:
        app_name = "infra-test-app"
        try:
            app = firebase_admin.get_app(app_name)
        except ValueError:
            cred = credentials.Certificate(str(creds_path))
            app = firebase_admin.initialize_app(
                cred,
                {
                    "projectId": project_id,
                    "storageBucket": firebase_bucket_name or None,
                },
                name=app_name,
            )
        _record(results, "firebase_admin:init", True, f"app={app.name}")
    except Exception as exc:
        _record(results, "firebase_admin:init", False, str(exc))
        return _print_summary(results)

    # Firestore write/read/delete smoke test
    run_id = f"infra_{uuid.uuid4().hex[:8]}"
    doc_path = f"_infra_smoke_tests/{run_id}"
    try:
        db = firestore.client(app=app)
        ref = db.document(doc_path)
        payload = {"ping": "ok", "created_at": _now_iso()}
        ref.set(payload)
        snap = ref.get()
        ok = snap.exists and snap.to_dict().get("ping") == "ok"
        _record(results, "firestore:write_read", ok, doc_path)
        ref.delete()
        _record(results, "firestore:delete", True, doc_path)
    except Exception as exc:
        _record(results, "firestore:write_read_delete", False, str(exc))

    # GCS smoke test helper
    def test_bucket(bucket_name: str, label: str) -> None:
        if not bucket_name:
            _record(results, f"{label}:bucket_name", False, "missing")
            return

        object_path = f"_infra_smoke_tests/{run_id}/ping.txt"
        try:
            gcs_client = gcs_storage.Client(project=project_id)
            bucket = gcs_client.bucket(bucket_name)
            exists = bucket.exists()
            _record(results, f"{label}:bucket_exists", bool(exists), bucket_name)
            if not exists:
                return

            blob = bucket.blob(object_path)
            content = f"infra test @ {_now_iso()}"
            blob.upload_from_string(content, content_type="text/plain")
            read_back = blob.download_as_text()
            _record(results, f"{label}:upload_download", read_back == content, object_path)
            blob.delete()
            _record(results, f"{label}:delete", True, object_path)
        except Exception as exc:
            _record(results, f"{label}:upload_download_delete", False, str(exc))

    test_bucket(gcs_bucket_name, "gcs_bucket_name")
    # Avoid running duplicate checks if both env vars point to same bucket.
    if firebase_bucket_name and firebase_bucket_name != gcs_bucket_name:
        test_bucket(firebase_bucket_name, "firebase_storage_bucket")
    else:
        _record(
            results,
            "firebase_storage_bucket:deduplicated",
            True,
            "same as GCS_BUCKET_NAME or empty",
        )

    # Validate firebase storage adapter can resolve the configured bucket.
    if firebase_bucket_name:
        try:
            fb_bucket = storage.bucket(firebase_bucket_name, app=app)
            _record(results, "firebase_admin:storage_bucket_resolve", True, fb_bucket.name)
        except Exception as exc:
            _record(results, "firebase_admin:storage_bucket_resolve", False, str(exc))

    return _print_summary(results)


if __name__ == "__main__":
    sys.exit(main())
