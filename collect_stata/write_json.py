"""write_json.py"""
__author__ = "Marius Pahl"

import json
import logging
import pathlib
from collections import Counter
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from collect_stata.types import Categories, Numeric, Variable


def get_categorical_frequencies(elem: Variable, data: pd.DataFrame) -> Categories:
    """Generate dict with frequencies and labels for categorical variables

    Input:
    elem: dict
    data: pandas DataFrame

    Output:
    cat_dict: dict
    """

    frequencies: List[Numeric] = []

    value_count = data[elem["name"]].value_counts()

    # If values are not labeled in categorical variables, values become value and label
    for value in value_count.index:
        if value not in elem["categories"]["values"]:
            elem["categories"]["values"].append(int(value))
            elem["categories"]["labels"].append(str(int(value)))
            if value < 0:
                try:
                    elem["categories"]["missings"].append(True)
                except KeyError:
                    elem["categories"]["missings"] = list()
                    elem["categories"]["missings"].append(True)
            else:
                try:
                    elem["categories"]["missings"].append(True)
                except KeyError:
                    elem["categories"]["missings"] = list()
                    elem["categories"]["missings"].append(False)

    for value in elem["categories"]["values"]:
        try:
            frequencies.append(int(value_count[value]))
        except KeyError:
            frequencies.append(0)

    return {"frequencies": frequencies}


def get_categorical_statistics(
    elem: Variable, data: pd.DataFrame
) -> Dict[str, Union[int, float]]:
    """Generate dict with statistics for categorical variables

    Input:
    elem: dict
    data: pandas DataFrame

    Output:
    dict
    """

    total = data[elem["name"]].size
    invalid = int(data[elem["name"]].isnull().sum()) + int(
        sum(n < 0 for n in data[elem["name"]])
    )
    valid = total - invalid

    return {"valid": valid, "invalid": invalid}


def get_nominal_statistics(elem: Variable, data: pd.DataFrame) -> Dict[str, Numeric]:
    """Generate dict with statistics for nominal variables

    Input:
    elem: dict
    data: pandas DataFrame

    Output:
    dict
    """

    frequencies = Counter(data[elem["name"]])
    string_missings = frequencies[""] + frequencies["."]
    valid = data[elem["name"]].value_counts().sum() - string_missings
    invalid = data[elem["name"]].isnull().sum() + string_missings

    return {"valid": int(valid), "invalid": int(invalid)}


def get_numerical_statistics(
    elem: Variable, data: pd.DataFrame
) -> Dict[str, Union[float, int]]:
    """Generate dict with statistics for numerical variables

    Input:
    elem: dict
    data: pandas DataFrame

    Output:
    statistics: OrderedDict
    """

    data_withoutmissings = data[data[elem["name"]] >= 0][elem["name"]]

    total = data[elem["name"]].size
    invalid = int(data[elem["name"]].isnull().sum()) + int(
        sum(n < 0 for n in data[elem["name"]])
    )
    valid = total - invalid

    summary = data_withoutmissings.describe()
    return {
        "Min.": float(summary["min"]),
        "1st Qu.": float(summary["25%"]),
        "Median": float(summary["50%"]),
        "Mean": float(summary["mean"]),
        "3rd Qu.": float(summary["75%"]),
        "Max.": float(summary["max"]),
        "valid": int(valid),
        "invalid": int(invalid),
    }


def get_univariate_statistics(
    elem: Variable, data: pd.DataFrame
) -> Dict[str, Union[int, float]]:
    """Call function to generate statistics depending on the variable type

    Input:
    elem: dict
    data: pandas DataFrame

    Output:
    statistics: OrderedDict
    """

    if elem["scale"] == "cat":

        statistics = get_categorical_statistics(elem, data)

    elif elem["scale"] == "string":

        statistics = get_nominal_statistics(elem, data)

    elif elem["scale"] == "number":

        statistics = get_numerical_statistics(elem, data)

    else:
        statistics = dict()

    return statistics


def get_value_counts_and_frequencies(elem: Variable, data: pd.DataFrame) -> Categories:
    """Call function to generate frequencies depending on the variable type

    Input:
    elem: dict
    data: pandas DataFrame

    Output:
    statistics: OrderedDict
    """

    statistics: Categories = Categories()
    _scale = elem["scale"]

    if _scale == "cat":
        statistics.update(get_categorical_frequencies(elem, data))

    return statistics


def generate_statistics(
    data: pd.DataFrame, metadata: List[Variable], study: str
) -> List[Variable]:
    """Prepare statistics for every variable

    Input:
    data: pandas DataFrame
    metadata: dict
    study: string

    Output:
    stat: OrderedDict
    """

    for elem in metadata:
        logging.info("%s", str(len(metadata)))
        elem["study"] = study
        elem.update({"statistics": get_univariate_statistics(elem, data)})
        if elem["scale"] == "cat":
            elem["categories"].update(get_value_counts_and_frequencies(elem, data))

    return metadata


def update_metadata(
    metadata_en: Optional[List[Dict[str, Any]]],
    metadata_de: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Get information of german and english metadata and create a new metadata variable

    Input:
    metadata_en: Metadata of the english imported data.
    metadata_de: Metadata of the german imported data.

    Output:
    metadata: Metadata variable with german and english labels if given.
    """

    if metadata_de is None and metadata_en is not None:
        metadata = metadata_en.copy()
        for var in metadata:
            var["label_de"] = ""
    elif metadata_en is None and metadata_de is not None:
        metadata = metadata_de.copy()
        for var in metadata:
            var["label_de"] = var.pop("label")
            var["label"] = ""
            if var["scale"] == "cat":
                var["categories"]["labels_de"] = var["categories"].pop("labels")
                var["categories"]["labels"] = list()
    elif metadata_en is not None and metadata_de is not None:
        metadata = metadata_en.copy()
        for var, var_de in zip(metadata, metadata_de):
            var["label_de"] = var_de["label"]
            if var["scale"] == "cat":
                var["categories"]["labels_de"] = var_de["categories"]["labels"]

    return metadata


def write_json(  # pylint: disable=too-many-arguments
    data: pd.DataFrame,
    metadata_en: Optional[List[Dict[str, Any]]],
    metadata_de: Optional[List[Dict[str, Any]]],
    filename: pathlib.Path,
    study: str,
    latin1: bool,
) -> None:
    """Main function to write json.

    metadata_test = [
        {
            "name": "HKIND",
            "label": "test for categorical var",
            "type": "category",
            "scale": "cat",
            "categories": {
                "values": [-1, 1, 2],
                "labels": ["missing", "yes", "no"],
                "missings": [True, False, False],
            },
        },
        {
            "name": "HM04",
            "label": "test for numerical var",
            "type": "int",
            "scale": "number",
        },
        {
            "name": "HKGEBA",
            "label": "test for string var",
            "type": "str",
            "scale": "string",
        }
    ]

    metadata_de_test = [
        {
            "name": "HKIND",
            "label": "Test für kategoriale Variablen",
            "type": "category",
            "scale": "cat",
            "categories": {
                "values": [-1, 1, 2],
                "labels": ["missing", "ja", "nein"],
                "missings": [True, False, False],
            },
        },
        {
            "name": "HM04",
            "label": "Test für numerische Variablen",
            "type": "int",
            "scale": "number",
        },
        {
            "name": "HKGEBA",
            "label": "Test für nominale Variablen",
            "type": "str",
            "scale": "string",
        }
    ]

    Args:
        data: Datatable of imported data.
        metadata_en: Metadata of the english imported data.
        metadata_de: Metadata of the german imported data.
        filename: Name of the output json file.
        study: Name of the study.
    """

    metadata = update_metadata(metadata_en, metadata_de)

    stat = generate_statistics(data, metadata, study)

    logging.info('write "%s"', filename)
    # Pandas decodes data with Latin-1
    # The source will be decoded incorrectly,
    # if the source files are UTF-8 or anything other than Latin-1.
    # The data is encoded back to Latin-1 here
    # to minimize en/decoding errors.
    # This decode encode circle will most likely leave the original encoding intact.
    # If the source is actually a real Latin-1 encoded file, writing it back into Latin-1
    # will also make the output a Latin-1 file. We do not want this.
    # But since, in this case, the source was correctly decoded by pandas, we can just
    # write the file with UTF-8 encoding.
    # TL;DR: if the source is Latin-1 encoded we can safely use utf-8 for writing output.
    encoding = "utf-8" if latin1 else "latin1"
    with open(filename, "w+", encoding=encoding) as json_file:
        json.dump(stat, json_file, indent=2, ensure_ascii=False)
