# Digital Land Airflow

<!-- vim-markdown-toc Marked -->

* [Overview](#overview)
* [Prerequisites](#prerequisites)
* [Setting Digital Land Airflow up locally](#setting-digital-land-airflow-up-locally)
* [Using this repository and AWS authentication matters](#using-this-repository-and-aws-authentication-matters)

<!-- vim-markdown-toc -->

## Overview

This repository contains the [Apache Airflow](https://airflow.apache.org/) [DAG](https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html)'s used in running the Digital Land pipeline (ETL) infrastructure.

## Prerequisites

* Docker
* Docker Compose

## Setting Digital Land Airflow up locally

* At the time of writing, it is necessary to be authenticated with the Digital Land AWS account in order to download pre-processed resource files generated by previous pipeline runs, in order to avoid having to regenerate these resources.
  * See [the section below](#using-this-repository-and-aws-authentication-matters) for advice on how to set this authentication up. The rest of the instructions will assume you are following this process.
* Running `aws-vault exec dl-dev -- docker-compose up` from the root of this repository should bring up airflow and allow you to access the [Airflow UI](https://airflow.apache.org/docs/apache-airflow/stable/ui.html) at http://localhost:8080 from where you can enable and trigger workflows.
* To trigger a workflow from the command line, you can run:

```sh
aws-vault exec dl-dev -- ./airflow.sh dags trigger <workflow name>
```

e.g.

```sh
aws-vault exec dl-dev -- ./airflow.sh dags trigger listed-building
```

Note that this won't run the pipeline synchronously; you'll need to have airflow running via `aws-vault exec dl-dev -- docker-compose up` in order for the pipeline to execute.

## Using this repository and AWS authentication matters

Throughout this guide, [aws-vault](https://github.com/99designs/aws-vault) is used in order to assume the correct role for accessing our AWS environment.
It is recommended to set something like this up, but you can get by with manual authentication or other tooling. Just ensure that the
various AWS env vars are setup such that you can use the aws cli as the `developer` role. You can check this with the following command:

```bash
aws sts get-caller-identity
```

If everything is configured correctly this should return the details of the `developer` role.

```json
{
    "UserId": "[USER_ID]",
    "Account": "[ACCOUNT_ID]",
    "Arn": "arn:aws:sts::[ACCOUNT_ID]:assumed-role/developer/[BIGNUM]"
}
```

Commands in the rest of this readme assume you've setup a profile in aws-vault with the name dl-dev. If you name the profile something else, you'll need to adjust the commands.
