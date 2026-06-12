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


def test_exporter_filtering(dummy_snapshot):
    # JsonExporter filtering
    json_exp = JsonExporter()
    json_out = json_exp.format(dummy_snapshot, modules=["cpu"])
    assert "cpu" in json_out
    assert "memory" not in json_out

    # CsvExporter filtering
    csv_exp = CsvExporter()
    csv_out = csv_exp.format(dummy_snapshot, modules=["cpu"])
    assert "cpu.percent_overall" in csv_out
    assert "memory.percent" not in csv_out

    # TextExporter filtering
    text_exp = TextExporter()
    text_out = text_exp.format(dummy_snapshot, modules=["cpu"])
    assert "CPU" in text_out
    assert "RAM" not in text_out
