from homebox import HomeboxClient
from homebox.models import ItemCreate

class homebox_wrapper():
    def __init__(self, HOMEBOX_URL, HOMEBOX_EMAIL, HOMEBOX_PASSWORD):
        self.client = HomeboxClient(base_url=f"{HOMEBOX_URL}/api")
        self.client.login(HOMEBOX_EMAIL, HOMEBOX_PASSWORD)

    def build_location_map(self):
        """Fetch the full location tree and build a flat id -> full path map."""
        tree = self.client.locations.get_locations_tree()
        location_map = {}

        def walk(node, path_so_far):
            full_path = f"{path_so_far} > {node.name}" if path_so_far else node.name
            location_map[str(node.id)] = full_path
            if node.children:
                for child in node.children:
                    walk(child, full_path)

        for root in tree:
            walk(root, "")

        return location_map

    def search_items(self, search_term: str, limit: int = 5):
        location_map = self.build_location_map()

        result = self.client.items.query_all_items(q=search_term, pageSize=limit, page=1)
        items = result.items or []

        #print(f"\nTop {len(items)} results for '{search_term}':\n")
        for i, item in enumerate(items, 1):
            location_id = str(item.location.id) if item.location else None
            full_path = location_map.get(location_id, "Unknown") if location_id else "Unknown"

            #print(f"{i}. {item.name}")
            #print(f"   ID:          {item.id}")
            #print(f"   Location:    {full_path}")
            #print(f"   Description: {item.description or 'No description'}")
            #print()

        return items

    def get_item(self, item_id: str):
        return self.client.items.get_item(item_id)





    def list_locations(self):
        """Return the full location tree as a flat list with full paths and metadata."""
        tree = self.client.locations.get_locations_tree()
        locations = []

        def walk(node, path_so_far):
            full_path = f"{path_so_far} > {node.name}" if path_so_far else node.name
            locations.append({
                "id": str(node.id),
                "name": node.name,
                "full_path": full_path,
                "parent_id": str(node.parent.id) if getattr(node, "parent", None) and node.parent else None,
                "child_count": len(node.children) if node.children else 0,
            })
            if node.children:
                for child in node.children:
                    walk(child, full_path)

        for root in tree:
            walk(root, "")

        return locations

    def get_location(self, location_id: str):
        """Get full details for a single location by ID."""
        return self.client.locations.get_location(location_id)

    def list_labels(self):
        """Return all labels/categories."""
        return self.client.labels.get_labels() or []

    def get_label(self, label_id: str):
        """Get full details for a single label by ID."""
        return self.client.labels.get_label(label_id)

    def get_items_by_location(self, location_id: str, limit: int = 50):
        """Return all items in a given location."""
        result = self.client.items.query_all_items(locations=[location_id], pageSize=limit, page=1)
        return result.items or []

    def get_items_by_label(self, label_id: str, limit: int = 50):
        """Return all items with a given label."""
        result = self.client.items.query_all_items(labelIds=[label_id], pageSize=limit, page=1)
        return result.items or []

    def create_item(self, name: str, location_id: str, description: str = "", quantity: int = 1):
        """Create a new item in the given location."""
        summary = self.client.items.create_item(ItemCreate(
            name=name,
            description=description,
            quantity=quantity,
            locationId=location_id,
        ))
        # create_item returns ItemSummary (no purchase/warranty fields),
        # so fetch the full ItemOut before returning
        return self.client.items.get_item(str(summary.id))
    
    def delete_item(self, item_id: str) -> bool:
        """Delete an item by its ID."""
        self.client.items.delete_item(item_id)
        return True
    
    def update_item(self, item_id: str, **kwargs) -> object:
        """Update fields on an existing item by its ID."""
        from homebox.models import ItemUpdate

        item = self.client.items.get_item(item_id)

        # Build the update payload from the full existing item
        payload = ItemUpdate(
            name=kwargs.get("name", item.name),
            description=kwargs.get("description", item.description),
            quantity=kwargs.get("quantity", item.quantity),
            locationId=kwargs.get("locationId", str(item.location.id) if item.location else None),
            insured=kwargs.get("insured", item.insured),
            archived=kwargs.get("archived", item.archived),
            purchasePrice=kwargs.get("purchasePrice", item.purchasePrice),
            purchaseFrom=kwargs.get("purchaseFrom", item.purchaseFrom),
            purchaseTime=kwargs.get("purchaseTime", item.purchaseTime),
            warrantyExpires=kwargs.get("warrantyExpires", item.warrantyExpires),
            warrantyDetails=kwargs.get("warrantyDetails", item.warrantyDetails),
            serialNumber=kwargs.get("serialNumber", item.serialNumber),
            modelNumber=kwargs.get("modelNumber", item.modelNumber),
            manufacturer=kwargs.get("manufacturer", item.manufacturer),
            notes=kwargs.get("notes", item.notes),
        )

        self.client.items.update_item(item_id, payload)
        return self.client.items.get_item(item_id)


    def create_location(self, name: str, description: str = "", parent_id: str = None) -> object:
        """Create a new location, optionally nested under a parent."""
        from homebox.models import LocationCreate

        return self.client.locations.create_location(LocationCreate(
            name=name,
            description=description,
            parentId=parent_id,
        ))