from setuptools import find_namespace_packages, setup

from version import get_version


setup(
    name="digital-land-airflow",
    version=get_version(),
    long_description_content_type="text/markdown",
    author="MHCLG Digital Land Team",
    author_email="DigitalLand@communities.gov.uk",
    license="MIT",
    url="https://github.com/digital-land/digital-land-airflow",
    # TOOD move files into digital_land_airflow directory
    packages=find_namespace_packages(include=["digital_land_airflow*"]),
    include_package_data=True,
    install_requires=[
        # Data fetchers
        "GitPython~=3.1.0",
        "boto3~=1.20.0",
        "cloudpathlib",
        # Pipeline dependencies
        "pip",  # This is here to ensure we are using the latest version
        "csvkit",  # This is a pipeline dep
        # Utils
        "pendulum~=2.1.2",
        "pyhumps~=3.5.0",
    ],
    setup_requires=["pytest-runner"],
    extras_require={
        "digital_land": [
            "digital-land@git+https://github.com/digital-land/digital-land-python",
        ],
        "test": [
            "black",
            "coverage",
            "flake8",
            "pytest",
            "coveralls",
            "twine",
            "requests-mock",
            "pytest-mock",
            "pytest-dotenv",
            "apache-airflow~=2.2.0",
            "deep-dircmp",
        ],
        "dev": [
            "pytest-pudb",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
