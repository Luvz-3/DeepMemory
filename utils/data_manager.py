import json
import os
import datetime
from typing import List, Dict, Any
import itertools

DATA_DIR = "data"
NODES_FILE = os.path.join(DATA_DIR, "nodes.json")
EVENTS_FILE = os.path.join(DATA_DIR, "events.json")
EDGES_FILE = os.path.join(DATA_DIR, "edges.json")

def load_json(filepath: str) -> List[Dict[str, Any]]:
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_json(filepath: str, data: List[Dict[str, Any]]):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_nodes() -> List[Dict[str, Any]]:
    return load_json(NODES_FILE)

def get_node_by_id(node_id: str) -> Dict[str, Any]:
    nodes = get_nodes()
    for n in nodes:
        if n['id'] == node_id:
            return n
    return None

def save_node(node: Dict[str, Any]):
    nodes = get_nodes()
    found = False
    for i, n in enumerate(nodes):
        if n['id'] == node['id']:
            nodes[i] = node
            found = True
            break
    if not found:
        nodes.append(node)
    save_json(NODES_FILE, nodes)

def delete_node(node_id: str):
    """
    Safely deletes a node and cleans up all references (edges and events).
    """
    # 1. Remove Node
    nodes = get_nodes()
    new_nodes = [n for n in nodes if n['id'] != node_id]
    save_json(NODES_FILE, new_nodes)
    
    # 2. Remove Edges
    edges = get_edges()
    new_edges = [e for e in edges if e['source'] != node_id and e['target'] != node_id]
    save_json(EDGES_FILE, new_edges)
    
    # 3. Clean Events
    events = get_events()
    for e in events:
        if node_id in e.get('related_nodes', []):
            e['related_nodes'].remove(node_id)
            # Note: We keep the event even if empty, as it might have text/images.
            
    save_json(EVENTS_FILE, events)
    
    # 4. Consistency Check (optional but good)
    update_edges_from_events()

def get_events() -> List[Dict[str, Any]]:
    return load_json(EVENTS_FILE)

def save_event(event: Dict[str, Any]):
    events = get_events()
    events.append(event)
    save_json(EVENTS_FILE, events)
    update_edges_from_events()

def get_all_events() -> List[Dict[str, Any]]:
    """
    Returns all events sorted by date descending.
    """
    events = get_events()
    events.sort(key=lambda x: x.get('date', ''), reverse=True)
    return events

def delete_event(event_id: str):
    """
    Deletes the event with the given ID.
    """
    events = get_events()
    new_events = [e for e in events if e['id'] != event_id]
    save_json(EVENTS_FILE, new_events)
    # Note: We might want to re-calc edges if edges are derived from events.
    # Currently edges are cumulative/independent mostly, but update_edges_from_events exists.
    # For now, simplistic delete.
    update_edges_from_events()

def update_event(event_id: str, new_data: Dict[str, Any]):
    """
    Updates the event with the given ID using the provided data.
    """
    events = get_events()
    updated = False
    for i, e in enumerate(events):
        if e['id'] == event_id:
            events[i].update(new_data)
            updated = True
            break
            
    if updated:
        save_json(EVENTS_FILE, events)
        update_edges_from_events()

def get_events_for_node(node_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all events involving a specific node, sorted by date (newest first).
    """
    events = get_events()
    node_events = []
    
    for e in events:
        if node_id in e.get('related_nodes', []):
            node_events.append(e)
            
    # Sort by date descending
    node_events.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return node_events

def get_edges() -> List[Dict[str, Any]]:
    return load_json(EDGES_FILE)

def add_edge(source: str, target: str, label: str = ""):
    """
    Manually creates or updates an edge between two nodes.
    """
    if source == target: return
    
    edges = get_edges()
    key_sorted = tuple(sorted((source, target)))
    
    found = False
    for e in edges:
        e_key = tuple(sorted((e['source'], e['target'])))
        if e_key == key_sorted:
            e['relation_type'] = label
            # Optionally increment weight? For manual mapping, maybe not.
            found = True
            break
    
    if not found:
        new_edge = {
            "source": key_sorted[0],
            "target": key_sorted[1],
            "weight": 1,
            "last_interaction": str(datetime.date.today()),
            "relation_type": label
        }
        edges.append(new_edge)
        
    save_json(EDGES_FILE, edges)

def remove_edge(source: str, target: str):
    """
    Deletes the edge between two nodes.
    """
    edges = get_edges()
    key_sorted = tuple(sorted((source, target)))
    
    new_edges = []
    for e in edges:
        e_key = tuple(sorted((e['source'], e['target'])))
        if e_key != key_sorted:
            new_edges.append(e)
            
    save_json(EDGES_FILE, new_edges)

def update_edge_attribute(source: str, target: str, attr_key: str, attr_value: Any):
    """
    Manually updates an attribute (like label/relation_type) for a specific edge.
    """
    edges = get_edges()
    key_sorted = tuple(sorted((source, target)))
    
    updated = False
    for e in edges:
        e_key = tuple(sorted((e['source'], e['target'])))
        if e_key == key_sorted:
            e[attr_key] = attr_value
            updated = True
            break
            
    if updated:
        save_json(EDGES_FILE, edges)

def update_edges_from_events():
    """
    Re-calculates edges. Preserves existing 'relation_type' if already set, 
    unless new info overwrites it (not implemented here strictly, we keep old labels).
    """
    events = get_events()
    old_edges = {tuple(sorted((e['source'], e['target']))): e for e in get_edges()}
    
    edges_map = {} 
    root_id = "root_me"
    
    for event in events:
        participants = event.get("related_nodes", [])
        date = event.get("date", "")
        # Check if this event brought explicit relation info (custom structure)
        # We might store relation info in the event in future iterations.
        
        # 1. Link Me to everyone
        for p_id in participants:
            if p_id == root_id: continue
            
            key = tuple(sorted((root_id, p_id)))
            if key not in edges_map:
                # Inherit old data if exists
                old_data = old_edges.get(key, {})
                edges_map[key] = {
                    "source": key[0], 
                    "target": key[1], 
                    "weight": 0, 
                    "last_interaction": "",
                    "relation_type": old_data.get("relation_type", "")
                }
            
            edges_map[key]["weight"] += 1
            if date > edges_map[key]["last_interaction"]:
                edges_map[key]["last_interaction"] = date

        # 2. Link participants
        for p1, p2 in itertools.combinations(participants, 2):
            if p1 == root_id or p2 == root_id: continue 
            
            key = tuple(sorted((p1, p2)))
            if key not in edges_map:
                 old_data = old_edges.get(key, {})
                 edges_map[key] = {
                     "source": key[0], 
                     "target": key[1], 
                     "weight": 0, 
                     "last_interaction": "",
                     "relation_type": old_data.get("relation_type", "")
                 }
            
            edges_map[key]["weight"] += 1
            if date > edges_map[key]["last_interaction"]:
                edges_map[key]["last_interaction"] = date
    
def reset_database():
    """
    Factory reset: wipes all data and restores the initial state with just 'Me'.
    """
    # 1. Delete files
    for filepath in [NODES_FILE, EDGES_FILE, EVENTS_FILE]:
        if os.path.exists(filepath):
            os.remove(filepath)
            
    # 2. Re-initialize Nodes with 'Me'
    root_node = {
        "id": "root_me",
        "name": "Me",
        "type": "person",
        "description": "The center of the universe",
        "created_at": str(datetime.date.today()),
        "avatar_type": "color",
        "avatar_value": "#2C3E50"
    }
    save_json(NODES_FILE, [root_node])
    
    # 3. Re-initialize empty Edges and Events
    save_json(EDGES_FILE, [])
    save_json(EVENTS_FILE, [])
    
    return True