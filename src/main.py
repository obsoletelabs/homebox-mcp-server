from os import getenv
import json
from dotenv import load_dotenv
import logging
from datetime import datetime

import base64
import io
from PIL import Image

from mcp.server.fastmcp import FastMCP

from homebox_wrapper import homebox_wrapper

mcp = FastMCP("Homebox mcp server")

load_dotenv()
client = homebox_wrapper(
    getenv("HOMEBOX_URL"),
    getenv("HOMEBOX_EMAIL"),
    getenv("HOMEBOX_PASSWORD"),
)


# Set up logger (put this near the top of server.py with your other setup code)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/deleted_items.log"),
        logging.StreamHandler(),  # also prints to console
    ]
)
logger = logging.getLogger(__name__)


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

@mcp.tool()
def delete_item(item_id: str) -> str:
    """Delete an item by its ID."""
    # Fetch details before deleting so we can log the name
    try:
        item = client.get_item(item_id)
        item_name = item.name
        item_location = client.build_location_map().get(str(item.location.id), "Unknown") if item.location else "Unknown"
    except Exception:
        item_name = "Unknown"
        item_location = "Unknown"

    client.delete_item(item_id)

    logger.info(f"DELETED | id={item_id} | name={item_name} | location={item_location}")
    with open("/deleted_items.log", "a") as f:
        f.write(f"DELETED | id={item_id} | name={item_name} | location={item_location}")

    return json.dumps({
        "success": True,
        "deleted_item_id": item_id,
        "deleted_item_name": item_name,
    })


@mcp.tool()
def update_item(
    item_id: str,
    name: str = None,
    description: str = None,
    quantity: int = None,
    location_id: str = None,
    insured: bool = None,
    archived: bool = None,
    purchase_price: float = None,
    purchase_from: str = None,
    purchase_date: str = None,
    warranty_expires: str = None,
    warranty_details: str = None,
    serial_number: str = None,
    model_number: str = None,
    manufacturer: str = None,
    notes: str = None,
) -> str:
    """Update any fields on an existing item. Only pass the fields you want to change."""
    field_map = {
        "name": name,
        "description": description,
        "quantity": quantity,
        "locationId": location_id,
        "insured": insured,
        "archived": archived,
        "purchasePrice": purchase_price,
        "purchaseFrom": purchase_from,
        "purchaseTime": purchase_date,
        "warrantyExpires": warranty_expires,
        "warrantyDetails": warranty_details,
        "serialNumber": serial_number,
        "modelNumber": model_number,
        "manufacturer": manufacturer,
        "notes": notes,
    }

    # Only pass fields that were explicitly provided
    updates = {k: v for k, v in field_map.items() if v is not None}

    if not updates:
        return json.dumps({"error": "No fields provided to update."})

    updated_item = client.update_item(item_id, **updates)
    return format_item_for_ai(updated_item, client.build_location_map())


@mcp.tool()
def create_location(name: str, description: str = "", parent_id: str = None) -> str:
    """Create a new location. Optionally nest it under a parent location by providing a parent_id."""
    location = client.create_location(
        name=name,
        description=description,
        parent_id=parent_id,
    )
    return format_location_for_ai(location, client.build_location_map())


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
