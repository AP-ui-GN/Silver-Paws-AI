"""Regression tests for validation setup failures."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from scripts import validate_gait


class ValidateGaitSetupTests(unittest.TestCase):
    def test_empty_clip_directory_is_not_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = io.StringIO()
            args = Namespace(
                clips_dir=root / "clips",
                labels=root / "labels.csv",
                out=root / "out.csv",
            )
            args.clips_dir.mkdir()
            with patch.object(validate_gait, "parse_args", return_value=args):
                with contextlib.redirect_stdout(output):
                    code = validate_gait.main()
            self.assertEqual(code, 2)
            self.assertIn("no video clips were found", output.getvalue())

    def test_missing_label_file_is_not_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            clips = root / "clips"
            clips.mkdir()
            (clips / "example.mp4").write_bytes(b"not analyzed in this setup test")
            output = io.StringIO()
            args = Namespace(
                clips_dir=clips,
                labels=root / "missing-labels.csv",
                out=root / "out.csv",
            )
            with patch.object(validate_gait, "parse_args", return_value=args):
                with contextlib.redirect_stdout(output):
                    code = validate_gait.main()
            self.assertEqual(code, 2)
            self.assertIn("label file not found", output.getvalue())


if __name__ == "__main__":
    unittest.main()
