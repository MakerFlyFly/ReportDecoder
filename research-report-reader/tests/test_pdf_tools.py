import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SPEC = importlib.util.spec_from_file_location("pdf_tools", ROOT / "scripts" / "pdf_tools.py")
pdf_tools = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pdf_tools)


def poppler_available():
    try:
        return all(pdf_tools.tool_path(name) for name in ("pdfinfo", "pdftotext", "pdftoppm"))
    except pdf_tools.PdfToolError:
        return False


class FileAndFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rrr-tests-")
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def test_note_paths_are_unique_and_do_not_overwrite(self):
        one, _ = pdf_tools.new_note(self.root)
        Path(one["note"]).write_text("existing user work", encoding="utf-8")
        two, _ = pdf_tools.new_note(self.root)
        self.assertNotEqual(one["note"], two["note"])
        self.assertEqual(Path(one["note"]).read_text(encoding="utf-8"), "existing user work")
        self.assertIn("整理中", Path(two["note"]).read_text(encoding="utf-8"))

    def test_collision_retry_preserves_existing_content(self):
        fixed = mock.Mock(hex="f" * 32)
        moment = mock.Mock()
        moment.now.return_value.strftime.return_value = "20250101-120000"
        old = self.root / "研报解读-20250101-120000-ffffffff.md"
        old.write_text("keep", encoding="utf-8")
        with mock.patch.object(pdf_tools, "datetime", moment), mock.patch.object(pdf_tools.uuid, "uuid4", return_value=fixed):
            with self.assertRaises(pdf_tools.PdfToolError) as caught:
                pdf_tools.new_note(self.root)
        self.assertEqual(caught.exception.code, "output_collision")
        self.assertEqual(old.read_text(encoding="utf-8"), "keep")

    def test_missing_dependency_reports_all_tools(self):
        result, code = pdf_tools.doctor(str(self.root))
        self.assertEqual(code, 2)
        self.assertEqual(len(result["tools"]), 3)
        self.assertFalse(any(row["available"] for row in result["tools"]))

    def test_error_summary_does_not_echo_identity(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = pdf_tools.main(["extract", str(self.root / "SecretCompany-Research.pdf")])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["error_code"], "invalid_input")
        self.assertNotIn("SecretCompany", output.getvalue())

    def test_timeout_is_reported_and_process_is_reaped(self):
        with self.assertRaises(pdf_tools.PdfToolError) as caught:
            pdf_tools.run_tool([sys.executable, "-c", "import time; time.sleep(5)"], 0.05)
        self.assertEqual(caught.exception.code, "tool_timeout")

    def test_invalid_manifest_is_controlled(self):
        path = self.root / "manifest.json"
        for content in ["not json", "[]", '{"schema_version":1,"page_count":false}', '{"schema_version":2}']:
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(pdf_tools.PdfToolError) as caught:
                pdf_tools.load_manifest(path)
            self.assertEqual(caught.exception.code, "invalid_manifest")

    def test_pages_are_bounded_sorted_and_deduplicated(self):
        self.assertEqual(pdf_tools.parse_pages("3, 1-3,5", 5), [1, 2, 3, 5])
        self.assertEqual(pdf_tools.parse_pages("all", 2), [1, 2])
        for value in ["0", "-1", "4-2", "1,", "6", "1-999999999", "1;anything"]:
            with self.subTest(value=value), self.assertRaises(pdf_tools.PdfToolError):
                pdf_tools.parse_pages(value, 5)


@unittest.skipUnless(poppler_available(), "Native Poppler is required for integration tests")
class PopplerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rrr-integration-")
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def extract(self, name="synthetic-report.pdf"):
        result, code = pdf_tools.extract_pdf(FIXTURES / name, self.root)
        path = Path(result["manifest"])
        return result, code, path, json.loads(path.read_text(encoding="utf-8"))

    def test_cjk_text_and_exact_numbers_survive_real_extraction(self):
        result, code, path, manifest = self.extract()
        self.assertIn(code, (0, 3))
        self.assertEqual(result["page_count"], 4)
        self.assertFalse(result["failed_pages"])
        texts = [(path.parent / row["text_file"]).read_text(encoding="utf-8") for row in manifest["pages"]]
        self.assertIn("澄海设备", texts[0])
        self.assertIn("22.4%", texts[0])
        self.assertIn("20.96%", texts[2])
        self.assertIn("22.0%", texts[3])
        self.assertIn("Jichuan", texts[3])

    def test_blank_middle_and_short_last_page_keep_their_positions(self):
        result, code, path, manifest = self.extract("blank-middle.pdf")
        self.assertEqual(code, 3)
        self.assertEqual([row["page"] for row in manifest["pages"]], [1, 2, 3])
        self.assertEqual(manifest["pages"][1]["nonspace_chars"], 0)
        self.assertIn("no_text", manifest["pages"][1]["flags"])
        self.assertIn("sparse_text", manifest["pages"][2]["flags"])
        self.assertEqual((path.parent / manifest["pages"][2]["text_file"]).read_text().strip(), "End.")

    def test_bitmap_only_is_not_reported_as_successful_text_reading(self):
        result, code, path, _ = self.extract("image-only.pdf")
        self.assertEqual(code, 4)
        self.assertEqual(result["status"], "no_extractable_text")
        rendered, render_code = pdf_tools.render_pdf(path, "1", dpi=72)
        self.assertEqual(render_code, 0)
        self.assertTrue(Path(rendered["images"][0]["image"]).read_bytes().startswith(b"\x89PNG"))

    def test_password_protected_and_corrupted_inputs_fail_cleanly(self):
        for name in ["password-protected.pdf", "broken.pdf"]:
            with self.subTest(name=name), self.assertRaises(pdf_tools.PdfToolError) as caught:
                self.extract(name)
            self.assertEqual(caught.exception.code, "pdf_read_failed")

    def test_paths_with_spaces_unicode_and_shell_metacharacters(self):
        source = self.root / "中文 & $(echo BAD) `名称.pdf"
        shutil.copyfile(FIXTURES / "synthetic-report.pdf", source)
        result, code = pdf_tools.extract_pdf(source, self.root / "缓存 & 中文")
        self.assertIn(code, (0, 3))
        self.assertEqual(result["page_count"], 4)
        rendered, code = pdf_tools.render_pdf(result["manifest"], "2", dpi=72)
        self.assertEqual(code, 0)
        self.assertTrue(Path(rendered["images"][0]["image"]).is_file())

    def test_new_extraction_does_not_overwrite_old_work(self):
        first, _, path, _ = self.extract()
        marker = path.parent / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        second, _, _, _ = self.extract()
        self.assertNotEqual(first["manifest"], second["manifest"])
        self.assertEqual(marker.read_text(), "keep")

    def test_source_fingerprint_prevents_rendering_a_different_revision(self):
        source = self.root / "input.pdf"
        shutil.copyfile(FIXTURES / "synthetic-report.pdf", source)
        result, _ = pdf_tools.extract_pdf(source, self.root)
        with source.open("ab") as stream:
            stream.write(b"\n% changed\n")
        with self.assertRaises(pdf_tools.PdfToolError) as caught:
            pdf_tools.render_pdf(result["manifest"], "1")
        self.assertEqual(caught.exception.code, "source_changed")

    def test_failed_page_does_not_discard_later_pages(self):
        actual = pdf_tools.run_tool

        def fail_second(command, timeout):
            if "-layout" in command and command[command.index("-f") + 1] == 2:
                raise pdf_tools.PdfToolError("tool_timeout", "simulated timeout")
            return actual(command, timeout)

        with mock.patch.object(pdf_tools, "run_tool", side_effect=fail_second):
            result, code, path, manifest = self.extract()
        self.assertEqual(code, 3)
        self.assertEqual(result["failed_pages"], [2])
        self.assertEqual(manifest["pages"][1]["text_file"], None)
        self.assertEqual(manifest["pages"][3]["status"], "extracted")
        self.assertIn("22.0%", (path.parent / manifest["pages"][3]["text_file"]).read_text(encoding="utf-8"))

    def test_partial_render_keeps_successes_and_records_failures(self):
        _, _, path, _ = self.extract()
        actual = pdf_tools.run_tool

        def fail_second(command, timeout):
            if "-singlefile" in command and command[command.index("-f") + 1] == 2:
                raise pdf_tools.PdfToolError("tool_timeout", "simulated timeout")
            return actual(command, timeout)

        with mock.patch.object(pdf_tools, "run_tool", side_effect=fail_second):
            rendered, code = pdf_tools.render_pdf(path, "1-2", dpi=72)
        self.assertEqual(code, 3)
        self.assertEqual([row["page"] for row in rendered["images"]], [1])
        self.assertEqual(rendered["failed_pages"][0]["page"], 2)

    def test_cli_returns_machine_readable_manifest(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "pdf_tools.py"), "extract", str(FIXTURES / "synthetic-report.pdf"), "--work-dir", str(self.root)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertIn(result.returncode, (0, 3))
        parsed = json.loads(result.stdout.decode("utf-8"))
        self.assertTrue(Path(parsed["manifest"]).is_file())
        self.assertNotIn("澄海", result.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
