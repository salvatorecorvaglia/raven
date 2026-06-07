from raven.export.csv_export import CsvExporter
from raven.export.json_export import JsonExporter
from raven.export.text_export import TextExporter


def test_json_exporter(dummy_snapshot):
    exporter = JsonExporter()
    output = exporter.format(dummy_snapshot)
    assert '"timestamp"' in output
    assert '"system_info"' in output

def test_csv_exporter(dummy_snapshot):
    exporter = CsvExporter()
    output = exporter.format(dummy_snapshot, modules=["cpu"])
    assert "cpu.percent_overall" in output
    assert "10.0" in output

def test_text_exporter(dummy_snapshot):
    exporter = TextExporter()
    output = exporter.format(dummy_snapshot)
    assert "test-host" in output
    assert "RAM" in output
