"""Example setup script for the AppVeyor upload blueprint."""

import os


def main() -> None:
    """Create sample JUnit and xUnit results used by the upload stage."""
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.mkdir(results_dir)

    files = {
        os.path.join(results_dir, "xunit.xml"): (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<assemblies>\n"
            '  <assembly name="Builddrone.Appveyor.Example">\n'
            '    <collection name="ExampleTests">\n'
            '      <test name="ExampleTest.Passes" type="ExampleTest" '
            'method="Passes" result="Pass" time="0.001"/>\n'
            "    </collection>\n"
            "  </assembly>\n"
            "</assemblies>\n"
        ),
        os.path.join(results_dir, "junit.xml"): (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<testsuite name="Builddrone AppVeyor Example" tests="1" '
            'failures="0" errors="0" skipped="0" time="0.001">\n'
            '  <testcase classname="ExampleTest" name="test_passes" time="0.001"/>\n'
            "</testsuite>\n"
        ),
    }

    for file_path, content in files.items():
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)


if __name__ == "__main__":
    main()
