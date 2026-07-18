# coding=utf-8

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_SCRIPT = REPOSITORY_ROOT / "scripts" / "upload_incremental_sftp.sh"


class SFTPUploadScriptTests(unittest.TestCase):
    def test_upload_uses_part_files_and_publishes_checksum_last(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            package_path = temp_dir / "incremental.json.gz"
            package_path.write_bytes(b"package")
            capture_path = temp_dir / "batch.txt"
            fake_sftp = temp_dir / "sftp"
            fake_sftp.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
batch=""
while (($#)); do
  if [[ "$1" == "-b" ]]; then
    batch="$2"
    shift 2
  else
    shift
  fi
done
cp "$batch" "$SFTP_CAPTURE"
""",
                encoding="utf-8",
            )
            fake_sftp.chmod(fake_sftp.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{temp_dir}:{env['PATH']}",
                    "SFTP_CAPTURE": str(capture_path),
                    "NEWS_SFTP_HOST": "news.example.com",
                    "NEWS_SFTP_PORT": "22",
                    "NEWS_SFTP_USER": "news-upload",
                    "NEWS_SFTP_PRIVATE_KEY": "dummy-private-key",
                    "NEWS_SFTP_KNOWN_HOSTS": "news.example.com ssh-ed25519 AAAA",
                    "NEWS_SFTP_REMOTE_DIR": "incoming/news",
                    "GITHUB_RUN_ID": "123",
                    "GITHUB_RUN_ATTEMPT": "2",
                }
            )

            result = subprocess.run(
                ["bash", str(UPLOAD_SCRIPT), str(package_path)],
                cwd=REPOSITORY_ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            commands = capture_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(commands), 4)
            self.assertIn("run123-attempt2.json.gz.part", commands[0])
            self.assertIn("run123-attempt2.json.gz.sha256.part", commands[1])
            self.assertIn("run123-attempt2.json.gz\"", commands[2])
            self.assertIn("run123-attempt2.json.gz.sha256\"", commands[3])

    def test_partial_configuration_fails_instead_of_silently_skipping(self):
        env = os.environ.copy()
        for name in (
            "NEWS_SFTP_HOST",
            "NEWS_SFTP_USER",
            "NEWS_SFTP_PRIVATE_KEY",
            "NEWS_SFTP_KNOWN_HOSTS",
        ):
            env.pop(name, None)
        env["NEWS_SFTP_HOST"] = "news.example.com"

        result = subprocess.run(
            ["bash", str(UPLOAD_SCRIPT), "/tmp/missing-package"],
            cwd=REPOSITORY_ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing required secret", result.stderr)


if __name__ == "__main__":
    unittest.main()
