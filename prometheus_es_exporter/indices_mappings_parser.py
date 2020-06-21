from collections import OrderedDict

from .metrics import format_metric_name, format_labels
from .utils import merge_dicts_ordered


def count_object_fields(object_mappings, counts=None):
    if counts is None:
        counts = {}
    else:
        counts = counts.copy()

    for field, mapping in object_mappings['properties'].items():
        # This field is an object, so count its fields.
        if 'properties' in mapping:
            counts = count_object_fields(mapping, counts=counts)

        else:
            field_type = mapping['type']
            if field_type in counts:
                counts[field_type] += 1
            else:
                counts[field_type] = 1

            # If a field has any multifields (copies of the field with different mappings) we need
            # to add their mappings as well.
            if 'fields' in mapping:
                for mfield, mfield_mapping in mapping['fields'].items():
                    mfield_type = mfield_mapping['type']
                    if mfield_type in counts:
                        counts[mfield_type] += 1
                    else:
                        counts[mfield_type] = 1

    return counts


def parse_index(index, mappings, metric=None):
    if metric is None:
        metric = []

    metric = metric + ['field', 'count']
    labels = OrderedDict([('index', index)])

    # In newer Elasticsearch versions, the mappings root is simply the object mappings for the whole
    # document, so we can count the fields in it directly.
    if 'properties' in mappings:
        counts = count_object_fields(mappings)

    # Older Elasticsearch versions had the concept of mapping types, so the root maps from mapping
    # type to the object mappings for that type. We have to count the fields the types separately.
    else:
        counts = {}
        for mapping_type, type_mappings in mappings.items():
            counts = count_object_fields(type_mappings, counts=counts)

    metrics = []
    for field_type, count in counts.items():
        metrics.append((metric, '', merge_dicts_ordered(labels, field_type=field_type), count))

    return metrics


def parse_response(response, metric=None):
    if metric is None:
        metric = []

    metrics = []

    for index, data in response.items():
        metrics.extend(parse_index(index, data['mappings'], metric=metric))

    return [
        (format_metric_name(*metric_name),
         metric_doc,
         format_labels(label_dict),
         value)
        for metric_name, metric_doc, label_dict, value
        in metrics
    ]
