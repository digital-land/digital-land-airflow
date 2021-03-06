from csv import DictReader
from datetime import date
from difflib import diff_bytes, context_diff
from json import load
from subprocess import run, CalledProcessError

from deep_dircmp import DeepDirCmp

from digital_land_airflow.tasks.collector import (
    callable_collect_task,
    callable_collection_task,
)
from digital_land_airflow.tasks.pipeline import (
    callable_build_dataset_task,
    callable_dataset_task,
)

TODAY = date.today()


def _split_string_on_unknown_line_ending(string):
    if "\r\n" in string:
        return string.split("\r\n")
    else:
        return string.split("\n")


def _is_text_file_output(content):
    try:
        content.decode("utf-8")
    except Exception:
        return False
    else:
        return True


def _diff_sql_files(dir1_files, dir2_files):
    diffs = []
    assert [sqlite_file.name for sqlite_file in dir1_files] == [
        sqlite_file.name for sqlite_file in dir2_files
    ]
    for dir1_file, dir2_file in zip(dir1_files, dir2_files):
        run(
            ["command", "-v", "sqldiff"],
            check=True,
            shell=True,
        )
        completed_process = run(
            f"sqldiff {dir1_file} {dir2_file}",
            capture_output=True,
            shell=True,
        )
        if completed_process.stdout:
            diffs.extend(completed_process.stdout.split(b"\n"))
        if completed_process.stderr:
            diffs.extend(completed_process.stderr.split(b"\n"))
        try:
            completed_process.check_returncode()
        except CalledProcessError as e:
            print(f"sqldiff stdout: {completed_process.stdout}")
            print(f"sqldiff stderr: {completed_process.stderr}")
            raise e

    assert not diffs


def _diff_files(dir1, dir2, filenames):
    diffs = []
    for filename in filenames:
        with dir1.joinpath(filename).open(mode="rb") as f1, dir2.joinpath(
            filename
        ).open(mode="rb") as f2:

            f1_content = f1.readline()
            f2_content = f2.readline()
        if _is_text_file_output(f1_content) and _is_text_file_output(f1_content):

            f1_content_list = _split_string_on_unknown_line_ending(
                f1_content.decode("utf-8")
            )
            f2_content_list = _split_string_on_unknown_line_ending(
                f2_content.decode("utf-8")
            )
            diffs.extend(
                context_diff(
                    f1_content_list,
                    f2_content_list,
                    fromfile=str(dir1.joinpath(filename)),
                    tofile=str(dir2.joinpath(filename)),
                )
            )
        else:
            diffs.extend(
                diff_bytes(
                    context_diff,
                    bytes(f1_content),
                    bytes(f2_content),
                    fromfile=str(dir1.joinpath(filename)),
                    tofile=str(dir2.joinpath(filename)),
                )
            )
    return diffs


def _assert_tree_identical(dir1, dir2, only=None):
    if only:
        ignore = [
            filepath.name for filepath in dir2.glob("**/*") if filepath.name not in only
        ]
    else:
        ignore = []

    # TODO the insertion order in digital-land-python is unstable, see if getting it reliable is practical
    dir1_sqlite = sorted(dir1.glob("**/*.sqlite*"))
    #  dir2_sqlite = sorted(dir2.glob("**/*.sqlite*"))
    #  _diff_sql_files(dir1_sqlite, dir2_sqlite)
    ignore.extend([sqlite_file.name for sqlite_file in dir1_sqlite])

    dircmp_instance = DeepDirCmp(dir1, dir2, ignore=ignore)
    assert not dircmp_instance.left_only
    assert not dircmp_instance.right_only
    assert not dircmp_instance.diff_files, _diff_files(
        dir1, dir2, dircmp_instance.diff_files
    )


def get_filename_without_suffix_from_path(path):
    return path.name[: -len("".join(path.suffixes))]


def test_collect(collection_metadata_dir, endpoint_requests_mock, kwargs, tmp_path):
    # Setup
    tmp_path.joinpath("pipeline").mkdir()

    # Call
    callable_collect_task(**kwargs)

    # Assert
    log_dir = collection_metadata_dir.joinpath("log").joinpath(TODAY.isoformat())
    all_urls = {endpoint._url for endpoint in endpoint_requests_mock}
    all_logs = [load(f.open()) for f in log_dir.iterdir()]
    assert {log["endpoint-url"] for log in all_logs} == all_urls
    for mock in endpoint_requests_mock:
        assert mock.called_once
        assert mock._url in [log["endpoint-url"] for log in all_logs]


def test_collection(
    collection_resources_dir,
    collection_metadata_dir,
    collection_payload_dir,
    kwargs,
    tmp_path,
):
    # Setup
    tmp_path.joinpath("pipeline").mkdir()

    # Call
    callable_collection_task(**kwargs)

    # Assert
    with open(collection_payload_dir.parent.parent.joinpath("log.csv")) as log_file:
        log_csv = DictReader(log_file)
        logs = list(log_csv)
        assert {log["endpoint"] for log in logs} == set(
            get_filename_without_suffix_from_path(path)
            for path in collection_payload_dir.iterdir()
        )

        with open(
            collection_payload_dir.parent.parent.joinpath("resource.csv")
        ) as resource_file:
            resource_csv = DictReader(resource_file)
            assert {log["resource"] for log in logs} == {
                resource["resource"] for resource in resource_csv
            }


def test_dataset(
    # Static runtime filesystem dependencies
    pipeline_dir,
    # Runtime filesystem dependencies
    collection_payload_dir,  # This is now a dependency of api.pipeline_resource_mapping_for_collection_
    collection_metadata_dir,
    collection_resources_dir,
    collection_resources_file,
    # Test assertion directories
    data_dir,
    # Function argument fixtures
    kwargs,
    # Pytest fixtures
    mocker,
    requests_mock,
    tmp_path,
):
    # Setup
    transformed_dir = tmp_path.joinpath("transformed")
    issue_dir = tmp_path.joinpath("issue")

    # Call
    with mocker.patch(
        "digital_land_airflow.tasks.pipeline.get_organisation_csv",
        return_value=data_dir.joinpath("organisation.csv"),
    ):
        callable_dataset_task(**kwargs)

    # Assert
    _assert_tree_identical(transformed_dir, data_dir.joinpath("transformed"))

    _assert_tree_identical(issue_dir, data_dir.joinpath("issue"))


def test_dataset_specified_resources(
    # Static runtime filesystem dependencies
    pipeline_dir,
    # Runtime filesystem dependencies
    collection_metadata_dir,
    collection_payload_dir,  # This is now a dependency of api.pipeline_resource_mapping_for_collection_
    collection_resources_dir,
    collection_resources_file,
    # Test assertion directories
    data_dir,
    # Function argument fixtures
    kwargs_specified_resources,
    # Pytest fixtures
    mocker,
    requests_mock,
    tmp_path,
):
    # Setup
    transformed_dir = tmp_path.joinpath("transformed")
    issue_dir = tmp_path.joinpath("issue")

    # Call
    with mocker.patch(
        "digital_land_airflow.tasks.pipeline.get_organisation_csv",
        return_value=data_dir.joinpath("organisation.csv"),
    ):
        callable_dataset_task(**kwargs_specified_resources)

    # Assert
    _assert_tree_identical(
        transformed_dir,
        data_dir.joinpath("transformed"),
        only=kwargs_specified_resources["params"]["resource_hashes"],
    )

    _assert_tree_identical(
        issue_dir,
        data_dir.joinpath("issue"),
        kwargs_specified_resources["params"]["resource_hashes"],
    )


def test_build_dataset(
    # Static runtime filesystem dependencies
    column_field_dir,
    dataset_resource_dir,
    pipeline_dir,
    # Runtime filesystem dependencies generated by previous steps
    collection_metadata_dir,
    collection_payload_dir,  # This is now a dependency of api.pipeline_resource_mapping_for_collection_
    collection_resources_dir,
    collection_resources_file,
    issue_dir,
    transformed_dir,
    # Test assertion directories
    data_dir,
    # Function argument fixtures
    kwargs,
    # Pytest fixtures
    mocker,
    requests_mock,
    tmp_path,
):
    # Setup

    # Call
    callable_build_dataset_task(**kwargs)

    # Assert
    _assert_tree_identical(
        tmp_path.joinpath("dataset"),
        data_dir.joinpath("dataset"),
    )


def test_build_dataset_specified_resources(
    # Static runtime filesystem dependencies
    column_field_dir,
    dataset_resource_dir,
    pipeline_dir,
    # Runtime filesystem dependencies generated by previous steps
    collection_metadata_dir,
    collection_payload_dir,  # This is now a dependency of api.pipeline_resource_mapping_for_collection_
    collection_resources_dir,
    collection_resources_file,
    issue_dir,
    transformed_dir,
    # Test assertion directories
    data_dir,
    # Function argument fixtures
    kwargs_specified_resources,
    # Pytest fixtures
    mocker,
    requests_mock,
    tmp_path,
):
    # Setup

    # Call
    callable_build_dataset_task(**kwargs_specified_resources)

    # Assert
    _assert_tree_identical(
        tmp_path.joinpath("dataset"),
        data_dir.joinpath("dataset"),
        only=kwargs_specified_resources["params"]["resource_hashes"],
    )
