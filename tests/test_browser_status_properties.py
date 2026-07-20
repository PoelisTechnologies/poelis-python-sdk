from __future__ import annotations

from poelis_sdk._browser.node.properties import _item_properties_gql


def test_item_properties_gql_includes_status_fragments() -> None:
    query_sdk, _, name_sdk = _item_properties_gql(
        use_sdk=True,
        item_id="item-1",
        product_id=None,
        version_number=None,
    )
    assert name_sdk == "sdkProperties"
    assert (
        "... on SdkStatusProperty { id name readableId deleted value parsedValue updatedAt updatedBy }"
        in query_sdk
    )

    query, _, name = _item_properties_gql(
        use_sdk=False,
        item_id="item-1",
        product_id=None,
        version_number=None,
    )
    assert name == "properties"
    assert (
        "... on StatusProperty { id name readableId deleted value parsedValue }"
        in query
    )
    assert "... on SdkStatusProperty" not in query
