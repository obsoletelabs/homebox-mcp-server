from os import getenv
import json
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

from homebox_wrapper import homebox_wrapper

mcp = FastMCP("Homebox mcp server")

load_dotenv()
client = homebox_wrapper(
    getenv("HOMEBOX_URL"),
    getenv("HOMEBOX_EMAIL"),
    getenv("HOMEBOX_PASSWORD"),
)


def format_items_for_ai(items, location_map):
    results = []
    for item in items:
        location_id = str(item.location.id) if item.location else None
        full_path = location_map.get(location_id, "Unknown") if location_id else "Unknown"

        results.append({
            "name": item.name,
            "id": str(item.id),
            "description": item.description or "",
            "location": full_path,
            "quantity": item.quantity,
            "asset_id": item.assetId,
        })
    return json.dumps(results, indent=2)

def format_item_for_ai(item, location_map):
    location_id = str(item.location.id) if item.location else None
    full_path = location_map.get(location_id, "Unknown") if location_id else "Unknown"

    return json.dumps({
        "name": item.name,
        "id": str(item.id),
        "description": item.description or "NULL",
        "location": full_path,
        "quantity": item.quantity,
        "asset_id": item.assetId,
        "insured": item.insured,
        "archived": item.archived,
        "labels": [l.name for l in item.labels] if item.labels else [],
        "purchase_price": item.purchasePrice,
        "purchase_from": item.purchaseFrom or "NULL",
        "purchase_date": str(item.purchaseTime) if item.purchaseTime else "NULL",
        "warranty_expires": str(item.warrantyExpires) if item.warrantyExpires else "NULL",
        "warranty_details": item.warrantyDetails or "NULL",
        "serial_number": item.serialNumber or "NULL",
        "model_number": item.modelNumber or "NULL",
        "manufacturer": item.manufacturer or "NULL",
        "notes": item.notes or "NULL",
    }, indent=2)

def format_locations_for_ai(locations):
    return json.dumps(locations, indent=2)

def format_location_for_ai(location, location_map):
    location_id = str(location.id)
    full_path = location_map.get(location_id, "Unknown")

    return json.dumps({
        "id": location_id,
        "name": location.name,
        "full_path": full_path,
        "description": location.description or "NULL",
        "parent_id": str(location.parent.id) if getattr(location, "parent", None) and location.parent else "NULL",
    }, indent=2)

def format_labels_for_ai(labels):
    return json.dumps([
        {
            "id": str(label.id),
            "name": label.name,
            "description": label.description or "NULL"
        }
        for label in labels
    ], indent=2)

def format_label_for_ai(label):
    return json.dumps({
        "id": str(label.id),
        "name": label.name,
        "description": label.description or "NULL"
    }, indent=2)

def format_items_for_ai_simple(items):
    return json.dumps([
        {
            "id": str(item.id),
            "name": item.name,
            "description": item.description or "",
            "quantity": item.quantity,
            "asset_id": item.assetId,
        }
        for item in items
    ], indent=2)




@mcp.tool()
def search_inventory(search_term: str) -> str:
    """Search homebox inventory for search term"""
    return format_items_for_ai(client.search_items(search_term, 5), client.build_location_map())

@mcp.tool()
def get_item(item_id: str) -> str:
    """Get complete details about a specific item by its ID."""
    return format_item_for_ai(client.get_item(item_id), client.build_location_map())

@mcp.tool()
def list_locations() -> str:
    """List all storage locations as a flat list with full paths and hierarchy info."""
    return format_locations_for_ai(client.list_locations())

@mcp.tool()
def get_location(location_id: str) -> str:
    """Get full details about a specific location by its ID."""
    return format_location_for_ai(client.get_location(location_id), client.build_location_map())

@mcp.tool()
def list_labels() -> str:
    """List all labels/categories."""
    return format_labels_for_ai(client.list_labels())

@mcp.tool()
def get_label(label_id: str) -> str:
    """Get full details for a specific label."""
    return format_label_for_ai(client.get_label(label_id))

@mcp.tool()
def get_items_by_location(location_id: str) -> str:
    """List all items stored in a specific location."""
    items = client.get_items_by_location(location_id)
    return format_items_for_ai_simple(items)

@mcp.tool()
def get_items_by_label(label_id: str) -> str:
    """List all items that have a specific label."""
    items = client.get_items_by_label(label_id)
    return format_items_for_ai_simple(items)


@mcp.tool()
def create_item(name: str, location_id: str, description: str = "", quantity: int = 1) -> str:
    """Create a new item in the given location."""
    item = client.create_item(
        name=name,
        location_id=location_id,
        description=description,
        quantity=quantity,
    )
    return format_item_for_ai(item, client.build_location_map())




if __name__ == "__main__":
    mcp.run(transport="streamable-http")